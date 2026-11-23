"""CLI operacional do pipeline IBGE Market Intelligence (run, maintain, inspect, idempotency)."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import time
import uuid
from collections.abc import Sequence

import duckdb
from deltalake import DeltaTable

from ibge_market_intel.analytics.insights import build_market_insights, format_insights_report
from ibge_market_intel.config import PipelineSettings, get_settings
from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_MUNICIPAL_SPEC,
    CEMPRE_SETORIAL_UF_SPEC,
    CEMPRE_YEARS,
    CENSO_POPULACAO_SPEC,
    CENSO_YEARS,
    ESTIMATIVA_POP_YEARS,
    ESTIMATIVA_POPULACAO_SPEC,
    IPCA_MENSAL_SPEC,
    IPCA_YEARS,
    PIB_MUNICIPAL_SPEC,
    PIB_YEARS,
    PMC_VAREJO_UF_SPEC,
    PMC_YEARS,
    AgregadoSpec,
)
from ibge_market_intel.ingestion.client import IBGEAsyncClient
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter
from ibge_market_intel.logging import configure_logging, get_logger
from ibge_market_intel.orchestration.assets_gold_export import (
    GOLD_EXPORT_TABLES,
    SILVER_EXPORT_TABLES,
    export_duckdb_tables_to_delta,
)
from ibge_market_intel.orchestration.resources import IBGEPipelineResource
from ibge_market_intel.quality.contracts import (
    validate_cnae_contract,
    validate_localidades_contract,
    validate_sidra_contract,
)

logger = get_logger(__name__)


async def _ingest_all_bronze(
    settings: PipelineSettings,
    *,
    smoke: bool,
    run_id: str,
) -> None:
    writer = DeltaLakeWriter(settings.resolved_bronze_dir)
    uf_codes = settings.uf_filter or ([35, 51] if smoke else None)

    async with IBGEAsyncClient(settings) as client:
        # 1. Cadastros (Localidades + CNAE)
        loc_res = await client.fetch_localidades(uf_codes=uf_codes)
        loc_report = validate_localidades_contract(loc_res.df)
        if not loc_report.passed:
            raise RuntimeError(f"Contrato Bronze localidades falhou: {loc_report.error_message}")
        writer.write_full_overwrite(
            loc_res.df,
            "localidades",
            ingestion_id=run_id,
            source_url=loc_res.source_urls[0],
        )

        cnae_res = await client.fetch_cnae_secoes()
        cnae_report = validate_cnae_contract(cnae_res.df)
        if not cnae_report.passed:
            raise RuntimeError(f"Contrato Bronze cnae_secoes falhou: {cnae_report.error_message}")
        writer.write_full_overwrite(
            cnae_res.df,
            "cnae_secoes",
            ingestion_id=run_id,
            source_url=cnae_res.source_urls[0],
        )

        # 2. Fontes SIDRA particionadas por ano
        plan: list[tuple[AgregadoSpec, Sequence[str]]] = [
            (PIB_MUNICIPAL_SPEC, ("2020", "2022", "2023") if smoke else PIB_YEARS),
            (CENSO_POPULACAO_SPEC, CENSO_YEARS),
            (
                ESTIMATIVA_POPULACAO_SPEC,
                ("2020", "2021", "2024", "2025") if smoke else ESTIMATIVA_POP_YEARS,
            ),
            (CEMPRE_MUNICIPAL_SPEC, ("2022", "2023", "2024") if smoke else CEMPRE_YEARS),
            (CEMPRE_SETORIAL_UF_SPEC, ("2022", "2023", "2024") if smoke else CEMPRE_YEARS),
            (IPCA_MENSAL_SPEC, ("2020", "2022", "2023", "2024", "2025") if smoke else IPCA_YEARS),
            (PMC_VAREJO_UF_SPEC, ("2023", "2024") if smoke else PMC_YEARS),
        ]

        for spec, years in plan:
            for ano in years:
                res = await client.fetch_agregado_for_year(spec, ano=ano, uf_codes=uf_codes)
                if res.df.height == 0:
                    continue
                report = validate_sidra_contract(res.df, spec.table_name)
                if not report.passed:
                    raise RuntimeError(
                        f"Circuit Breaker Pandera em {spec.table_name} ({ano}): "
                        f"{report.error_message}"
                    )
                writer.write_partition_overwrite(
                    res.df,
                    spec.table_name,
                    partition_col="ano_referencia",
                    partition_value=ano,
                    ingestion_id=run_id,
                    source_url=res.source_urls[0] if res.source_urls else "",
                )


def _run_dbt_build(settings: PipelineSettings) -> None:
    env = dict(os.environ)
    env["IBGE_BRONZE_DIR"] = settings.resolved_bronze_dir.as_posix()
    env["IBGE_DUCKDB_PATH"] = settings.resolved_duckdb_path.as_posix()
    cmd = [
        "dbt",
        "build",
        "--project-dir",
        str(settings.resolved_dbt_project_dir),
        "--profiles-dir",
        str(settings.resolved_dbt_project_dir),
    ]
    subprocess.run(cmd, env=env, check=True)


def run_pipeline(*, mode: str) -> None:
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(settings.log_level, log_format="console")
    run_id = f"{mode}-{uuid.uuid4().hex[:8]}"
    t0 = time.perf_counter()

    logger.info(
        "pipeline_start", mode=mode, run_id=run_id, data_dir=str(settings.resolved_data_dir)
    )
    asyncio.run(_ingest_all_bronze(settings, smoke=(mode == "smoke"), run_id=run_id))

    logger.info("dbt_build_start", run_id=run_id)
    _run_dbt_build(settings)

    logger.info("delta_export_start", run_id=run_id)
    pipeline_res = IBGEPipelineResource(data_dir=str(settings.resolved_data_dir))
    silver_summary = export_duckdb_tables_to_delta(
        pipeline_res,
        schema="silver",
        tables=SILVER_EXPORT_TABLES,
        layer="silver",
        run_id=run_id,
    )
    gold_summary = export_duckdb_tables_to_delta(
        pipeline_res,
        schema="gold",
        tables=GOLD_EXPORT_TABLES,
        layer="gold",
        run_id=run_id,
    )
    logger.info(
        "pipeline_finished",
        run_id=run_id,
        elapsed_seconds=round(time.perf_counter() - t0, 2),
        silver_tables=len(silver_summary),
        gold_tables=len(gold_summary),
    )


def maintain_lakehouse() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, log_format="console")
    for layer_dir in (
        settings.resolved_bronze_dir,
        settings.resolved_silver_dir,
        settings.resolved_gold_dir,
    ):
        writer = DeltaLakeWriter(layer_dir)
        if not layer_dir.exists():
            continue
        for child in sorted(layer_dir.iterdir()):
            if child.is_dir() and (child / "_delta_log").exists():
                writer.maintain_table(child.name, retention_hours=168, dry_run=False)


def inspect_gold() -> None:
    settings = get_settings()
    con = duckdb.connect(str(settings.resolved_duckdb_path), read_only=True)
    con.execute("LOAD delta;")
    try:
        print("\n=== 1. TOP 15 MUNICIPIOS POR SCORE IMS (ULTIMO ANO COMPLETO) ===")
        rows = con.execute(
            """
            select
                rank_nacional_ims as rk,
                nome_municipio || ' - ' || sigla_uf as municipio,
                ano_referencia as ano,
                populacao_residente as pop,
                round(pib_real_mil_brl / 1e6, 2) as pib_real_bi,
                round(pib_per_capita_real_brl, 0) as pib_pc_real,
                num_empresas_atuantes as empresas,
                round(salario_medio_real_brl, 0) as sal_medio_real,
                ims_score_0_100 as ims,
                tier_mercado as tier
            from gold.mart_inteligencia_mercado_municipal
            where is_ultimo_ano_completo
            order by rank_nacional_ims
            limit 15
            """
        ).fetchall()
        for r in rows:
            print(r)

        print("\n=== 2. DISTRIBUICAO POR TIER DE MERCADO (ULTIMO ANO COMPLETO) ===")
        for r in con.execute(
            """
            select
                tier_mercado,
                count(*) as municipios,
                round(avg(ims_score_0_100), 2) as media_ims,
                round(sum(pib_real_mil_brl) / 1e9, 2) as pib_real_tri
            from gold.mart_inteligencia_mercado_municipal
            where is_ultimo_ano_completo
            group by 1
            order by media_ims desc
            """
        ).fetchall():
            print(r)

        print("\n=== 3. VALIDACAO BOA ESPERANCA DO NORTE (5101837) EM DIM_GEOGRAFIA ===")
        print(
            con.execute(
                """
                select codigo_ibge_municipio, nome_municipio, sigla_uf,
                       nome_regiao_imediata, codigo_microrregiao, is_current
                from gold.dim_geografia
                where codigo_ibge_municipio = 5101837
                """
            ).fetchall()
        )

        print("\n=== 4. TOP 10 CLUSTERS SETORIAIS ESTADUAIS POR QUOCIENTE LOCACIONAL (2024) ===")
        for r in con.execute(
            """
            select
                sigla_uf,
                codigo_secao_cnae,
                left(descricao_secao_cnae, 42) as setor,
                pessoal_ocupado_total as emprego,
                quociente_locacional_emprego as ql,
                round(market_share_uf_no_setor_pct, 2) as share_br_pct,
                perfil_especializacao
            from gold.mart_clusters_setoriais_uf
            where ano_referencia = (select max(ano_referencia) from gold.mart_clusters_setoriais_uf)
                and pessoal_ocupado_total >= 10000
            order by quociente_locacional_emprego desc nulls last,
                market_share_uf_no_setor_pct desc nulls last
            limit 10
            """
        ).fetchall():
            print(r)

        print("\n=== 5. PULSO DO VAREJO (PMC x IPCA) - ULTIMA COMPETENCIA (SP/MG/BA/RS) ===")
        for r in con.execute(
            """
            select
                ano_mes,
                sigla_uf,
                left(nome_atividade_pmc, 38) as atividade,
                var_yoy_volume_pct as vol_yoy,
                var_yoy_receita_nominal_pct as rec_yoy,
                spread_preco_vs_volume_yoy_pp as spread_pp,
                ipca_variacao_acum_12m_pct as ipca_12m,
                regime_consumo
            from gold.mart_pulso_consumo_macro
            where ano_mes = (select max(ano_mes) from gold.mart_pulso_consumo_macro)
                and sigla_uf in ('SP', 'MG', 'BA', 'RS')
                and codigo_atividade_pmc in (103154, 103155, 103159)
            order by sigla_uf, codigo_atividade_pmc
            """
        ).fetchall():
            print(r)

        print("\n=== 6. AUDITORIA DELTA LAKE GOLD ===")
        for tbl in (
            "mart_inteligencia_mercado_municipal",
            "mart_clusters_setoriais_uf",
            "mart_pulso_consumo_macro",
        ):
            p = settings.resolved_gold_dir / tbl
            if (p / "_delta_log").exists():
                dt = DeltaTable(str(p))
                cnt = con.execute(
                    "select count(*) from delta_scan(?)",
                    [p.as_posix()],
                ).fetchone()
                print(f"  gold/{tbl}: delta_v={dt.version()} | rows={cnt[0] if cnt else 0}")
    finally:
        con.close()


def run_quality_suite() -> None:
    """Executa toda a bateria de qualidade (ruff, mypy, pytest unit+E2E e dbt unit tests)."""
    settings = get_settings()
    dbt_dir = str(settings.resolved_dbt_project_dir)
    commands: list[list[str]] = [
        ["ruff", "check", "src", "tests"],
        ["ruff", "format", "--check", "src", "tests"],
        ["mypy", "src"],
        ["pytest", "tests/unit", "-v", "--cov=ibge_market_intel"],
        ["pytest", "tests/integration", "-v"],
        ["dbt", "parse", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir],
        [
            "dbt",
            "test",
            "--select",
            "test_type:unit",
            "--project-dir",
            dbt_dir,
            "--profiles-dir",
            dbt_dir,
        ],
    ]
    for cmd in commands:
        print(f"\n>>> Executando: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


def show_insights(*, top_n: int = 10, uf: str | None = None, year: int | None = None) -> None:
    """Executa consultas analiticas em Polars Lazy (scan_delta) sobre os marts Gold."""
    settings = get_settings()
    report = build_market_insights(
        settings.resolved_gold_dir,
        top_n=top_n,
        uf=uf,
        year=year,
    )
    print(format_insights_report(report))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="SidraLake — IBGE Market Intelligence 360 Medallion CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Executa pipeline completo Bronze -> Silver -> Gold")
    run_cmd.add_argument("--mode", choices=("smoke", "full"), default="full")

    sub.add_parser("maintain", help="Executa OPTIMIZE e VACUUM nas tabelas Delta Lake")
    sub.add_parser("inspect", help="Imprime metricas de sanity check da camada Gold (DuckDB)")
    insights_cmd = sub.add_parser(
        "insights",
        help="Gera rankings de mercado via Polars Lazy API (scan_delta) na camada Gold",
    )
    insights_cmd.add_argument(
        "--top", type=int, default=10, help="Quantidade de linhas por ranking"
    )
    insights_cmd.add_argument(
        "--uf", type=str, default=None, help="Filtra por sigla da UF (ex: SP)"
    )
    insights_cmd.add_argument("--year", type=int, default=None, help="Filtra por ano de referencia")
    sub.add_parser(
        "test", help="Executa toda a bateria de testes e qualidade (ruff, mypy, pytest, dbt)"
    )

    args = parser.parse_args(argv)
    if args.command == "run":
        run_pipeline(mode=args.mode)
    elif args.command == "maintain":
        maintain_lakehouse()
    elif args.command == "inspect":
        inspect_gold()
    elif args.command == "insights":
        show_insights(top_n=args.top, uf=args.uf, year=args.year)
    elif args.command == "test":
        run_quality_suite()


if __name__ == "__main__":
    main()
