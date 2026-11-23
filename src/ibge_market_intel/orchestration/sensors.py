"""Sensors de frescor (Freshness Sensor na API IBGE) e Schedules no Dagster."""

import asyncio
import json

from dagster import (
    AssetKey,
    RunRequest,
    ScheduleDefinition,
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    StaticPartitionsDefinition,
    sensor,
)

from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_MUNICIPAL_SPEC,
    CEMPRE_SETORIAL_UF_SPEC,
    IPCA_MENSAL_SPEC,
    PIB_MUNICIPAL_SPEC,
    PMC_VAREJO_UF_SPEC,
)
from ibge_market_intel.orchestration.partitions import (
    CEMPRE_PARTITIONS,
    IPCA_PARTITIONS,
    PIB_PARTITIONS,
    PMC_PARTITIONS,
)
from ibge_market_intel.orchestration.resources import IBGEPipelineResource

_MONITORED_SOURCES: tuple[tuple[str, int, StaticPartitionsDefinition], ...] = (
    ("ipca_mensal", IPCA_MENSAL_SPEC.agregado_id, IPCA_PARTITIONS),
    ("pmc_varejo_uf", PMC_VAREJO_UF_SPEC.agregado_id, PMC_PARTITIONS),
    ("pib_municipal", PIB_MUNICIPAL_SPEC.agregado_id, PIB_PARTITIONS),
    ("cempre_municipal", CEMPRE_MUNICIPAL_SPEC.agregado_id, CEMPRE_PARTITIONS),
    ("cempre_setorial_uf", CEMPRE_SETORIAL_UF_SPEC.agregado_id, CEMPRE_PARTITIONS),
)


@sensor(
    name="ibge_new_period_sensor",
    minimum_interval_seconds=3600,
    description=(
        "Monitora /api/v3/agregados/{id}/periodos no IBGE para detectar automaticamente "
        "novas competencias publicadas (IPCA, PMC, PIB, CEMPRE) e disparar materializacao."
    ),
    asset_selection=[AssetKey(["bronze", name]) for name, _, _ in _MONITORED_SOURCES],
)
def ibge_new_period_sensor(
    context: SensorEvaluationContext,
    pipeline: IBGEPipelineResource,
) -> SensorResult | SkipReason:
    previous_state: dict[str, str] = json.loads(context.cursor) if context.cursor else {}
    new_state: dict[str, str] = dict(previous_state)
    run_requests: list[RunRequest] = []
    partitions_by_name = {name: part_def for name, _, part_def in _MONITORED_SOURCES}

    async def _poll_latest() -> dict[str, str]:
        latest_map: dict[str, str] = {}
        async with pipeline.create_client() as client:
            for name, agregado_id, _ in _MONITORED_SOURCES:
                periods = await client.fetch_available_periods(agregado_id, use_cache=False)
                if periods:
                    latest_map[name] = max(periods)
        return latest_map

    latest_periods = asyncio.run(_poll_latest())

    for name, latest in latest_periods.items():
        if previous_state.get(name) != latest:
            partition_year = latest[:4]
            part_def = partitions_by_name[name]
            if not part_def.has_partition_key(partition_year):
                context.log.warning(
                    f"Nova competencia IBGE {latest} em '{name}' fora das particoes "
                    f"estaticas configuradas ({part_def.get_partition_keys()}); "
                    "atualize catalogs.py para habilitar materializacao automatica."
                )
                continue
            run_requests.append(
                RunRequest(
                    run_key=f"{name}-{latest}",
                    asset_selection=[AssetKey(["bronze", name])],
                    partition_key=partition_year,
                    tags={"trigger": "ibge_freshness_sensor", "latest_period": latest},
                )
            )
            new_state[name] = latest

    cursor_json = json.dumps(new_state, sort_keys=True)
    if not run_requests:
        return SkipReason(f"Nenhuma nova competencia elegivel detectada no IBGE: {latest_periods}")
    return SensorResult(run_requests=run_requests, cursor=cursor_json)


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
