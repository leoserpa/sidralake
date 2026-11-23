"""Configuracoes centralizadas do pipeline IBGE Market Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class PipelineSettings(BaseSettings):
    """Configuracoes carregadas via variaveis de ambiente com prefixo IBGE_."""

    model_config = SettingsConfigDict(
        env_prefix="IBGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = Field(default_factory=_default_project_root)
    data_dir: Path | None = None
    bronze_dir: Path | None = None
    silver_dir: Path | None = None
    gold_dir: Path | None = None
    duckdb_path: Path | None = None
    dbt_project_dir: Path | None = None

    ibge_base_url: str = "https://servicodados.ibge.gov.br/api"
    max_concurrency: int = Field(default=6, ge=1, le=20)
    request_timeout_s: float = Field(default=40.0, ge=5.0, le=180.0)
    retry_max_attempts: int = Field(default=5, ge=1, le=10)
    user_agent: str = "ibge-market-intel/0.1.0 (+data-engineering-lakehouse)"
    log_format: str = Field(default="json", pattern="^(json|console)$")
    log_level: str = "INFO"

    # Opcional: restringir UFs (ex: [35] ou [35, 33]) para modo smoke/dev
    uf_filter: list[int] | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_data_dir(self) -> Path:
        return (self.data_dir or (self.project_root / "data")).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_bronze_dir(self) -> Path:
        return (self.bronze_dir or (self.resolved_data_dir / "bronze")).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_silver_dir(self) -> Path:
        return (self.silver_dir or (self.resolved_data_dir / "silver")).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_gold_dir(self) -> Path:
        return (self.gold_dir or (self.resolved_data_dir / "gold")).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_duckdb_path(self) -> Path:
        return (
            self.duckdb_path or (self.resolved_data_dir / "warehouse" / "ibge_market_intel.duckdb")
        ).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_dbt_project_dir(self) -> Path:
        return (self.dbt_project_dir or (self.project_root / "dbt_project")).resolve()

    def ensure_directories(self) -> None:
        """Garante que os diretorios locais do Lakehouse existam."""
        for directory in (
            self.resolved_bronze_dir,
            self.resolved_silver_dir,
            self.resolved_gold_dir,
            self.resolved_duckdb_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def get_settings() -> PipelineSettings:
    """Factory padrao de configuracoes."""
    return PipelineSettings()
