"""Cliente HTTP assincrono resiliente para as APIs oficiais do IBGE."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import polars as pl
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ibge_market_intel.config import PipelineSettings
from ibge_market_intel.ingestion.catalogs import UF_CODES, AgregadoSpec
from ibge_market_intel.ingestion.schemas import (
    empty_sidra_dataframe,
    flatten_sidra_response,
    parse_cnae_payload,
    parse_localidades_payload,
)
from ibge_market_intel.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS_CODES
    return False


@dataclass(frozen=True)
class FetchResult:
    """Resultado de extracao com metadados de auditoria e observabilidade."""

    df: pl.DataFrame
    source_urls: tuple[str, ...]
    elapsed_seconds: float
    requests_made: int


class IBGEAsyncClient:
    """Cliente assincrono com semaforo de concorrencia, retry exponencial e chunking por UF."""

    def __init__(
        self,
        settings: PipelineSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._base_url = settings.ibge_base_url.rstrip("/")
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._periods_cache: dict[int, list[str]] = {}
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_s),
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "application/json",
            },
            limits=httpx.Limits(
                max_connections=settings.max_concurrency * 2,
                max_keepalive_connections=settings.max_concurrency,
            ),
            transport=transport,
        )

    async def __aenter__(self) -> IBGEAsyncClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_json(self, url: str) -> Any:
        async with self._semaphore:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_retryable_error),
                wait=wait_exponential_jitter(initial=1.0, max=25.0),
                stop=stop_after_attempt(self._settings.retry_max_attempts),
                reraise=True,
            ):
                with attempt:
                    t0 = time.perf_counter()
                    response = await self._client.get(url)
                    response.raise_for_status()
                    payload = response.json()
                    logger.debug(
                        "ibge_http_get_ok",
                        url=url,
                        status_code=response.status_code,
                        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
                    )
                    return payload
        raise RuntimeError(f"Falha inesperada ao consultar {url}")  # pragma: no cover

    async def fetch_localidades(self, uf_codes: Sequence[int] | None = None) -> FetchResult:
        """Extrai todos os municipios da API de Localidades v1 (opcionalmente filtrados por UF)."""
        t0 = time.perf_counter()
        url = f"{self._base_url}/v1/localidades/municipios"
        raw = await self._get_json(url)
        df = parse_localidades_payload(raw)
        if uf_codes:
            df = df.filter(pl.col("uf_id").is_in(list(uf_codes)))
        return FetchResult(
            df=df,
            source_urls=(url,),
            elapsed_seconds=round(time.perf_counter() - t0, 3),
            requests_made=1,
        )

    async def fetch_cnae_secoes(self) -> FetchResult:
        """Extrai as 21 secoes oficiais da API CNAE v2."""
        t0 = time.perf_counter()
        url = f"{self._base_url}/v2/cnae/secoes"
        raw = await self._get_json(url)
        df = parse_cnae_payload(raw)
        return FetchResult(
            df=df,
            source_urls=(url,),
            elapsed_seconds=round(time.perf_counter() - t0, 3),
            requests_made=1,
        )

    async def fetch_available_periods(
        self,
        agregado_id: int,
        *,
        use_cache: bool = True,
    ) -> list[str]:
        """Consulta /api/v3/agregados/{id}/periodos para descoberta dinamica e freshness sensor."""
        if use_cache and agregado_id in self._periods_cache:
            return self._periods_cache[agregado_id]

        url = f"{self._base_url}/v3/agregados/{agregado_id}/periodos"
        raw: list[dict[str, Any]] = await self._get_json(url)
        periods = [str(item["id"]).strip() for item in raw if "id" in item]
        self._periods_cache[agregado_id] = periods
        return periods

    async def discover_available_years(
        self,
        spec: AgregadoSpec,
        *,
        use_cache: bool = True,
    ) -> list[str]:
        """Descobre dinamicamente todos os anos >= spec.min_year publicados na API do IBGE."""
        periods = await self.fetch_available_periods(spec.agregado_id, use_cache=use_cache)
        years = {
            p[:4]
            for p in periods
            if len(p) >= 4 and p[:4].isdigit() and int(p[:4]) >= spec.min_year
        }
        return sorted(years)

    def _build_sidra_url(
        self,
        spec: AgregadoSpec,
        periodos: Sequence[str],
        localidades_expr: str,
    ) -> str:
        periodos_str = "|".join(periodos)
        vars_str = "|".join(str(v) for v in spec.variaveis)
        base = (
            f"{self._base_url}/v3/agregados/{spec.agregado_id}"
            f"/periodos/{periodos_str}/variaveis/{vars_str}"
            f"?localidades={localidades_expr}"
        )
        cls_param = spec.classificacao_param()
        if cls_param:
            return f"{base}&classificacao={cls_param}"
        return base

    async def _resolve_periods_for_year(self, spec: AgregadoSpec, ano: str) -> list[str]:
        available = await self.fetch_available_periods(spec.agregado_id)
        if spec.periodicidade == "anual":
            return [ano] if ano in available else []
        return sorted(p for p in available if p.startswith(ano))

    async def fetch_agregado_for_year(
        self,
        spec: AgregadoSpec,
        ano: str,
        uf_codes: Sequence[int] | None = None,
    ) -> FetchResult:
        """Extrai particao anual de um agregado SIDRA com chunking por UF/semestre."""
        t0 = time.perf_counter()
        target_periods = await self._resolve_periods_for_year(spec, ano)
        if not target_periods:
            logger.warning(
                "ibge_period_not_available",
                agregado_id=spec.agregado_id,
                table_name=spec.table_name,
                ano=ano,
            )
            return FetchResult(
                df=empty_sidra_dataframe(),
                source_urls=(),
                elapsed_seconds=round(time.perf_counter() - t0, 3),
                requests_made=0,
            )

        # Quebra meses em blocos de 6 (semestres) quando o agregado tem multiplas classificacoes
        period_chunks: list[list[str]] = (
            [target_periods[i : i + 6] for i in range(0, len(target_periods), 6)]
            if spec.chunk_months_half_year and len(target_periods) > 6
            else [target_periods]
        )

        # Quebra localidades por UF (N6[N3[uf]]) para evitar timeouts em N6[all] com muitas vars
        effective_ufs = list(uf_codes) if uf_codes else list(UF_CODES)
        loc_expressions: list[str]
        if spec.nivel_territorial == "N6" and (spec.chunk_by_uf or uf_codes):
            loc_expressions = [f"N6[N3[{uf}]]" for uf in effective_ufs]
        elif spec.nivel_territorial == "N3" and uf_codes:
            loc_expressions = [f"N3[{','.join(str(uf) for uf in effective_ufs)}]"]
        else:
            loc_expressions = [f"{spec.nivel_territorial}[all]"]

        urls = [
            self._build_sidra_url(spec, p_chunk, loc_expr)
            for p_chunk in period_chunks
            for loc_expr in loc_expressions
        ]

        logger.info(
            "ibge_fetch_agregado_start",
            table_name=spec.table_name,
            agregado_id=spec.agregado_id,
            ano=ano,
            requests_planned=len(urls),
            periods=target_periods,
        )

        async def _fetch_chunk(url: str) -> pl.DataFrame:
            raw_json = await self._get_json(url)
            if not isinstance(raw_json, list):
                raise ValueError(
                    f"Resposta inesperada (nao-lista) da API IBGE em {url}: "
                    f"{type(raw_json).__name__}"
                )
            return flatten_sidra_response(spec.agregado_id, raw_json)

        frames = await asyncio.gather(*(_fetch_chunk(u) for u in urls))
        non_empty = [f for f in frames if f.height > 0]
        combined = pl.concat(non_empty, how="vertical") if non_empty else empty_sidra_dataframe()

        elapsed = round(time.perf_counter() - t0, 3)
        logger.info(
            "ibge_fetch_agregado_done",
            table_name=spec.table_name,
            agregado_id=spec.agregado_id,
            ano=ano,
            rows=combined.height,
            requests_made=len(urls),
            elapsed_seconds=elapsed,
        )
        return FetchResult(
            df=combined,
            source_urls=tuple(urls),
            elapsed_seconds=elapsed,
            requests_made=len(urls),
        )
