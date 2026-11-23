"""Testes unitarios para parsing Pydantic e normalizacao dos payloads IBGE."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ibge_market_intel.ingestion.schemas import (
    flatten_sidra_response,
    parse_cnae_payload,
    parse_localidades_payload,
)


def test_parse_localidades_handles_boa_esperanca_null_microrregiao(
    sample_localidades_payload: list[dict[str, Any]],
) -> None:
    df = parse_localidades_payload(sample_localidades_payload)
    assert df.height == 3

    boa = df.filter(df["municipio_id"] == 5101837).to_dicts()[0]
    assert boa["municipio_nome"] == "Boa Esperança do Norte"
    assert boa["uf_sigla"] == "MT"
    assert boa["uf_id"] == 51
    assert boa["regiao_sigla"] == "CO"
    assert boa["regiao_imediata_id"] == 510012
    assert boa["microrregiao_id"] is None
    assert boa["mesorregiao_id"] is None


def test_parse_cnae_maps_sidra_12762_ids(sample_cnae_payload: list[dict[str, Any]]) -> None:
    df = parse_cnae_payload(sample_cnae_payload)
    assert df.height == 3
    by_code = {r["secao_codigo"]: r["categoria_sidra_12762_id"] for r in df.to_dicts()}
    assert by_code == {"A": 116830, "C": 116910, "G": 117363}


def test_flatten_sidra_preserves_special_codes(
    sample_sidra_pib_payload: list[dict[str, Any]],
) -> None:
    df = flatten_sidra_response(5938, sample_sidra_pib_payload)
    assert df.height == 2
    values = dict(zip(df["localidade_id"].to_list(), df["valor_bruto"].to_list(), strict=True))
    assert values == {"3550308": "828980607", "5101837": "..."}
    assert df["classificacao_1_id"].to_list() == ["NONE", "NONE"]
    assert df["ano_referencia"].to_list() == ["2023", "2023"]


def test_flatten_sidra_sorts_multiple_classifications_deterministically(
    sample_sidra_pmc_payload: list[dict[str, Any]],
) -> None:
    df = flatten_sidra_response(8883, sample_sidra_pmc_payload)
    assert df.height == 4
    # 85 < 11046 => classificacao_1_id deve ser sempre "85" e classificacao_2_id "11046"
    assert set(df["classificacao_1_id"].to_list()) == {"85"}
    assert set(df["categoria_1_id"].to_list()) == {"90672"}
    assert set(df["classificacao_2_id"].to_list()) == {"11046"}
    assert set(df["categoria_2_id"].to_list()) == {"56736"}
    assert set(df["valor_bruto"].to_list()) == {"104.5", "-", "X", ".."}


def test_parse_localidades_rejects_malformed_payload() -> None:
    with pytest.raises(ValidationError):
        parse_localidades_payload([{"id": "not-an-int", "nome": "Broken"}])
