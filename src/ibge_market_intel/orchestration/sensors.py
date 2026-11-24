"""Sensors de frescor (Freshness Sensor na API IBGE) e Schedules no Dagster."""

import asyncio
import json

from dagster import (
    AddDynamicPartitionsRequest,
    AssetKey,
    DynamicPartitionsDefinition,
    RunRequest,
    ScheduleDefinition,
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    sensor,
)

from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_MUNICIPAL_SPEC,
    CEMPRE_SETORIAL_UF_SPEC,
    CENSO_POPULACAO_SPEC,
    ESTIMATIVA_POPULACAO_SPEC,
    IPCA_MENSAL_SPEC,
    PIB_MUNICIPAL_SPEC,
    PMC_VAREJO_UF_SPEC,
    PMS_SERVICOS_UF_SPEC,
    PNAD_DESOCUPACAO_UF_SPEC,
    PNAD_RENDIMENTO_UF_SPEC,
    AgregadoSpec,
)
from ibge_market_intel.orchestration.partitions import (
    CEMPRE_PARTITIONS,
    CENSO_PARTITIONS,
    ESTIMATIVA_POP_PARTITIONS,
    IPCA_PARTITIONS,
    PIB_PARTITIONS,
    PMC_PARTITIONS,
    PMS_PARTITIONS,
    PNAD_PARTITIONS,
)
from ibge_market_intel.orchestration.resources import IBGEPipelineResource

_MONITORED_SOURCES: tuple[tuple[AgregadoSpec, DynamicPartitionsDefinition], ...] = (
    (IPCA_MENSAL_SPEC, IPCA_PARTITIONS),
    (PMC_VAREJO_UF_SPEC, PMC_PARTITIONS),
    (PMS_SERVICOS_UF_SPEC, PMS_PARTITIONS),
    (PNAD_DESOCUPACAO_UF_SPEC, PNAD_PARTITIONS),
    (PNAD_RENDIMENTO_UF_SPEC, PNAD_PARTITIONS),
    (PIB_MUNICIPAL_SPEC, PIB_PARTITIONS),
    (CEMPRE_MUNICIPAL_SPEC, CEMPRE_PARTITIONS),
    (CEMPRE_SETORIAL_UF_SPEC, CEMPRE_PARTITIONS),
    (ESTIMATIVA_POPULACAO_SPEC, ESTIMATIVA_POP_PARTITIONS),
    (CENSO_POPULACAO_SPEC, CENSO_PARTITIONS),
)


@sensor(
    name="ibge_new_period_sensor",
    minimum_interval_seconds=3600,
    description=(
        "Monitora /api/v3/agregados/{id}/periodos no IBGE para detectar automaticamente "
        "novas competencias publicadas (IPCA, PMC, PIB, CEMPRE, Populacao), registrar "
        "particoes dinamicas e disparar materializacao sem intervencao manual."
    ),
    asset_selection=[AssetKey(["bronze", spec.table_name]) for spec, _ in _MONITORED_SOURCES],
)
def ibge_new_period_sensor(
    context: SensorEvaluationContext,
    pipeline: IBGEPipelineResource,
) -> SensorResult | SkipReason:
    previous_state: dict[str, str] = json.loads(context.cursor) if context.cursor else {}
    new_state: dict[str, str] = dict(previous_state)
    run_requests: list[RunRequest] = []
    partitions_to_add: dict[str, tuple[DynamicPartitionsDefinition, set[str]]] = {}
    sources_by_name = {spec.table_name: (spec, part_def) for spec, part_def in _MONITORED_SOURCES}

    async def _poll_latest() -> dict[str, str]:
        latest_map: dict[str, str] = {}
        async with pipeline.create_client() as client:
            for spec, _ in _MONITORED_SOURCES:
                periods = await client.fetch_available_periods(spec.agregado_id, use_cache=False)
                eligible = [
                    p
                    for p in periods
                    if len(p) >= 4 and p[:4].isdigit() and int(p[:4]) >= spec.min_year
                ]
                if eligible:
                    latest_map[spec.table_name] = max(eligible)
        return latest_map

    latest_periods = asyncio.run(_poll_latest())

    for name, latest in latest_periods.items():
        if previous_state.get(name) != latest:
            partition_year = latest[:4]
            _, part_def = sources_by_name[name]
            part_name = part_def.name or name
            if part_name not in partitions_to_add:
                partitions_to_add[part_name] = (part_def, set())
            partitions_to_add[part_name][1].add(partition_year)

            run_requests.append(
                RunRequest(
                    run_key=f"{name}-{latest}",
                    asset_selection=[AssetKey(["bronze", name])],
                    partition_key=partition_year,
                    tags={"trigger": "ibge_freshness_sensor", "latest_period": latest},
                )
            )
            new_state[name] = latest

    dynamic_requests: list[AddDynamicPartitionsRequest] = [
        part_def.build_add_request(sorted(keys))
        for part_def, keys in partitions_to_add.values()
        if keys
    ]

    cursor_json = json.dumps(new_state, sort_keys=True)
    if not run_requests:
        return SkipReason(f"Nenhuma nova competencia elegivel detectada no IBGE: {latest_periods}")
    return SensorResult(
        run_requests=run_requests,
        cursor=cursor_json,
        dynamic_partitions_requests=dynamic_requests,
    )


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
