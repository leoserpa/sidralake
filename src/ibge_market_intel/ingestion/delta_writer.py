"""Escritor ACID Delta Lake com suporte a idempotencia, auditoria e manutencao."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from deltalake import DeltaTable, write_deltalake

from ibge_market_intel.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DeltaWriteResult:
    """Metadados retornados apos escrita ACID em Delta Lake."""

    table_path: Path
    delta_version: int
    rows_written: int
    payload_hash: str
    active_files_count: int
    total_size_bytes: int


def compute_dataframe_hash(df: pl.DataFrame) -> str:
    """Computa hash SHA-256 deterministico do conteudo tabular (excluindo colunas _*)."""
    business_cols = sorted(c for c in df.columns if not c.startswith("_"))
    if df.height == 0 or not business_cols:
        return hashlib.sha256(b"empty").hexdigest()

    sorted_df = df.select(business_cols).sort(business_cols)
    hasher = hashlib.sha256()
    # Serializa em IPC/CSV deterministico em memoria para hash rapido e reproduzivel
    hasher.update(",".join(business_cols).encode("utf-8"))
    hasher.update(sorted_df.write_csv().encode("utf-8"))
    return hasher.hexdigest()


def attach_audit_columns(
    df: pl.DataFrame,
    *,
    ingestion_id: str,
    source_url: str,
    payload_hash: str | None = None,
    ingested_at_utc: datetime | None = None,
) -> tuple[pl.DataFrame, str]:
    """Adiciona colunas imutaveis de auditoria e linhagem na camada Bronze."""
    resolved_hash = payload_hash or compute_dataframe_hash(df)
    ts = (ingested_at_utc or datetime.now(UTC)).isoformat()
    enriched = df.with_columns(
        pl.lit(ingestion_id).cast(pl.String()).alias("_ingestion_id"),
        pl.lit(ts).cast(pl.String()).alias("_ingested_at_utc"),
        pl.lit(source_url).cast(pl.String()).alias("_source_url"),
        pl.lit(resolved_hash).cast(pl.String()).alias("_payload_hash"),
    )
    return enriched, resolved_hash


def _inspect_delta_table(table_path: Path) -> tuple[int, int, int]:
    dt = DeltaTable(str(table_path))
    file_uris = dt.file_uris()
    total_bytes = sum(Path(uri).stat().st_size for uri in file_uris if Path(uri).exists())
    return dt.version(), len(file_uris), total_bytes


class DeltaLakeWriter:
    """Gerencia escritas ACID idempotentes (replace_where, overwrite, MERGE) e manutencao."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def table_path(self, table_name: str) -> Path:
        return self._base_dir / table_name

    def table_exists(self, table_name: str) -> bool:
        return (self.table_path(table_name) / "_delta_log").exists()

    def write_full_overwrite(
        self,
        df: pl.DataFrame,
        table_name: str,
        *,
        ingestion_id: str,
        source_url: str,
        partition_by: Sequence[str] | None = None,
    ) -> DeltaWriteResult:
        """Sobrescreve tabela completa mantendo historico ACID no _delta_log."""
        target = self.table_path(table_name)
        enriched, payload_hash = attach_audit_columns(
            df, ingestion_id=ingestion_id, source_url=source_url
        )
        write_deltalake(
            str(target),
            enriched.to_arrow(),
            mode="overwrite",
            partition_by=list(partition_by) if partition_by else None,
            schema_mode="overwrite",
        )
        version, files_cnt, size_bytes = _inspect_delta_table(target)
        logger.info(
            "delta_write_full_overwrite",
            table=table_name,
            delta_version=version,
            rows=enriched.height,
            files=files_cnt,
            size_bytes=size_bytes,
        )
        return DeltaWriteResult(
            table_path=target,
            delta_version=version,
            rows_written=enriched.height,
            payload_hash=payload_hash,
            active_files_count=files_cnt,
            total_size_bytes=size_bytes,
        )

    def write_partition_overwrite(
        self,
        df: pl.DataFrame,
        table_name: str,
        *,
        partition_col: str,
        partition_value: str,
        ingestion_id: str,
        source_url: str,
    ) -> DeltaWriteResult:
        """Substitui atomicamente uma unica particao (replace_where) de forma idempotente."""
        target = self.table_path(table_name)
        enriched, payload_hash = attach_audit_columns(
            df, ingestion_id=ingestion_id, source_url=source_url
        )
        escaped_val = partition_value.replace("'", "''")
        if not self.table_exists(table_name):
            write_deltalake(
                str(target),
                enriched.to_arrow(),
                mode="overwrite",
                partition_by=[partition_col],
            )
        else:
            write_deltalake(
                str(target),
                enriched.to_arrow(),
                mode="overwrite",
                predicate=f"{partition_col} = '{escaped_val}'",
            )
        version, files_cnt, size_bytes = _inspect_delta_table(target)
        logger.info(
            "delta_write_partition_overwrite",
            table=table_name,
            partition=f"{partition_col}={partition_value}",
            delta_version=version,
            rows=enriched.height,
            files=files_cnt,
        )
        return DeltaWriteResult(
            table_path=target,
            delta_version=version,
            rows_written=enriched.height,
            payload_hash=payload_hash,
            active_files_count=files_cnt,
            total_size_bytes=size_bytes,
        )

    def upsert_merge(
        self,
        df: pl.DataFrame,
        table_name: str,
        *,
        merge_keys: Sequence[str],
        ingestion_id: str,
        source_url: str,
        partition_by: Sequence[str] | None = None,
    ) -> DeltaWriteResult:
        """Executa MERGE ACID idempotente por chaves de negocio."""
        target = self.table_path(table_name)
        enriched, payload_hash = attach_audit_columns(
            df, ingestion_id=ingestion_id, source_url=source_url
        )
        if not self.table_exists(table_name):
            write_deltalake(
                str(target),
                enriched.to_arrow(),
                mode="overwrite",
                partition_by=list(partition_by) if partition_by else None,
            )
        else:
            dt = DeltaTable(str(target))
            predicate = " AND ".join(f"target.{k} = source.{k}" for k in merge_keys)
            (
                dt.merge(
                    source=enriched.to_arrow(),
                    predicate=predicate,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute()
            )
        version, files_cnt, size_bytes = _inspect_delta_table(target)
        logger.info(
            "delta_upsert_merge",
            table=table_name,
            delta_version=version,
            rows=enriched.height,
            files=files_cnt,
        )
        return DeltaWriteResult(
            table_path=target,
            delta_version=version,
            rows_written=enriched.height,
            payload_hash=payload_hash,
            active_files_count=files_cnt,
            total_size_bytes=size_bytes,
        )

    def maintain_table(
        self,
        table_name: str,
        *,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Executa OPTIMIZE (compactacao de small files) e VACUUM em uma tabela Delta."""
        target = self.table_path(table_name)
        if not self.table_exists(table_name):
            return {"table": table_name, "status": "skipped_missing"}

        dt = DeltaTable(str(target))
        compact_metrics = dt.optimize.compact()
        deleted_files = dt.vacuum(
            retention_hours=retention_hours,
            dry_run=dry_run,
            enforce_retention_duration=retention_hours >= 168,
        )
        summary = {
            "table": table_name,
            "delta_version": dt.version(),
            "num_files_added": compact_metrics.get("numFilesAdded", 0),
            "num_files_removed": compact_metrics.get("numFilesRemoved", 0),
            "vacuum_files_removed": len(deleted_files),
        }
        logger.info("delta_table_maintained", **summary)
        return summary
