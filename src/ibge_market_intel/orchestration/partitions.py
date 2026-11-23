"""Definicoes de particoes declarativas do Dagster para backfill e idempotencia."""

from __future__ import annotations

from dagster import StaticPartitionsDefinition

from ibge_market_intel.ingestion.catalogs import (
    CEMPRE_YEARS,
    CENSO_YEARS,
    ESTIMATIVA_POP_YEARS,
    IPCA_YEARS,
    PIB_YEARS,
    PMC_YEARS,
)

PIB_PARTITIONS = StaticPartitionsDefinition(list(PIB_YEARS))
CENSO_PARTITIONS = StaticPartitionsDefinition(list(CENSO_YEARS))
ESTIMATIVA_POP_PARTITIONS = StaticPartitionsDefinition(list(ESTIMATIVA_POP_YEARS))
CEMPRE_PARTITIONS = StaticPartitionsDefinition(list(CEMPRE_YEARS))
IPCA_PARTITIONS = StaticPartitionsDefinition(list(IPCA_YEARS))
PMC_PARTITIONS = StaticPartitionsDefinition(list(PMC_YEARS))
