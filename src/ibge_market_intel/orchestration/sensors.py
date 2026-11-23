"""Sensors de frescor (Freshness Sensor na API IBGE) e Schedules no Dagster."""

import asyncio
import json

from dagster import (
    AssetKey,
    RunRequest,
    ScheduleDefinition,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_MUNICIPAL_SPEC,
    IPCA_MENSAL_SPEC,
    PIB_MUNICIPAL_SPEC,
    PMC_VAREJO_UF_SPEC,
)
from ibge_market_intel.orchestration.resources import IBGEPipelineResource

_MONITORED_SOURCES = (
    ("ipca_mensal", IPCA_MENSAL_SPEC.agregado_id),
    ("pmc_varejo_uf", PMC_VAREJO_UF_SPEC.agregado_id),
    ("pib_municipal", PIB_MUNICIPAL_SPEC.agregado_id),
    ("cempre_municipal", CEMPRE_MUNICIPAL_SPEC.agregado_id),
)


@sensor(
    name="ibge_new_period_sensor",
    minimum_interval_seconds=3600,
    description=(
        "Monitora /api/v3/agregados/{id}/periodos no IBGE para detectar automaticamente "
        "novas competencias publicadas (IPCA, PMC, PIB, CEMPRE) e disparar materializacao."
    ),
    asset_selection=[AssetKey(["bronze", name]) for name, _ in _MONITORED_SOURCES],
)
def ibge_new_period_sensor(
    context: SensorEvaluationContext,
    pipeline: IBGEPipelineResource,
) -> list[RunRequest] | SkipReason:
    previous_state: dict[str, str] = json.loads(context.cursor) if context.cursor else {}
    new_state: dict[str, str] = dict(previous_state)
    run_requests: list[RunRequest] = []

    async def _poll_latest() -> dict[str, str]:
        latest_map: dict[str, str] = {}
        async with pipeline.create_client() as client:
            for name, agregado_id in _MONITORED_SOURCES:
                periods = await client.fetch_available_periods(agregado_id, use_cache=False)
                if periods:
                    latest_map[name] = max(periods)
        return latest_map

    latest_periods = asyncio.run(_poll_latest())

    for name, latest in latest_periods.items():
        if previous_state.get(name) != latest:
            partition_year = latest[:4]
            run_requests.append(
                RunRequest(
                    run_key=f"{name}-{latest}",
                    asset_selection=[AssetKey(["bronze", name])],
                    partition_key=partition_year,
                    tags={"trigger": "ibge_freshness_sensor", "latest_period": latest},
                )
            )
            new_state[name] = latest

    context.update_cursor(json.dumps(new_state, sort_keys=True))
    if not run_requests:
        return SkipReason(f"Nenhuma nova competencia detectada no IBGE: {latest_periods}")
    return run_requests


def build_schedules(
    macro_job_name: str,
    maintenance_job_name: str,
) -> list[ScheduleDefinition]:
    """Schedules recorrentes (atualizacao macro mensal e manutencao Delta semanal)."""
    return [
        ScheduleDefinition(
            name="monthly_macro_refresh_schedule",
            job_name=macro_job_name,
            cron_schedule="0 8 15 * *",
            execution_timezone="America/Sao_Paulo",
            description="Atualiza IPCA, PMC e camada Gold todo dia 15 apos divulgacao do IBGE.",
        ),
        ScheduleDefinition(
            name="weekly_delta_maintenance_schedule",
            job_name=maintenance_job_name,
            cron_schedule="0 3 * * 0",
            execution_timezone="America/Sao_Paulo",
            description="Executa OPTIMIZE e VACUUM semanal nas tabelas Delta Lake.",
        ),
    ]
