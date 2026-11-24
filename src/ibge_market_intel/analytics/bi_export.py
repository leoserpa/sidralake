"""Exportacao otimizada em Parquet (via Polars Lazy API) para o dashboard Evidence.dev."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from ibge_market_intel.logging import get_logger

logger = get_logger(__name__)

BI_GOLD_TABLES: tuple[str, ...] = (
    "mart_inteligencia_mercado_municipal",
    "mart_clusters_setoriais_uf",
    "mart_pulso_consumo_macro",
    "mart_pulso_servicos_uf",
    "mart_mercado_trabalho_uf",
    "fct_populacao_municipal",
    "fct_ipca_mensal",
    "dim_geografia",
    "dim_cnae",
)


def export_gold_for_bi(
    gold_dir: Path,
    output_dir: Path,
) -> dict[str, dict[str, int | float | str]]:
    """Exporta tabelas Gold Delta Lake para Parquet Snappy (compativel com Evidence/DuckDB-WASM)."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, int | float | str]] = {}

    for table_name in BI_GOLD_TABLES:
        delta_path = gold_dir / table_name
        if not (delta_path / "_delta_log").exists():
            raise FileNotFoundError(
                f"Tabela Delta Gold '{table_name}' nao encontrada em {delta_path}. "
                "Execute 'uv run sidralake run --mode full' antes de exportar para BI."
            )

        lf = pl.scan_delta(str(delta_path))
        if table_name in ("dim_geografia", "dim_cnae"):
            lf = lf.filter(pl.col("is_current"))
        drop_audit = [c for c in lf.collect_schema().names() if c.startswith("_")]
        if drop_audit:
            lf = lf.drop(drop_audit)

        df = lf.collect()
        target_parquet = output_dir / f"{table_name}.parquet"
        df.write_parquet(target_parquet, compression="snappy")

        size_kb = round(target_parquet.stat().st_size / 1024.0, 2)
        summary[table_name] = {
            "rows": df.height,
            "size_kb": size_kb,
            "path": str(target_parquet),
        }
        logger.info(
            "bi_parquet_exported",
            table=table_name,
            rows=df.height,
            size_kb=size_kb,
            path=str(target_parquet),
        )

    return summary


def write_bi_freshness_manifest(
    parquet_dir: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Extrai a competencia mais recente de cada fonte BI e grava manifesto JSON de frescor."""
    parquet_dir = parquet_dir.resolve()
    manifest_path = manifest_path.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def _max_str(table: str, col: str, *, non_null_col: str | None = None) -> str | None:
        path = parquet_dir / f"{table}.parquet"
        if not path.exists():
            return None
        lf = pl.scan_parquet(path)
        if non_null_col is not None:
            lf = lf.filter(pl.col(non_null_col).is_not_null())
        val = lf.select(pl.col(col).max()).collect().item()
        return str(val) if val is not None else None

    payload: dict[str, Any] = {
        "refreshed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest_periods": {
            "ipca_mensal": _max_str("fct_ipca_mensal", "ano_mes"),
            "pmc_varejo_uf": _max_str("mart_pulso_consumo_macro", "ano_mes"),
            "pms_servicos_uf": _max_str("mart_pulso_servicos_uf", "ano_mes"),
            "pnad_trabalho_uf": _max_str("mart_mercado_trabalho_uf", "ano_trimestre"),
            "pib_municipal": _max_str(
                "mart_inteligencia_mercado_municipal",
                "ano_referencia",
                non_null_col="pib_real_mil_brl",
            ),
            "cempre_setorial_uf": _max_str("mart_clusters_setoriais_uf", "ano_referencia"),
            "populacao_municipal": _max_str("fct_populacao_municipal", "ano_referencia"),
        },
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
