"""Consultas analiticas one-shot via Polars Lazy API (scan_delta) sobre a camada Gold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True)
class MarketInsightsReport:
    """Resultado estruturado das consultas analiticas sobre os marts Gold Delta Lake."""

    top_municipalities: pl.DataFrame
    fastest_growing: pl.DataFrame
    dominant_clusters: pl.DataFrame
    retail_pulse: pl.DataFrame


def _scan_gold_table(gold_dir: Path, table_name: str) -> pl.LazyFrame:
    table_path = gold_dir / table_name
    if not (table_path / "_delta_log").exists():
        raise FileNotFoundError(
            f"Tabela Delta Gold '{table_name}' nao encontrada em {table_path}. "
            "Execute 'uv run sidralake run --mode full' antes de rodar insights."
        )
    return pl.scan_delta(str(table_path))


def build_market_insights(
    gold_dir: Path,
    *,
    top_n: int = 10,
    uf: str | None = None,
    year: int | None = None,
    min_population_growth: int = 50_000,
) -> MarketInsightsReport:
    """Executa consultas Lazy Polars diretamente nas tabelas Gold Delta Lake."""
    if top_n < 1:
        raise ValueError("top_n deve ser >= 1")
    uf_norm = uf.strip().upper() if uf else None

    mart_mun = _scan_gold_table(gold_dir, "mart_inteligencia_mercado_municipal")
    mun_filter = (
        pl.col("ano_referencia") == year if year is not None else pl.col("is_ultimo_ano_completo")
    )
    if uf_norm is not None:
        mun_filter = mun_filter & (pl.col("sigla_uf") == uf_norm)

    top_municipalities = (
        mart_mun.filter(mun_filter & pl.col("ims_score_0_100").is_not_null())
        .sort(["rank_nacional_ims", "codigo_ibge_municipio"])
        .select(
            pl.col("rank_nacional_ims").alias("rank"),
            pl.col("nome_municipio").alias("municipio"),
            pl.col("sigla_uf").alias("uf"),
            pl.col("ano_referencia").alias("ano"),
            pl.col("populacao_residente").alias("populacao"),
            (pl.col("pib_real_mil_brl") / 1_000_000.0).round(2).alias("pib_real_bi"),
            pl.col("pib_per_capita_real_brl").round(0).alias("pib_pc_real"),
            pl.col("ims_score_0_100").alias("ims"),
            pl.col("tier_mercado").alias("tier"),
        )
        .limit(top_n)
        .collect()
    )

    fastest_growing = (
        mart_mun.filter(
            mun_filter
            & pl.col("cagr_pib_real_3a_pct").is_not_null()
            & (pl.col("populacao_residente") >= min_population_growth)
        )
        .sort("cagr_pib_real_3a_pct", descending=True)
        .select(
            pl.col("nome_municipio").alias("municipio"),
            pl.col("sigla_uf").alias("uf"),
            pl.col("ano_referencia").alias("ano"),
            pl.col("populacao_residente").alias("populacao"),
            pl.col("cagr_pib_real_3a_pct").round(2).alias("cagr_3a_pct"),
            (pl.col("pib_real_mil_brl") / 1_000_000.0).round(2).alias("pib_real_bi"),
            pl.col("ims_score_0_100").alias("ims"),
        )
        .limit(top_n)
        .collect()
    )

    mart_clusters = _scan_gold_table(gold_dir, "mart_clusters_setoriais_uf")
    cluster_filter = (
        pl.col("ano_referencia") == year
        if year is not None
        else pl.col("ano_referencia") == pl.col("ano_referencia").max()
    )
    cluster_filter = cluster_filter & pl.col("pessoal_ocupado_total").is_not_null()
    if uf_norm is not None:
        cluster_filter = cluster_filter & (pl.col("sigla_uf") == uf_norm)

    dominant_clusters = (
        mart_clusters.filter(cluster_filter)
        .sort(
            [
                "quociente_locacional_emprego",
                "market_share_uf_no_setor_pct",
                "pessoal_ocupado_total",
            ],
            descending=[True, True, True],
            nulls_last=True,
        )
        .select(
            pl.col("sigla_uf").alias("uf"),
            pl.col("codigo_secao_cnae").alias("cnae"),
            pl.col("descricao_secao_cnae").str.slice(0, 42).alias("setor"),
            pl.col("ano_referencia").alias("ano"),
            pl.col("pessoal_ocupado_total").alias("emprego"),
            pl.col("quociente_locacional_emprego").round(2).alias("ql_emprego"),
            pl.col("market_share_uf_no_setor_pct").round(2).alias("share_br_pct"),
            pl.col("perfil_especializacao").alias("perfil"),
        )
        .limit(top_n)
        .collect()
    )

    mart_pulso = _scan_gold_table(gold_dir, "mart_pulso_consumo_macro")
    pulso_filter = (
        pl.col("ano_referencia") == year
        if year is not None
        else pl.col("ano_mes") == pl.col("ano_mes").max()
    )
    pulso_filter = pulso_filter & (pl.col("regime_consumo") != "SEM_DADO")
    if uf_norm is not None:
        pulso_filter = pulso_filter & (pl.col("sigla_uf") == uf_norm)

    retail_pulse = (
        mart_pulso.filter(pulso_filter)
        .group_by(["ano_mes", "regime_consumo"])
        .agg(
            pl.len().alias("series_uf_atividade"),
            pl.col("var_yoy_volume_pct").mean().round(2).alias("vol_yoy_medio_pct"),
            pl.col("spread_preco_vs_volume_yoy_pp").mean().round(2).alias("spread_medio_pp"),
        )
        .sort(["ano_mes", "series_uf_atividade"], descending=[True, True])
        .limit(top_n)
        .collect()
    )

    return MarketInsightsReport(
        top_municipalities=top_municipalities,
        fastest_growing=fastest_growing,
        dominant_clusters=dominant_clusters,
        retail_pulse=retail_pulse,
    )


def format_insights_report(report: MarketInsightsReport) -> str:
    """Renderiza relatorio tabular legivel no terminal a partir dos DataFrames Polars."""
    with pl.Config(tbl_rows=-1, tbl_cols=12, tbl_width_chars=140, tbl_hide_dataframe_shape=True):
        sections = [
            "=== 1. TOP MUNICIPIOS POR SCORE IMS (POLARS LAZY / DELTA GOLD) ===",
            str(report.top_municipalities),
            "\n=== 2. MAIOR DINAMISMO REAL (CAGR PIB 3A, POP >= 50 MIL) ===",
            str(report.fastest_growing),
            "\n=== 3. LIDERANCA E CLUSTERS SETORIAIS ESTADUAIS (CNAE 2.0 / CEMPRE) ===",
            str(report.dominant_clusters),
            "\n=== 4. PULSO DO VAREJO AMPLIADO POR REGIME DE CONSUMO (PMC x IPCA) ===",
            str(report.retail_pulse),
        ]
        return "\n".join(sections)
