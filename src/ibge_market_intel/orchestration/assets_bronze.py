"""Software-Defined Assets (Bronze) + Asset Checks bloqueantes (Pandera) no Dagster."""

import asyncio
from typing import Any

import polars as pl
from dagster import (
    AssetCheckExecutionContext,
    AssetCheckResult,
    AssetCheckSeverity,
    AssetExecutionContext,
    AssetKey,
    MaterializeResult,
    MetadataValue,
    asset,
    asset_check,
)
from deltalake import DeltaTable

from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_MUNICIPAL_SPEC,
    CEMPRE_SETORIAL_UF_SPEC,
    CENSO_POPULACAO_SPEC,
    ESTIMATIVA_POPULACAO_SPEC,
    IPCA_MENSAL_SPEC,
    PIB_MUNICIPAL_SPEC,
    PMC_VAREJO_UF_SPEC,
    AgregadoSpec,
)
from ibge_market_intel.orchestration.partitions import (
    CEMPRE_PARTITIONS,
    CENSO_PARTITIONS,
    ESTIMATIVA_POP_PARTITIONS,
    IPCA_PARTITIONS,
    PIB_PARTITIONS,
    PMC_PARTITIONS,
)
from ibge_market_intel.orchestration.resources import IBGEPipelineResource
from ibge_market_intel.quality.contracts import (
    QualityReport,
    validate_cnae_contract,
    validate_localidades_contract,
    validate_sidra_contract,
)


def _read_bronze_delta(pipeline: IBGEPipelineResource, table_name: str) -> pl.DataFrame:
    path = pipeline.bronze_writer().table_path(table_name)
    dt = DeltaTable(str(path))
    df = pl.from_arrow(dt.to_pyarrow_table(engine="datafusion"))
    if not isinstance(df, pl.DataFrame):
        raise TypeError(f"Esperado pl.DataFrame ao ler {table_name}, recebido {type(df)!r}")
    return df


def _quality_to_check_result(report: QualityReport) -> AssetCheckResult:
    return AssetCheckResult(
        passed=report.passed,
        severity=AssetCheckSeverity.ERROR,
        description=report.error_message
        or f"Contrato Pandera validado para {report.dataset_name}.",
        metadata={
            "row_count": MetadataValue.int(report.row_count),
            "distinct_localidades": MetadataValue.int(report.distinct_localidades),
            "duplicate_key_rows": MetadataValue.int(report.duplicate_key_rows),
            "invalid_value_rows": MetadataValue.int(report.invalid_value_rows),
            "secrecy_x_rate_pct": MetadataValue.float(round(report.secrecy_x_rate * 100.0, 4)),
            "unavailable_rate_pct": MetadataValue.float(round(report.unavailable_rate * 100.0, 4)),
            "exact_zero_rate_pct": MetadataValue.float(round(report.exact_zero_rate * 100.0, 4)),
        },
    )


async def _ingest_sidra_partition(
    pipeline: IBGEPipelineResource,
    spec: AgregadoSpec,
    ano: str,
    run_id: str,
) -> dict[str, Any]:
    settings = pipeline.build_settings()
    async with pipeline.create_client() as client:
        fetch_res = await client.fetch_agregado_for_year(
            spec,
            ano=ano,
            uf_codes=settings.uf_filter,
        )

    if fetch_res.df.height == 0:
        return {
            "rows_written": 0,
            "delta_version": -1,
            "size_kb": 0.0,
            "requests_made": fetch_res.requests_made,
            "elapsed_seconds": fetch_res.elapsed_seconds,
            "payload_hash": "empty",
        }

    report = validate_sidra_contract(fetch_res.df, spec.table_name)
    if not report.passed:
        raise ValueError(
            f"Circuit Breaker Pandera acionado em bronze/{spec.table_name} ({ano}): "
            f"{report.error_message}"
        )

    source_summary = fetch_res.source_urls[0] if fetch_res.source_urls else ""
    write_res = pipeline.bronze_writer().write_partition_overwrite(
        fetch_res.df,
        spec.table_name,
        partition_col="ano_referencia",
        partition_value=ano,
        ingestion_id=run_id,
        source_url=source_summary,
    )
    return {
        "rows_written": write_res.rows_written,
        "delta_version": write_res.delta_version,
        "size_kb": round(write_res.total_size_bytes / 1024.0, 2),
        "requests_made": fetch_res.requests_made,
        "elapsed_seconds": fetch_res.elapsed_seconds,
        "payload_hash": write_res.payload_hash,
        "secrecy_x_rate_pct": round(report.secrecy_x_rate * 100.0, 4),
        "unavailable_rate_pct": round(report.unavailable_rate * 100.0, 4),
    }


def _to_materialize_result(metrics: dict[str, Any]) -> MaterializeResult[Any]:
    return MaterializeResult(
        metadata={
            k: (
                MetadataValue.int(v)
                if isinstance(v, int)
                else MetadataValue.float(v)
                if isinstance(v, float)
                else MetadataValue.text(str(v))
            )
            for k, v in metrics.items()
        }
    )


@asset(
    key_prefix=["bronze"],
    name="localidades",
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="Cadastro completo de municipios brasileiros (/api/v1/localidades/municipios).",
)
def bronze_localidades(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    settings = pipeline.build_settings()

    async def _run() -> dict[str, Any]:
        async with pipeline.create_client() as client:
            res = await client.fetch_localidades(uf_codes=settings.uf_filter)
        report = validate_localidades_contract(res.df)
        if not report.passed:
            raise ValueError(f"Contrato Pandera falhou em localidades: {report.error_message}")
        write_res = pipeline.bronze_writer().write_full_overwrite(
            res.df,
            "localidades",
            ingestion_id=context.run_id,
            source_url=res.source_urls[0],
        )
        return {
            "rows_written": write_res.rows_written,
            "delta_version": write_res.delta_version,
            "size_kb": round(write_res.total_size_bytes / 1024.0, 2),
            "elapsed_seconds": res.elapsed_seconds,
            "payload_hash": write_res.payload_hash,
        }

    return _to_materialize_result(asyncio.run(_run()))


@asset(
    key_prefix=["bronze"],
    name="cnae_secoes",
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="21 secoes oficiais da CNAE 2.0 (/api/v2/cnae/secoes) + mapeamento SIDRA 12762.",
)
def bronze_cnae_secoes(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    async def _run() -> dict[str, Any]:
        async with pipeline.create_client() as client:
            res = await client.fetch_cnae_secoes()
        report = validate_cnae_contract(res.df)
        if not report.passed:
            raise ValueError(f"Contrato Pandera falhou em cnae_secoes: {report.error_message}")
        write_res = pipeline.bronze_writer().write_full_overwrite(
            res.df,
            "cnae_secoes",
            ingestion_id=context.run_id,
            source_url=res.source_urls[0],
        )
        return {
            "rows_written": write_res.rows_written,
            "delta_version": write_res.delta_version,
            "size_kb": round(write_res.total_size_bytes / 1024.0, 2),
            "elapsed_seconds": res.elapsed_seconds,
            "payload_hash": write_res.payload_hash,
        }

    return _to_materialize_result(asyncio.run(_run()))


@asset(
    key_prefix=["bronze"],
    name="pib_municipal",
    partitions_def=PIB_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 5938: PIB Municipal e VAB por setor com chunking assincrono por UF.",
)
def bronze_pib_municipal(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(pipeline, PIB_MUNICIPAL_SPEC, context.partition_key, context.run_id)
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="censo_populacao",
    partitions_def=CENSO_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 4714: Censo Demografico 2022 (populacao, area km2 e densidade).",
)
def bronze_censo_populacao(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(
            pipeline, CENSO_POPULACAO_SPEC, context.partition_key, context.run_id
        )
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="estimativa_populacao",
    partitions_def=ESTIMATIVA_POP_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 6579: Estimativas anuais de populacao residente municipal.",
)
def bronze_estimativa_populacao(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(
            pipeline, ESTIMATIVA_POPULACAO_SPEC, context.partition_key, context.run_id
        )
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="cempre_municipal",
    partitions_def=CEMPRE_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 9509 (nova serie 2022+): empresas, emprego e salarios por municipio.",
)
def bronze_cempre_municipal(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(
            pipeline, CEMPRE_MUNICIPAL_SPEC, context.partition_key, context.run_id
        )
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="cempre_setorial_uf",
    partitions_def=CEMPRE_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 9418 (nova serie 2022+): CEMPRE por UF e 21 secoes CNAE 2.0.",
)
def bronze_cempre_setorial_uf(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(
            pipeline, CEMPRE_SETORIAL_UF_SPEC, context.partition_key, context.run_id
        )
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="ipca_mensal",
    partitions_def=IPCA_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 1737: Serie historica mensal do IPCA Brasil.",
)
def bronze_ipca_mensal(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(pipeline, IPCA_MENSAL_SPEC, context.partition_key, context.run_id)
    )
    return _to_materialize_result(metrics)


@asset(
    key_prefix=["bronze"],
    name="pmc_varejo_uf",
    partitions_def=PMC_PARTITIONS,
    group_name="bronze",
    kinds={"python", "polars", "deltalake"},
    description="SIDRA 8883: PMC varejo ampliado por UF, receita/volume e 14 atividades.",
)
def bronze_pmc_varejo_uf(
    context: AssetExecutionContext,
    pipeline: IBGEPipelineResource,
) -> MaterializeResult[Any]:
    metrics = asyncio.run(
        _ingest_sidra_partition(pipeline, PMC_VAREJO_UF_SPEC, context.partition_key, context.run_id)
    )
    return _to_materialize_result(metrics)


# ==================== ASSET CHECKS BLOQUEANTES (CIRCUIT BREAKERS) ====================


@asset_check(
    asset=AssetKey(["bronze", "localidades"]),
    name="pandera_contract_localidades",
    blocking=True,
)
def check_bronze_localidades(
    context: AssetCheckExecutionContext,
    pipeline: IBGEPipelineResource,
) -> AssetCheckResult:
    _ = context
    df = _read_bronze_delta(pipeline, "localidades")
    return _quality_to_check_result(validate_localidades_contract(df))


@asset_check(
    asset=AssetKey(["bronze", "cnae_secoes"]),
    name="pandera_contract_cnae_secoes",
    blocking=True,
)
def check_bronze_cnae_secoes(
    context: AssetCheckExecutionContext,
    pipeline: IBGEPipelineResource,
) -> AssetCheckResult:
    _ = context
    df = _read_bronze_delta(pipeline, "cnae_secoes")
    return _quality_to_check_result(validate_cnae_contract(df))


def _make_sidra_check(table_name: str) -> Any:
    @asset_check(
        asset=AssetKey(["bronze", table_name]),
        name=f"pandera_contract_{table_name}",
        blocking=True,
    )
    def _check(
        context: AssetCheckExecutionContext,
        pipeline: IBGEPipelineResource,
    ) -> AssetCheckResult:
        _ = context
        df = _read_bronze_delta(pipeline, table_name)
        return _quality_to_check_result(validate_sidra_contract(df, table_name))

    return _check


BRONZE_ASSETS = [
    bronze_localidades,
    bronze_cnae_secoes,
    bronze_pib_municipal,
    bronze_censo_populacao,
    bronze_estimativa_populacao,
    bronze_cempre_municipal,
    bronze_cempre_setorial_uf,
    bronze_ipca_mensal,
    bronze_pmc_varejo_uf,
]

BRONZE_ASSET_CHECKS = [
    check_bronze_localidades,
    check_bronze_cnae_secoes,
    *(
        _make_sidra_check(t)
        for t in (
            "pib_municipal",
            "censo_populacao",
            "estimativa_populacao",
            "cempre_municipal",
            "cempre_setorial_uf",
            "ipca_mensal",
            "pmc_varejo_uf",
        )
    ),
]
