"""Exportacao ACID das camadas Silver e Gold do DuckDB para Delta Lake + Manutencao Lakehouse."""

from typing import Any

import duckdb
import polars as pl
from dagster import (
    AssetExecutionContext,
    AssetKey,
    MaterializeResult,
    MetadataValue,
    OpExecutionContext,
    asset,
    op,
)

from ibge_market_intel.orchestration.resources import IBGEPipelineResource

SILVER_EXPORT_TABLES: tuple[str, ...] = (
    "int_populacao_municipal_unificada",
    "int_ipca_deflator_anual",
    "int_pib_municipal_deflacionado",
    "int_cempre_municipal_deflacionado",
)

GOLD_EXPORT_TABLES: tuple[str, ...] = (
    "dim_geografia",
    "dim_tempo",
    "dim_cnae",
    "dim_atividade_varejo",
    "fct_pib_municipal",
    "fct_populacao_municipal",
    "fct_cempre_municipal",
    "fct_cempre_setorial_uf",
    "fct_ipca_mensal",
    "fct_pmc_varejo_mensal",
    "mart_inteligencia_mercado_municipal",
    "mart_clusters_setoriais_uf",
    "mart_pulso_consumo_macro",
)


def export_duckdb_tables_to_delta(
    pipeline: IBGEPipelineResource,
    *,
    schema: str,
    tables: tuple[str, ...],
    layer: str,
    run_id: str,
) -> dict[str, dict[str, Any]]:
    """Exporta tabelas DuckDB via Arrow zero-copy para Delta Lake ACID (Silver ou Gold)."""
    settings = pipeline.build_settings()
    writer = pipeline.gold_writer() if layer == "gold" else pipeline.silver_writer()
    results: dict[str, dict[str, Any]] = {}

    allowed_schemas = {"silver", "gold"}
    allowed_tables = set(SILVER_EXPORT_TABLES) | set(GOLD_EXPORT_TABLES)
    if schema not in allowed_schemas:
        raise ValueError(f"Schema nao autorizado para exportacao: {schema!r}")

    con = duckdb.connect(str(settings.resolved_duckdb_path), read_only=True)
    try:
        for table in tables:
            if table not in allowed_tables:
                raise ValueError(f"Tabela nao autorizada para exportacao: {table!r}")
            arrow_tbl = con.table(f"{schema}.{table}").to_arrow_table()
            df = pl.from_arrow(arrow_tbl)
            if not isinstance(df, pl.DataFrame):
                raise TypeError(f"Esperado pl.DataFrame para {schema}.{table}")
            res = writer.write_full_overwrite(
                df,
                table,
                ingestion_id=run_id,
                source_url=f"duckdb://{schema}.{table}",
            )
            results[table] = {
                "rows": res.rows_written,
                "delta_version": res.delta_version,
                "size_kb": round(res.total_size_bytes / 1024.0, 2),
                "path": str(res.table_path),
            }
    finally:
        con.close()

    return results


@asset(
    key_prefix=["lakehouse"],
    name="silver_delta_export",
    deps=[AssetKey(["silver", t]) for t in SILVER_EXPORT_TABLES],
    group_name="lakehouse_export",
    kinds={"duckdb", "deltalake"},
    description="Exporta modelos Silver curados do DuckDB para formato aberto Delta Lake.",
)
def silver_delta_export(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    summary = export_duckdb_tables_to_delta(
        pipeline,
        schema="silver",
        tables=SILVER_EXPORT_TABLES,
        layer="silver",
        run_id=context.run_id,
    )
    total_rows = sum(v["rows"] for v in summary.values())
    return MaterializeResult(
        metadata={
            "tables_exported": MetadataValue.int(len(summary)),
            "total_rows": MetadataValue.int(total_rows),
            "details": MetadataValue.json(summary),
        }
    )


@asset(
    key_prefix=["lakehouse"],
    name="gold_delta_export",
    deps=[AssetKey(["gold", t]) for t in GOLD_EXPORT_TABLES],
    group_name="lakehouse_export",
    kinds={"duckdb", "deltalake"},
    description="Exporta Star Schema e Marts OBT Gold do DuckDB para Delta Lake ACID.",
)
def gold_delta_export(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    summary = export_duckdb_tables_to_delta(
        pipeline,
        schema="gold",
        tables=GOLD_EXPORT_TABLES,
        layer="gold",
        run_id=context.run_id,
    )
    total_rows = sum(v["rows"] for v in summary.values())
    return MaterializeResult(
        metadata={
            "tables_exported": MetadataValue.int(len(summary)),
            "total_rows": MetadataValue.int(total_rows),
            "details": MetadataValue.json(summary),
        }
    )


@op(description="Executa OPTIMIZE (compaction) e VACUUM em todas as tabelas Delta do Lakehouse.")
def maintain_delta_lakehouse_op(
    context: OpExecutionContext,
    pipeline: IBGEPipelineResource,
) -> dict[str, Any]:
    """Manutencao periodica de tabelas Delta (Bronze, Silver, Gold) contra small files."""
    summary: dict[str, list[dict[str, Any]]] = {"bronze": [], "silver": [], "gold": []}
    writers = (
        ("bronze", pipeline.bronze_writer()),
        ("silver", pipeline.silver_writer()),
        ("gold", pipeline.gold_writer()),
    )
    for layer_name, writer in writers:
        base_dir = writer.table_path(".").parent
        if not base_dir.exists():
            continue
        for child in sorted(base_dir.iterdir()):
            if child.is_dir() and (child / "_delta_log").exists():
                res = writer.maintain_table(child.name, retention_hours=168, dry_run=False)
                summary[layer_name].append(res)
    context.log.info(f"Manutencao Delta Lake concluida: {summary}")
    return summary
