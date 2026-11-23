"""Testes unitarios do cliente assincrono IBGE (chunking UF, retry 429/500 e periodos)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from ibge_market_intel.config import PipelineSettings
from ibge_market_intel.ingestion.catalogs import PIB_MUNICIPAL_SPEC, PMC_VAREJO_UF_SPEC
from ibge_market_intel.ingestion.client import IBGEAsyncClient


@pytest.mark.asyncio
async def test_client_chunks_by_uf_for_municipal_tables(
    tmp_settings: PipelineSettings,
    sample_sidra_pib_payload: list[dict[str, Any]],
) -> None:
    base = tmp_settings.ibge_base_url
    with respx.mock(assert_all_called=True) as mock_router:
        mock_router.get(f"{base}/v3/agregados/5938/periodos").mock(
            return_value=httpx.Response(200, json=[{"id": "2023"}])
        )
        sp_route = mock_router.get(
            url__regex=r".*/agregados/5938/periodos/2023/variaveis/.*localidades=N6\[N3\[35\]\].*"
        ).mock(return_value=httpx.Response(200, json=sample_sidra_pib_payload))
        mt_route = mock_router.get(
            url__regex=r".*/agregados/5938/periodos/2023/variaveis/.*localidades=N6\[N3\[51\]\].*"
        ).mock(return_value=httpx.Response(200, json=[]))

        async with IBGEAsyncClient(tmp_settings) as client:
            res = await client.fetch_agregado_for_year(
                PIB_MUNICIPAL_SPEC, ano="2023", uf_codes=[35, 51]
            )

        assert sp_route.called
        assert mt_route.called
        assert res.requests_made == 2
        assert res.df.height == 2


@pytest.mark.asyncio
async def test_client_retries_on_http_429_and_succeeds(
    tmp_settings: PipelineSettings,
    sample_localidades_payload: list[dict[str, Any]],
) -> None:
    base = tmp_settings.ibge_base_url
    with respx.mock(assert_all_called=True) as mock_router:
        route = mock_router.get(f"{base}/v1/localidades/municipios").mock(
            side_effect=[
                httpx.Response(429, text="Too Many Requests"),
                httpx.Response(503, text="Service Unavailable"),
                httpx.Response(200, json=sample_localidades_payload),
            ]
        )
        async with IBGEAsyncClient(tmp_settings) as client:
            res = await client.fetch_localidades()

        assert route.call_count == 3
        assert res.df.height == 3


@pytest.mark.asyncio
async def test_client_chunks_monthly_pmc_in_half_years(
    tmp_settings: PipelineSettings,
    sample_sidra_pmc_payload: list[dict[str, Any]],
) -> None:
    base = tmp_settings.ibge_base_url
    months = [{"id": f"2024{m:02d}"} for m in range(1, 13)]
    with respx.mock(assert_all_called=True) as mock_router:
        mock_router.get(f"{base}/v3/agregados/8883/periodos").mock(
            return_value=httpx.Response(200, json=months)
        )
        h1 = mock_router.get(url__regex=r".*/periodos/202401.*202406/.*").mock(
            return_value=httpx.Response(200, json=sample_sidra_pmc_payload)
        )
        h2 = mock_router.get(url__regex=r".*/periodos/202407.*202412/.*").mock(
            return_value=httpx.Response(200, json=[])
        )
        async with IBGEAsyncClient(tmp_settings) as client:
            res = await client.fetch_agregado_for_year(
                PMC_VAREJO_UF_SPEC, ano="2024", uf_codes=[35, 51]
            )

        assert h1.called
        assert h2.called
        assert res.requests_made == 2
        assert res.df.height == 4


@pytest.mark.asyncio
async def test_client_raises_on_non_list_chunk_payload(
    tmp_settings: PipelineSettings,
) -> None:
    base = tmp_settings.ibge_base_url
    with respx.mock(assert_all_called=True) as mock_router:
        mock_router.get(f"{base}/v3/agregados/5938/periodos").mock(
            return_value=httpx.Response(200, json=[{"id": "2023"}])
        )
        mock_router.get(
            url__regex=r".*/agregados/5938/periodos/2023/variaveis/.*localidades=N6\[N3\[35\]\].*"
        ).mock(return_value=httpx.Response(200, json={"erro": "limite excedido"}))

        async with IBGEAsyncClient(tmp_settings) as client:
            with pytest.raises(ValueError, match="nao-lista"):
                await client.fetch_agregado_for_year(PIB_MUNICIPAL_SPEC, ano="2023", uf_codes=[35])
