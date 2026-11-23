"""Ponto de entrada unificado do Dagster (assets, checks, jobs, sensors, schedules, resources)."""

from __future__ import annotations

from dagster import AssetSelection, Definitions, define_asset_job, job

from ibge_market_intel.orchestration.assets_bronze import BRONZE_ASSET_CHECKS, BRONZE_ASSETS
from ibge_market_intel.orchestration.assets_dbt import ibge_dbt_medallion_assets
from ibge_market_intel.orchestration.assets_gold_export import (
    gold_delta_export,
    maintain_delta_lakehouse_op,
    silver_delta_export,
)
from ibge_market_intel.orchestration.resources import (
    IBGEPipelineResource,
    create_dbt_cli_resource,
)
from ibge_market_intel.orchestration.sensors import build_schedules, ibge_new_period_sensor

dbt_medallion_job = define_asset_job(
    name="dbt_medallion_job",
    selection=AssetSelection.assets(
        ibge_dbt_medallion_assets,
        silver_delta_export,
        gold_delta_export,
    ),
    description="Executa dbt build (Silver + SCD2 + Gold + Testes) e exporta Delta Lake.",
)

macro_refresh_job = define_asset_job(
    name="macro_refresh_job",
    selection=AssetSelection.assets(
        ibge_dbt_medallion_assets,
        gold_delta_export,
    ),
    description="Recompila modelos Silver/Gold e exporta camada Gold Delta Lake.",
)


@job(description="Job de manutencao ACID (OPTIMIZE + VACUUM) em todas as tabelas Delta Lake.")
def delta_maintenance_job() -> None:
    maintain_delta_lakehouse_op()


defs = Definitions(
    assets=[
        *BRONZE_ASSETS,
        ibge_dbt_medallion_assets,
        silver_delta_export,
        gold_delta_export,
    ],
    asset_checks=[*BRONZE_ASSET_CHECKS],
    jobs=[dbt_medallion_job, macro_refresh_job, delta_maintenance_job],
    schedules=build_schedules(
        macro_job_name="macro_refresh_job",
        maintenance_job_name="delta_maintenance_job",
    ),
    sensors=[ibge_new_period_sensor],
    resources={
        "pipeline": IBGEPipelineResource(),
        "dbt": create_dbt_cli_resource(),
    },
)
