"""Exportacao otimizada em Parquet (via Polars Lazy API) para o dashboard Evidence.dev."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from ibge_market_intel.logging import get_logger

logger = get_logger(__name__)

BI_GOLD_TABLES: tuple[str, ...] = (
    "mart_inteligencia_mercado_municipal",
    "mart_clusters_setoriais_uf",
    "mart_pulso_consumo_macro",
    "dim_geografia",
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
        if table_name == "dim_geografia":
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
