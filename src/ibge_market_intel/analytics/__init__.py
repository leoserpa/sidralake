"""Camada analitica local em Polars Lazy API sobre as tabelas Delta Lake Gold."""

from ibge_market_intel.analytics.bi_export import BI_GOLD_TABLES, export_gold_for_bi
from ibge_market_intel.analytics.insights import (
    MarketInsightsReport,
    build_market_insights,
    format_insights_report,
)

__all__ = [
    "BI_GOLD_TABLES",
    "MarketInsightsReport",
    "build_market_insights",
    "export_gold_for_bi",
    "format_insights_report",
]
