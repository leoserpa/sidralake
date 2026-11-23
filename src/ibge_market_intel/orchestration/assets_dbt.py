"""Integracao nativa dagster-dbt trazendo Silver, Snapshots SCD2 e Gold ao grafo Dagster."""

from collections.abc import Iterator, Mapping
from typing import Any

from dagster import AssetExecutionContext, AssetKey
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

from ibge_market_intel.orchestration.resources import create_dbt_project

dbt_project = create_dbt_project()
dbt_project.prepare_if_dev()


class IBGEDataTranslator(DagsterDbtTranslator):
    """Mapeia fontes Bronze para os AssetKeys Python e agrupa modelos por camada Medalhao."""

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        resource_type = dbt_resource_props.get("resource_type")
        if resource_type == "source":
            meta_key = dbt_resource_props.get("meta", {}).get("dagster", {}).get("asset_key")
            if meta_key:
                return AssetKey(meta_key)
        fqn = dbt_resource_props.get("fqn", [])
        name = str(dbt_resource_props.get("name", "unknown"))
        if resource_type == "snapshot":
            return AssetKey(["silver", "snapshots", name])
        if "silver" in fqn:
            return AssetKey(["silver", name])
        if "gold" in fqn:
            return AssetKey(["gold", name])
        return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        resource_type = dbt_resource_props.get("resource_type")
        fqn = dbt_resource_props.get("fqn", [])
        if resource_type == "snapshot":
            return "silver_scd2"
        if "staging" in fqn:
            return "silver_staging"
        if "intermediate" in fqn:
            return "silver_intermediate"
        if "dimensions" in fqn:
            return "gold_dimensions"
        if "facts" in fqn:
            return "gold_facts"
        if "marts" in fqn:
            return "gold_marts"
        return "dbt"


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=IBGEDataTranslator(),
)
def ibge_dbt_medallion_assets(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> Iterator[Any]:
    """Executa dbt build (Silver + SCD2 Snapshots + Gold + Contracts + Tests)."""
    yield from dbt.cli(["build"], context=context).stream()
