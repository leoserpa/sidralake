"""Teste de integracao E2E offline (Bronze -> Silver/SCD2 -> Gold -> Delta)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
import pytest
from deltalake import DeltaTable

from ibge_market_intel.config import PipelineSettings
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter
from ibge_market_intel.ingestion.schemas import (
    SIDRA_BRONZE_SCHEMA,
    parse_cnae_payload,
    parse_localidades_payload,
)
from ibge_market_intel.orchestration.assets_gold_export import (
    GOLD_EXPORT_TABLES,
    SILVER_EXPORT_TABLES,
    export_duckdb_tables_to_delta,
)
from ibge_market_intel.orchestration.definitions import defs
from ibge_market_intel.orchestration.resources import IBGEPipelineResource
from ibge_market_intel.quality.contracts import (
    validate_cnae_contract,
    validate_localidades_contract,
    validate_sidra_contract,
)


def _sidra_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    normalized = [
        {
            "agregado_id": r["agregado_id"],
            "variavel_id": r["variavel_id"],
            "variavel_nome": r.get("variavel_nome", "Variavel"),
            "unidade": r.get("unidade", "Unidade"),
            "localidade_id": str(r["localidade_id"]),
            "localidade_nome": r.get("localidade_nome", "Localidade"),
            "nivel_territorial": r["nivel_territorial"],
            "classificacao_1_id": r.get("classificacao_1_id", "NONE"),
            "categoria_1_id": r.get("categoria_1_id", "NONE"),
            "categoria_1_nome": r.get("categoria_1_nome", "Total"),
            "classificacao_2_id": r.get("classificacao_2_id", "NONE"),
            "categoria_2_id": r.get("categoria_2_id", "NONE"),
            "categoria_2_nome": r.get("categoria_2_nome", "Total"),
            "periodo_id": str(r["periodo_id"]),
            "ano_referencia": str(r["periodo_id"])[:4],
            "valor_bruto": str(r["valor_bruto"]),
        }
        for r in rows
    ]
    return pl.DataFrame(normalized, schema=SIDRA_BRONZE_SCHEMA)


@pytest.mark.integration
def test_full_medallion_pipeline_scd2_and_idempotency(
    tmp_path: Path,
    sample_localidades_payload: list[dict[str, Any]],
    sample_cnae_payload: list[dict[str, Any]],
) -> None:
    settings = PipelineSettings(
        data_dir=tmp_path / "data",
        bronze_dir=tmp_path / "data" / "bronze",
        silver_dir=tmp_path / "data" / "silver",
        gold_dir=tmp_path / "data" / "gold",
        duckdb_path=tmp_path / "data" / "warehouse" / "ibge_market_intel.duckdb",
    )
    settings.ensure_directories()
    writer = DeltaLakeWriter(settings.resolved_bronze_dir)

    # 1. Cadastros Bronze (inclui Boa Esperanca do Norte com microrregiao=None)
    loc_df = parse_localidades_payload(sample_localidades_payload)
    assert validate_localidades_contract(loc_df).passed
    writer.write_full_overwrite(
        loc_df, "localidades", ingestion_id="e2e-1", source_url="mock://loc"
    )

    cnae_df = parse_cnae_payload(sample_cnae_payload)
    assert validate_cnae_contract(cnae_df).passed
    writer.write_full_overwrite(
        cnae_df, "cnae_secoes", ingestion_id="e2e-1", source_url="mock://cnae"
    )

    # 2. PIB Municipal (5938) — anos 2022 e 2023 contabilmente consistentes (PIB = VAB + Impostos)
    pib_rows: list[dict[str, Any]] = []
    for ano, factor in (("2022", 1.0), ("2023", 1.08)):
        for mun_id, pib, imp, agro, ind, serv, adm in (
            ("3550308", 1000000, 200000, 10000, 190000, 500000, 100000),
            ("3509502", 200000, 40000, 5000, 55000, 80000, 20000),
        ):
            vab_total = agro + ind + serv + adm
            for vid, val in (
                (37, pib * factor),
                (543, imp * factor),
                (498, vab_total * factor),
                (513, agro * factor),
                (517, ind * factor),
                (6575, serv * factor),
                (525, adm * factor),
            ):
                pib_rows.append(
                    {
                        "agregado_id": 5938,
                        "variavel_id": vid,
                        "localidade_id": mun_id,
                        "nivel_territorial": "N6",
                        "periodo_id": ano,
                        "valor_bruto": f"{val:.1f}",
                    }
                )
        # Boa Esperanca do Norte sem PIB publicado ('...')
        pib_rows.append(
            {
                "agregado_id": 5938,
                "variavel_id": 37,
                "localidade_id": "5101837",
                "nivel_territorial": "N6",
                "periodo_id": ano,
                "valor_bruto": "...",
            }
        )

    for ano in ("2022", "2023"):
        part = _sidra_df([r for r in pib_rows if r["periodo_id"] == ano])
        assert validate_sidra_contract(part, "pib_municipal").passed
        writer.write_partition_overwrite(
            part,
            "pib_municipal",
            partition_col="ano_referencia",
            partition_value=ano,
            ingestion_id="e2e-1",
            source_url="mock://5938",
        )

    # 3. Censo 2022 (4714) + Estimativas 2024 (6579) -> gera interpolacao 2023 no Silver!
    censo_df = _sidra_df(
        [
            {
                "agregado_id": 4714,
                "variavel_id": 93,
                "localidade_id": "3550308",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "11450000",
            },
            {
                "agregado_id": 4714,
                "variavel_id": 6318,
                "localidade_id": "3550308",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "1521.1",
            },
            {
                "agregado_id": 4714,
                "variavel_id": 614,
                "localidade_id": "3550308",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "7527.4",
            },
            {
                "agregado_id": 4714,
                "variavel_id": 93,
                "localidade_id": "3509502",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "1139000",
            },
            {
                "agregado_id": 4714,
                "variavel_id": 6318,
                "localidade_id": "3509502",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "794.5",
            },
            {
                "agregado_id": 4714,
                "variavel_id": 614,
                "localidade_id": "3509502",
                "nivel_territorial": "N6",
                "periodo_id": "2022",
                "valor_bruto": "1433.6",
            },
        ]
    )
    assert validate_sidra_contract(censo_df, "censo_populacao").passed
    writer.write_partition_overwrite(
        censo_df,
        "censo_populacao",
        partition_col="ano_referencia",
        partition_value="2022",
        ingestion_id="e2e-1",
        source_url="mock://4714",
    )

    est_df = _sidra_df(
        [
            {
                "agregado_id": 6579,
                "variavel_id": 9324,
                "localidade_id": "3550308",
                "nivel_territorial": "N6",
                "periodo_id": "2024",
                "valor_bruto": "11850000",
            },
            {
                "agregado_id": 6579,
                "variavel_id": 9324,
                "localidade_id": "3509502",
                "nivel_territorial": "N6",
                "periodo_id": "2024",
                "valor_bruto": "1179000",
            },
            {
                "agregado_id": 6579,
                "variavel_id": 9324,
                "localidade_id": "5101837",
                "nivel_territorial": "N6",
                "periodo_id": "2024",
                "valor_bruto": "7500",
            },
        ]
    )
    assert validate_sidra_contract(est_df, "estimativa_populacao").passed
    writer.write_partition_overwrite(
        est_df,
        "estimativa_populacao",
        partition_col="ano_referencia",
        partition_value="2024",
        ingestion_id="e2e-1",
        source_url="mock://6579",
    )

    # 4. CEMPRE Municipal (9509) — 2022 e 2023
    cempre_rows: list[dict[str, Any]] = []
    for ano, mult in (("2022", 1.0), ("2023", 1.05)):
        for mun_id, emp, unid, po, assal, massa, sal_brl, sal_sm in (
            ("3550308", 950000, 1020000, 6200000, 5200000, 280000000, 4500.0, 3.4),
            ("3509502", 95000, 105000, 540000, 460000, 21000000, 3800.0, 2.9),
        ):
            for vid, val in (
                (706, int(unid * mult)),
                (367, int(emp * mult)),
                (707, int(po * mult)),
                (708, int(assal * mult)),
                (5944, int(assal * mult)),
                (662, round(massa * mult, 1)),
                (1606, sal_sm),
                (10143, sal_brl),
            ):
                cempre_rows.append(
                    {
                        "agregado_id": 9509,
                        "variavel_id": vid,
                        "localidade_id": mun_id,
                        "nivel_territorial": "N6",
                        "periodo_id": ano,
                        "valor_bruto": str(val),
                    }
                )
    for ano in ("2022", "2023"):
        part = _sidra_df([r for r in cempre_rows if r["periodo_id"] == ano])
        assert validate_sidra_contract(part, "cempre_municipal").passed
        writer.write_partition_overwrite(
            part,
            "cempre_municipal",
            partition_col="ano_referencia",
            partition_value=ano,
            ingestion_id="e2e-1",
            source_url="mock://9509",
        )

    # 5. CEMPRE Setorial UF (9418) com 'X' (sigilo estatistico) e '-' (zero exato)
    setorial_df = _sidra_df(
        [
            {
                "agregado_id": 9418,
                "variavel_id": 2585,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116910",
                "categoria_1_nome": "C Indústrias de transformação",
                "periodo_id": "2023",
                "valor_bruto": "120000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 707,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116910",
                "categoria_1_nome": "C Indústrias de transformação",
                "periodo_id": "2023",
                "valor_bruto": "2500000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 708,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116910",
                "categoria_1_nome": "C Indústrias de transformação",
                "periodo_id": "2023",
                "valor_bruto": "2200000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 662,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116910",
                "categoria_1_nome": "C Indústrias de transformação",
                "periodo_id": "2023",
                "valor_bruto": "95000000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 2585,
                "localidade_id": "51",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116830",
                "categoria_1_nome": "A Agricultura",
                "periodo_id": "2023",
                "valor_bruto": "15000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 707,
                "localidade_id": "51",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116830",
                "categoria_1_nome": "A Agricultura",
                "periodo_id": "2023",
                "valor_bruto": "180000",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 708,
                "localidade_id": "51",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116830",
                "categoria_1_nome": "A Agricultura",
                "periodo_id": "2023",
                "valor_bruto": "X",
            },
            {
                "agregado_id": 9418,
                "variavel_id": 662,
                "localidade_id": "51",
                "nivel_territorial": "N3",
                "classificacao_1_id": "12762",
                "categoria_1_id": "116830",
                "categoria_1_nome": "A Agricultura",
                "periodo_id": "2023",
                "valor_bruto": "-",
            },
        ]
    )
    assert validate_sidra_contract(setorial_df, "cempre_setorial_uf").passed
    writer.write_partition_overwrite(
        setorial_df,
        "cempre_setorial_uf",
        partition_col="ano_referencia",
        partition_value="2023",
        ingestion_id="e2e-1",
        source_url="mock://9418",
    )

    # 6. IPCA Mensal (1737)
    ipca_df = _sidra_df(
        [
            {
                "agregado_id": 1737,
                "variavel_id": 2266,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202212",
                "valor_bruto": "6474.09",
            },
            {
                "agregado_id": 1737,
                "variavel_id": 63,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202212",
                "valor_bruto": "0.62",
            },
            {
                "agregado_id": 1737,
                "variavel_id": 2265,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202212",
                "valor_bruto": "5.79",
            },
            {
                "agregado_id": 1737,
                "variavel_id": 2266,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202312",
                "valor_bruto": "6773.27",
            },
            {
                "agregado_id": 1737,
                "variavel_id": 63,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202312",
                "valor_bruto": "0.56",
            },
            {
                "agregado_id": 1737,
                "variavel_id": 2265,
                "localidade_id": "1",
                "nivel_territorial": "N1",
                "periodo_id": "202312",
                "valor_bruto": "4.62",
            },
        ]
    )
    assert validate_sidra_contract(ipca_df, "ipca_mensal").passed
    for ano in ("2022", "2023"):
        writer.write_partition_overwrite(
            ipca_df.filter(pl.col("ano_referencia") == ano),
            "ipca_mensal",
            partition_col="ano_referencia",
            partition_value=ano,
            ingestion_id="e2e-1",
            source_url="mock://1737",
        )

    # 7. PMC Varejo UF (8883)
    pmc_df = _sidra_df(
        [
            {
                "agregado_id": 8883,
                "variavel_id": 7169,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "85",
                "categoria_1_id": "103154",
                "categoria_1_nome": "Hipermercados e supermercados",
                "classificacao_2_id": "11046",
                "categoria_2_id": "56735",
                "categoria_2_nome": "Receita nominal",
                "periodo_id": "202312",
                "valor_bruto": "125.0",
            },
            {
                "agregado_id": 8883,
                "variavel_id": 11709,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "85",
                "categoria_1_id": "103154",
                "categoria_1_nome": "Hipermercados e supermercados",
                "classificacao_2_id": "11046",
                "categoria_2_id": "56735",
                "categoria_2_nome": "Receita nominal",
                "periodo_id": "202312",
                "valor_bruto": "8.5",
            },
            {
                "agregado_id": 8883,
                "variavel_id": 7169,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "85",
                "categoria_1_id": "103154",
                "categoria_1_nome": "Hipermercados e supermercados",
                "classificacao_2_id": "11046",
                "categoria_2_id": "56736",
                "categoria_2_nome": "Volume de vendas",
                "periodo_id": "202312",
                "valor_bruto": "118.0",
            },
            {
                "agregado_id": 8883,
                "variavel_id": 11709,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "85",
                "categoria_1_id": "103154",
                "categoria_1_nome": "Hipermercados e supermercados",
                "classificacao_2_id": "11046",
                "categoria_2_id": "56736",
                "categoria_2_nome": "Volume de vendas",
                "periodo_id": "202312",
                "valor_bruto": "3.5",
            },
            {
                "agregado_id": 8883,
                "variavel_id": 11711,
                "localidade_id": "35",
                "nivel_territorial": "N3",
                "classificacao_1_id": "85",
                "categoria_1_id": "103154",
                "categoria_1_nome": "Hipermercados e supermercados",
                "classificacao_2_id": "11046",
                "categoria_2_id": "56736",
                "categoria_2_nome": "Volume de vendas",
                "periodo_id": "202312",
                "valor_bruto": "4.0",
            },
        ]
    )
    assert validate_sidra_contract(pmc_df, "pmc_varejo_uf").passed
    writer.write_partition_overwrite(
        pmc_df,
        "pmc_varejo_uf",
        partition_col="ano_referencia",
        partition_value="2023",
        ingestion_id="e2e-1",
        source_url="mock://8883",
    )

    # 8. Executa dbt build completo (Silver + Snapshots SCD2 + Gold + Contracts + Tests)
    env = dict(os.environ)
    env["IBGE_BRONZE_DIR"] = settings.resolved_bronze_dir.as_posix()
    env["IBGE_DUCKDB_PATH"] = settings.resolved_duckdb_path.as_posix()
    dbt_dir = str(settings.resolved_dbt_project_dir)

    proc = subprocess.run(
        ["dbt", "build", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"dbt build falhou:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )

    # 9. Exporta Silver + Gold para Delta Lake e valida leitura via DuckDB delta_scan()
    pipeline_res = IBGEPipelineResource(data_dir=str(settings.resolved_data_dir))
    silver_export = export_duckdb_tables_to_delta(
        pipeline_res, schema="silver", tables=SILVER_EXPORT_TABLES, layer="silver", run_id="e2e-1"
    )
    gold_export = export_duckdb_tables_to_delta(
        pipeline_res, schema="gold", tables=GOLD_EXPORT_TABLES, layer="gold", run_id="e2e-1"
    )
    assert len(silver_export) == len(SILVER_EXPORT_TABLES)
    assert len(gold_export) == len(GOLD_EXPORT_TABLES)

    con = duckdb.connect(str(settings.resolved_duckdb_path), read_only=True)
    con.execute("LOAD delta;")
    try:
        # Verifica mart_inteligencia_mercado_municipal no Delta Lake Gold
        mart_path = (settings.resolved_gold_dir / "mart_inteligencia_mercado_municipal").as_posix()
        sp_2023 = con.execute(
            """
            select nome_municipio, is_populacao_interpolada, ims_score_0_100, rank_nacional_ims
            from delta_scan(?)
            where codigo_ibge_municipio = 3550308 and ano_referencia = 2023
            """,
            [mart_path],
        ).fetchone()
        assert sp_2023 is not None
        assert sp_2023[0] == "São Paulo"
        assert sp_2023[1] is True  # 2023 interpolado entre 2022 e 2024!
        assert 0.0 <= sp_2023[2] <= 100.0
        assert sp_2023[3] == 1

        # Verifica spread PMC x IPCA no mart_pulso_consumo_macro
        pulso = con.execute(
            "select spread_preco_vs_volume_yoy_pp, regime_consumo "
            "from gold.mart_pulso_consumo_macro"
        ).fetchone()
        assert pulso == (5.0, "EXPANSAO_REAL")
    finally:
        con.close()

    # 10. Prova SCD Type 2: altera nome de Campinas na Bronze e roda dbt snapshot + dim_geografia
    loc_updated = loc_df.with_columns(
        pl.when(pl.col("municipio_id") == 3509502)
        .then(pl.lit("Campinas (Renomeado SCD2)"))
        .otherwise(pl.col("municipio_nome"))
        .alias("municipio_nome")
    )
    writer.write_full_overwrite(
        loc_updated, "localidades", ingestion_id="e2e-2", source_url="mock://loc-v2"
    )
    proc_scd2 = subprocess.run(
        [
            "dbt",
            "build",
            "--select",
            "snap_ibge_municipios+",
            "--project-dir",
            dbt_dir,
            "--profiles-dir",
            dbt_dir,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_scd2.returncode == 0, f"SCD2 falhou:\n{proc_scd2.stdout}\n{proc_scd2.stderr}"

    con = duckdb.connect(str(settings.resolved_duckdb_path), read_only=True)
    try:
        campinas_versions = con.execute(
            """
            select nome_municipio, is_current, valid_to is not null as is_closed
            from gold.dim_geografia
            where codigo_ibge_municipio = 3509502
            order by valid_from
            """
        ).fetchall()
        assert len(campinas_versions) == 2
        assert campinas_versions[0] == ("Campinas", False, True)
        assert campinas_versions[1] == ("Campinas (Renomeado SCD2)", True, False)
    finally:
        con.close()

    # 11. Prova Idempotencia na Bronze: reescrever 2023 nao duplica linhas e avanca Delta version
    pib_2023 = _sidra_df([r for r in pib_rows if r["periodo_id"] == "2023"])
    v_before = DeltaTable(str(writer.table_path("pib_municipal"))).version()
    writer.write_partition_overwrite(
        pib_2023,
        "pib_municipal",
        partition_col="ano_referencia",
        partition_value="2023",
        ingestion_id="e2e-idempotent",
        source_url="mock://5938",
    )
    dt_after = DeltaTable(str(writer.table_path("pib_municipal")))
    assert dt_after.version() == v_before + 1
    assert dt_after.to_pyarrow_table(engine="datafusion").num_rows == len(pib_rows)

    # 12. Prova integridade do grafo Dagster unificado
    ag = defs.resolve_asset_graph()
    assert len(ag.external_asset_keys) == 0
    assert len(ag.materializable_asset_keys) == 39
