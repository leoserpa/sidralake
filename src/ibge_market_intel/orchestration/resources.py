"""Dagster Resources tipados para acesso a API IBGE, Delta Lake e dbt-duckdb."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dagster import ConfigurableResource
from dagster_dbt import DbtCliResource, DbtProject

from ibge_market_intel.config import PipelineSettings, get_settings
from ibge_market_intel.ingestion.client import IBGEAsyncClient
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter


class IBGEPipelineResource(ConfigurableResource[Any]):
    """Resource central fornecendo configuracoes, cliente HTTP IBGE e escritores Delta Lake."""

    data_dir: str | None = None
    max_concurrency: int = 6
    uf_filter_csv: str = ""

    def build_settings(self) -> PipelineSettings:
        uf_filter: list[int] | None = None
        if self.uf_filter_csv.strip():
            uf_filter = [int(x.strip()) for x in self.uf_filter_csv.split(",") if x.strip()]

        kwargs: dict[str, object] = {"max_concurrency": self.max_concurrency}
        if self.data_dir:
            kwargs["data_dir"] = Path(self.data_dir)
        if uf_filter is not None:
            kwargs["uf_filter"] = uf_filter
        settings = PipelineSettings(**kwargs)  # type: ignore[arg-type]
        settings.ensure_directories()
        return settings

    def create_client(self) -> IBGEAsyncClient:
        return IBGEAsyncClient(self.build_settings())

    def bronze_writer(self) -> DeltaLakeWriter:
        return DeltaLakeWriter(self.build_settings().resolved_bronze_dir)

    def silver_writer(self) -> DeltaLakeWriter:
        return DeltaLakeWriter(self.build_settings().resolved_silver_dir)

    def gold_writer(self) -> DeltaLakeWriter:
        return DeltaLakeWriter(self.build_settings().resolved_gold_dir)


def create_dbt_project(settings: PipelineSettings | None = None) -> DbtProject:
    """Instancia o objeto DbtProject apontando para dbt_project/ sem poluir os.environ."""
    cfg = settings or get_settings()
    cfg.ensure_directories()
    return DbtProject(
        project_dir=cfg.resolved_dbt_project_dir,
        profiles_dir=cfg.resolved_dbt_project_dir,
    )


def create_dbt_cli_resource(settings: PipelineSettings | None = None) -> DbtCliResource:
    """Cria DbtCliResource configurado para o projeto dbt-duckdb."""
    cfg = settings or get_settings()
    return DbtCliResource(
        project_dir=str(cfg.resolved_dbt_project_dir),
        profiles_dir=str(cfg.resolved_dbt_project_dir),
    )
