"""Testes unitarios de orquestracao Dagster (Definitions, Translator, Sensors, Checks e Exports)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
import pytest
from dagster import (
    AssetKey,
    Definitions,
    SensorResult,
    SkipReason,
    build_asset_check_context,
    build_op_context,
    build_sensor_context,
)

from ibge_market_intel.orchestration.assets_bronze import (
    BRONZE_ASSET_CHECKS,
    check_bronze_cnae_secoes,
    check_bronze_localidades,
)
from ibge_market_intel.orchestration.assets_dbt import IBGEDataTranslator
from ibge_market_intel.orchestration.assets_gold_export import (
    export_duckdb_tables_to_delta,
    maintain_delta_lakehouse_op,
)
from ibge_market_intel.orchestration.definitions import defs
from ibge_market_intel.orchestration.resources import IBGEPipelineResource
from ibge_market_intel.orchestration.sensors import build_schedules, ibge_new_period_sensor


def test_dagster_definitions_validate_loadable() -> None:
    Definitions.validate_loadable(defs)
    asset_graph = defs.resolve_asset_graph()
    all_keys = asset_graph.get_all_asset_keys()
    assert AssetKey(["bronze", "localidades"]) in all_keys
    assert AssetKey(["lakehouse", "silver_delta_export"]) in all_keys
    assert AssetKey(["lakehouse", "gold_delta_export"]) in all_keys
    assert len(BRONZE_ASSET_CHECKS) == 9


def test_ibge_dbt_translator_asset_keys_and_groups() -> None:
    translator = IBGEDataTranslator()

    assert translator.get_asset_key(
        {
            "resource_type": "source",
            "name": "pib_municipal",
            "meta": {"dagster": {"asset_key": ["bronze", "pib_municipal"]}},
        }
    ) == AssetKey(["bronze", "pib_municipal"])
    assert translator.get_asset_key(
        {"resource_type": "snapshot", "name": "snap_ibge_municipios"}
    ) == AssetKey(["silver", "snapshots", "snap_ibge_municipios"])
    assert translator.get_asset_key(
        {
            "resource_type": "model",
            "name": "stg_ibge__pib_municipal",
            "fqn": ["ibge_market_intel", "silver", "staging", "stg_ibge__pib_municipal"],
        }
    ) == AssetKey(["silver", "stg_ibge__pib_municipal"])
    assert translator.get_asset_key(
        {
            "resource_type": "model",
            "name": "mart_inteligencia_mercado_municipal",
            "fqn": ["ibge_market_intel", "gold", "marts", "mart_inteligencia_mercado_municipal"],
        }
    ) == AssetKey(["gold", "mart_inteligencia_mercado_municipal"])

    assert translator.get_group_name({"resource_type": "snapshot"}) == "silver_scd2"
    assert translator.get_group_name({"fqn": ["silver", "staging", "x"]}) == "silver_staging"
    assert (
        translator.get_group_name({"fqn": ["silver", "intermediate", "x"]}) == "silver_intermediate"
    )
    assert translator.get_group_name({"fqn": ["gold", "dimensions", "x"]}) == "gold_dimensions"
    assert translator.get_group_name({"fqn": ["gold", "facts", "x"]}) == "gold_facts"
    assert translator.get_group_name({"fqn": ["gold", "marts", "x"]}) == "gold_marts"
    assert translator.get_group_name({"fqn": ["other", "x"]}) == "dbt"


def test_ibge_new_period_sensor_emits_runs_skips_unchanged_and_guards_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_periods: dict[int, list[str]] = {
        1737: ["202401", "202506"],
        8883: ["202401", "202506"],
        5938: ["2022", "2023"],
        9509: ["2022", "2024"],
        9418: ["2022", "2099"],  # Ano fora das particoes estaticas -> deve ignorar sem falhar
    }

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def fetch_available_periods(
            self, agregado_id: int, *, use_cache: bool = True
        ) -> list[str]:
            _ = use_cache
            return fake_periods[agregado_id]

    pipeline = IBGEPipelineResource(data_dir=str(tmp_path))
    monkeypatch.setattr(IBGEPipelineResource, "create_client", lambda self: _FakeClient())

    # 1. Primeira avaliacao (sem cursor): gera RunRequests apenas para periodos elegiveis
    ctx1 = build_sensor_context()
    res1 = ibge_new_period_sensor(ctx1, pipeline=pipeline)
    assert isinstance(res1, SensorResult)
    assert res1.run_requests is not None
    run_keys = {rr.run_key for rr in res1.run_requests}
    assert run_keys == {
        "ipca_mensal-202506",
        "pmc_varejo_uf-202506",
        "pib_municipal-2023",
        "cempre_municipal-2024",
    }
    assert res1.cursor is not None
    cursor_data = json.loads(res1.cursor)
    assert "cempre_setorial_uf" not in cursor_data

    # 2. Segunda avaliacao com mesmo estado: retorna SkipReason
    ctx2 = build_sensor_context(cursor=res1.cursor)
    res2 = ibge_new_period_sensor(ctx2, pipeline=pipeline)
    assert isinstance(res2, SkipReason)


def test_build_schedules_configuration() -> None:
    schedules = build_schedules(
        macro_job_name="macro_refresh_job",
        maintenance_job_name="delta_maintenance_job",
    )
    assert len(schedules) == 2
    assert {s.name for s in schedules} == {
        "monthly_macro_refresh_schedule",
        "weekly_delta_maintenance_schedule",
    }
    assert all(s.execution_timezone == "America/Sao_Paulo" for s in schedules)


def test_export_duckdb_tables_to_delta_and_allowlist_security(tmp_path: Path) -> None:
    pipeline = IBGEPipelineResource(data_dir=str(tmp_path))
    settings = pipeline.build_settings()
    settings.ensure_directories()

    con = duckdb.connect(str(settings.resolved_duckdb_path))
    try:
        con.execute("create schema gold;")
        con.execute("create table gold.dim_tempo as select 202401 as sk_tempo, 2024 as ano;")
    finally:
        con.close()

    exported = export_duckdb_tables_to_delta(
        pipeline,
        schema="gold",
        tables=("dim_tempo",),
        layer="gold",
        run_id="unit-export-001",
    )
    assert exported["dim_tempo"]["rows"] == 1
    assert (settings.resolved_gold_dir / "dim_tempo" / "_delta_log").exists()

    with pytest.raises(ValueError, match="Schema nao autorizado"):
        export_duckdb_tables_to_delta(
            pipeline,
            schema="main; drop table x",
            tables=("dim_tempo",),
            layer="gold",
            run_id="bad-schema",
        )

    with pytest.raises(ValueError, match="Tabela nao autorizada"):
        export_duckdb_tables_to_delta(
            pipeline,
            schema="gold",
            tables=("tabela_inexistente",),
            layer="gold",
            run_id="bad-table",
        )


def test_maintain_delta_lakehouse_op_and_bronze_asset_checks(tmp_path: Path) -> None:
    pipeline = IBGEPipelineResource(data_dir=str(tmp_path))
    bronze_writer = pipeline.bronze_writer()

    df_loc = pl.DataFrame(
        {
            "municipio_id": [3550308],
            "municipio_nome": ["São Paulo"],
            "uf_id": [35],
            "uf_sigla": ["SP"],
            "uf_nome": ["São Paulo"],
            "regiao_id": [3],
            "regiao_sigla": ["SE"],
            "regiao_nome": ["Sudeste"],
            "regiao_imediata_id": [350001],
            "regiao_imediata_nome": ["São Paulo"],
            "regiao_intermediaria_id": [3501],
            "regiao_intermediaria_nome": ["São Paulo"],
            "microrregiao_id": [35061],
            "microrregiao_nome": ["São Paulo"],
            "mesorregiao_id": [3515],
            "mesorregiao_nome": ["Metropolitana de São Paulo"],
        }
    )
    bronze_writer.write_full_overwrite(
        df_loc, "localidades", ingestion_id="t1", source_url="https://ibge.test/loc"
    )

    df_cnae = pl.DataFrame(
        {
            "secao_codigo": ["A"],
            "secao_descricao": ["AGRICULTURA"],
            "categoria_sidra_12762_id": [117897],
            "observacoes": [""],
        }
    )
    bronze_writer.write_full_overwrite(
        df_cnae, "cnae_secoes", ingestion_id="t1", source_url="https://ibge.test/cnae"
    )

    loc_check = check_bronze_localidades(build_asset_check_context(), pipeline)
    assert loc_check.passed is True

    cnae_check = check_bronze_cnae_secoes(build_asset_check_context(), pipeline)
    assert cnae_check.passed is True

    op_ctx = build_op_context()
    maint = maintain_delta_lakehouse_op(op_ctx, pipeline)
    assert len(maint["bronze"]) == 2
    assert {item["table"] for item in maint["bronze"]} == {"localidades", "cnae_secoes"}
