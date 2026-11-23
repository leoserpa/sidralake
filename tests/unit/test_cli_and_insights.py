"""Testes unitarios da camada analitica Polars Lazy (insights) e da CLI SidraLake."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import pytest

from ibge_market_intel import cli
from ibge_market_intel.analytics.insights import build_market_insights, format_insights_report
from ibge_market_intel.config import PipelineSettings
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter


def _seed_gold_delta_tables(gold_dir: Path) -> None:
    writer = DeltaLakeWriter(gold_dir)

    mart_mun = pl.DataFrame(
        {
            "codigo_ibge_municipio": [3550308, 5103403, 3500105],
            "nome_municipio": ["São Paulo", "Cuiabá", "Adamantina"],
            "sigla_uf": ["SP", "MT", "SP"],
            "ano_referencia": [2023, 2023, 2023],
            "is_ultimo_ano_completo": [True, True, True],
            "populacao_residente": [12_000_000, 650_000, 35_000],
            "pib_real_mil_brl": [900_000_000.0, 40_000_000.0, 1_500_000.0],
            "pib_per_capita_real_brl": [75_000.0, 61_538.0, 42_857.0],
            "cagr_pib_real_3a_pct": [3.5, 9.2, 12.0],
            "ims_score_0_100": [88.5, 76.2, 54.0],
            "rank_nacional_ims": [1, 2, 3],
            "tier_mercado": [
                "Tier 1 - Polo Nacional",
                "Tier 2 - Expansao Prioritaria",
                "Tier 4 - Local / Nicho",
            ],
        }
    )
    writer.write_full_overwrite(
        mart_mun,
        "mart_inteligencia_mercado_municipal",
        ingestion_id="seed-1",
        source_url="test://mart_mun",
    )

    mart_clusters = pl.DataFrame(
        {
            "sigla_uf": ["MT", "SP"],
            "codigo_secao_cnae": ["A", "J"],
            "descricao_secao_cnae": ["AGRICULTURA E PECUARIA", "INFORMACAO E COMUNICACAO"],
            "ano_referencia": [2024, 2024],
            "pessoal_ocupado_total": [180_000, 740_000],
            "quociente_locacional_emprego": [2.45, 1.65],
            "market_share_uf_no_setor_pct": [18.5, 43.2],
            "perfil_especializacao": ["CLUSTER_DOMINANTE", "CLUSTER_DOMINANTE"],
        }
    )
    writer.write_full_overwrite(
        mart_clusters,
        "mart_clusters_setoriais_uf",
        ingestion_id="seed-1",
        source_url="test://mart_clusters",
    )

    mart_pulso = pl.DataFrame(
        {
            "sigla_uf": ["SP", "MT", "SP"],
            "ano_mes": ["202609", "202609", "202609"],
            "ano_referencia": [2026, 2026, 2026],
            "var_yoy_volume_pct": [4.5, -3.0, None],
            "spread_preco_vs_volume_yoy_pp": [2.0, 1.5, None],
            "regime_consumo": ["EXPANSAO_REAL", "RETRACAO", "SEM_DADO"],
        }
    )
    writer.write_full_overwrite(
        mart_pulso,
        "mart_pulso_consumo_macro",
        ingestion_id="seed-1",
        source_url="test://mart_pulso",
    )


def test_build_market_insights_and_uf_filter(tmp_path: Path) -> None:
    gold_dir = tmp_path / "gold"
    _seed_gold_delta_tables(gold_dir)

    report = build_market_insights(gold_dir, top_n=5)
    assert report.top_municipalities.height == 3
    assert report.top_municipalities["municipio"].to_list() == ["São Paulo", "Cuiabá", "Adamantina"]
    # Adamantina tem pop < 50k -> filtrada do ranking de CAGR
    assert report.fastest_growing["municipio"].to_list() == ["Cuiabá", "São Paulo"]
    assert report.dominant_clusters["uf"].to_list() == ["MT", "SP"]
    assert "SEM_DADO" not in report.retail_pulse["regime_consumo"].to_list()

    rendered = format_insights_report(report)
    assert "TOP MUNICIPIOS POR SCORE IMS" in rendered
    assert "Cuiabá" in rendered

    # Garante que relatorios com >25 linhas nao sejam truncados pelo Polars
    wide_df = pl.DataFrame(
        {"rank": list(range(1, 31)), "municipio": [f"Mun-{i}" for i in range(1, 31)]}
    )
    wide_rendered = format_insights_report(
        type(report)(
            top_municipalities=wide_df,
            fastest_growing=report.fastest_growing,
            dominant_clusters=report.dominant_clusters,
            retail_pulse=report.retail_pulse,
        )
    )
    assert "Mun-15" in wide_rendered
    assert "Mun-30" in wide_rendered

    sp_report = build_market_insights(gold_dir, top_n=5, uf="sp", year=2023)
    assert sp_report.top_municipalities["uf"].to_list() == ["SP", "SP"]

    with pytest.raises(ValueError, match="top_n deve ser >= 1"):
        build_market_insights(gold_dir, top_n=0)

    with pytest.raises(FileNotFoundError, match="nao encontrada"):
        build_market_insights(tmp_path / "missing_gold")


def test_cli_dispatch_insights_and_maintain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = PipelineSettings(data_dir=tmp_path)
    settings.ensure_directories()
    _seed_gold_delta_tables(settings.resolved_gold_dir)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    cli.main(["insights", "--top", "2", "--uf", "SP"])
    out = capsys.readouterr().out
    assert "São Paulo" in out
    assert "Cuiabá" not in out

    cli.main(["maintain"])

    called: list[str] = []
    monkeypatch.setattr(cli, "run_pipeline", lambda *, mode: called.append(f"run:{mode}"))
    monkeypatch.setattr(cli, "run_quality_suite", lambda: called.append("test"))
    monkeypatch.setattr(cli, "inspect_gold", lambda: called.append("inspect"))
    cli.main(["run", "--mode", "smoke"])
    cli.main(["test"])
    cli.main(["inspect"])
    assert called == ["run:smoke", "test", "inspect"]


def test_cli_inspect_gold_runs_against_duckdb_warehouse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = PipelineSettings(data_dir=tmp_path)
    settings.ensure_directories()
    _seed_gold_delta_tables(settings.resolved_gold_dir)

    con = duckdb.connect(str(settings.resolved_duckdb_path))
    try:
        con.execute("create schema gold;")
        con.execute(
            """
            create table gold.mart_inteligencia_mercado_municipal as
            select
                1 as rank_nacional_ims, 'São Paulo' as nome_municipio, 'SP' as sigla_uf,
                2023 as ano_referencia, 12000000 as populacao_residente,
                900000000.0 as pib_real_mil_brl, 75000.0 as pib_per_capita_real_brl,
                700000 as num_empresas_atuantes, 5500.0 as salario_medio_real_brl,
                88.5 as ims_score_0_100, 'Tier 1 - Polo Nacional' as tier_mercado,
                true as is_ultimo_ano_completo
            """
        )
        con.execute(
            """
            create table gold.dim_geografia as
            select
                5101837 as codigo_ibge_municipio, 'Boa Esperança do Norte' as nome_municipio,
                'MT' as sigla_uf, 'Sorriso' as nome_regiao_imediata,
                null::integer as codigo_microrregiao, true as is_current
            """
        )
        con.execute(
            """
            create table gold.mart_clusters_setoriais_uf as
            select
                'MT' as sigla_uf, 'A' as codigo_secao_cnae, 'AGRICULTURA' as descricao_secao_cnae,
                2024 as ano_referencia, 180000 as pessoal_ocupado_total,
                2.45 as quociente_locacional_emprego, 18.5 as market_share_uf_no_setor_pct,
                'CLUSTER_DOMINANTE' as perfil_especializacao
            """
        )
        con.execute(
            """
            create table gold.mart_pulso_consumo_macro as
            select
                '202609' as ano_mes, 'SP' as sigla_uf, 103154 as codigo_atividade_pmc,
                'Comercio varejista' as nome_atividade_pmc, 4.5 as var_yoy_volume_pct,
                6.5 as var_yoy_receita_nominal_pct, 2.0 as spread_preco_vs_volume_yoy_pp,
                4.2 as ipca_variacao_acum_12m_pct, 'EXPANSAO_REAL' as regime_consumo
            """
        )
    finally:
        con.close()

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    cli.inspect_gold()
    out = capsys.readouterr().out
    assert "TOP 15 MUNICIPIOS POR SCORE IMS" in out
    assert "Boa Esperança do Norte" in out
    assert "gold/mart_inteligencia_mercado_municipal" in out
