"""Testes unitarios dos contratos Pandera (circuit breakers da camada Bronze)."""

from __future__ import annotations

from typing import Any

import polars as pl

from ibge_market_intel.ingestion.schemas import (
    flatten_sidra_response,
    parse_cnae_payload,
    parse_localidades_payload,
)
from ibge_market_intel.quality.contracts import (
    validate_cnae_contract,
    validate_localidades_contract,
    validate_sidra_contract,
)


def test_valid_localidades_and_cnae_contracts_pass(
    sample_localidades_payload: list[dict[str, Any]],
    sample_cnae_payload: list[dict[str, Any]],
) -> None:
    loc_report = validate_localidades_contract(
        parse_localidades_payload(sample_localidades_payload)
    )
    cnae_report = validate_cnae_contract(parse_cnae_payload(sample_cnae_payload))

    assert loc_report.passed is True
    assert loc_report.row_count == 3
    assert cnae_report.passed is True
    assert cnae_report.row_count == 3


def test_localidades_contract_rejects_invalid_uf_or_duplicate_id(
    sample_localidades_payload: list[dict[str, Any]],
) -> None:
    df = parse_localidades_payload(sample_localidades_payload)
    corrupted = df.with_columns(pl.lit("ZZ").alias("uf_sigla"))
    report = validate_localidades_contract(corrupted)
    assert report.passed is False
    assert report.error_message is not None


def test_sidra_contract_tracks_ibge_special_codes_and_passes(
    sample_sidra_pmc_payload: list[dict[str, Any]],
) -> None:
    df = flatten_sidra_response(8883, sample_sidra_pmc_payload)
    report = validate_sidra_contract(df, "pmc_varejo_uf")

    assert report.passed is True
    assert report.row_count == 4
    assert report.secrecy_x_rate == 0.25
    assert report.unavailable_rate == 0.25
    assert report.exact_zero_rate == 0.25


def test_sidra_contract_rejects_duplicates_and_corrupted_values(
    sample_sidra_pib_payload: list[dict[str, Any]],
) -> None:
    df = flatten_sidra_response(5938, sample_sidra_pib_payload)
    corrupted = pl.concat([df, df.head(1)]).with_columns(
        pl.when(pl.col("localidade_id") == "3550308")
        .then(pl.lit("CORRUPTED_TEXT"))
        .otherwise(pl.col("valor_bruto"))
        .alias("valor_bruto")
    )
    report = validate_sidra_contract(corrupted, "pib_municipal")
    assert report.passed is False
    assert report.duplicate_key_rows == 1
    assert report.invalid_value_rows == 2


def test_contracts_handle_missing_required_columns_gracefully() -> None:
    incomplete_df = pl.DataFrame({"outra_coluna": [1, 2]})

    loc_report = validate_localidades_contract(incomplete_df)
    assert loc_report.passed is False
    assert loc_report.distinct_localidades == 0
    assert loc_report.duplicate_key_rows == 0

    cnae_report = validate_cnae_contract(incomplete_df)
    assert cnae_report.passed is False
    assert cnae_report.duplicate_key_rows == 0

    sidra_report = validate_sidra_contract(incomplete_df, "pib_municipal")
    assert sidra_report.passed is False
    assert sidra_report.error_message is not None
    assert "Colunas obrigatorias ausentes" in sidra_report.error_message
