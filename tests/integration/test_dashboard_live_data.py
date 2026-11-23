"""Teste de integracao das 52+ queries do dashboard Evidence contra os Parquets reais do IBGE."""

from __future__ import annotations

import os

import polars as pl
import pytest

from ibge_market_intel.analytics.bi_export import BI_GOLD_TABLES
from ibge_market_intel.config import get_settings
from ibge_market_intel.quality.dashboard_guard import validate_dashboard_queries


def test_dashboard_queries_against_exported_ibge_parquets() -> None:
    """Valida todas as queries BI contra os dados reais em dashboard/parquet_data/."""
    root = get_settings().project_root
    parquet_dir = root / "dashboard" / "parquet_data"

    if not parquet_dir.exists() or not any(parquet_dir.glob("*.parquet")):
        if os.environ.get("SIDRALAKE_REQUIRE_BI_DATA") == "1":
            pytest.fail(f"Parquets BI ausentes em {parquet_dir} com SIDRALAKE_REQUIRE_BI_DATA=1.")
        pytest.skip("dashboard/parquet_data nao materializado neste ambiente (apenas PR CI).")

    for tbl in BI_GOLD_TABLES:
        pq = parquet_dir / f"{tbl}.parquet"
        assert pq.exists(), f"Tabela BI ausente: {pq}"
        assert pl.scan_parquet(pq).select(pl.len()).collect().item() > 0

    mode = os.environ.get("SIDRALAKE_MODE", "full")
    if mode == "full":
        assert (
            pl.scan_parquet(parquet_dir / "dim_geografia.parquet").select(pl.len()).collect().item()
            >= 5570
        )
        assert (
            pl.scan_parquet(parquet_dir / "dim_cnae.parquet").select(pl.len()).collect().item()
            == 21
        )
        assert (
            pl.scan_parquet(parquet_dir / "fct_ipca_mensal.parquet")
            .select(pl.len())
            .collect()
            .item()
            >= 80
        )

    executed, issues = validate_dashboard_queries(
        root,
        parquet_dir,
        emulate_evidence_double=True,
        require_non_empty=(mode == "full"),
    )
    assert executed >= 50
    assert issues == [], "Falhas nos dados reais do dashboard:\n" + "\n".join(
        f"  - [{i.rule}] {i.file}: {i.message}" for i in issues
    )
