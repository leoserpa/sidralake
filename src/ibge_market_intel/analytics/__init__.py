"""Camada analitica local em Polars Lazy API sobre as tabelas Delta Lake Gold."""

from ibge_market_intel.analytics.insights import (
    MarketInsightsReport,
    build_market_insights,
    format_insights_report,
)

__all__ = [
    "MarketInsightsReport",
    "build_market_insights",
    "format_insights_report",
]
