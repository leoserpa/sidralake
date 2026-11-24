"""Definicoes de particoes dinamicas do Dagster para backfill e atualizacao automatica."""

from __future__ import annotations

from dagster import DynamicPartitionsDefinition

PIB_PARTITIONS = DynamicPartitionsDefinition(name="pib_years")
CENSO_PARTITIONS = DynamicPartitionsDefinition(name="censo_years")
ESTIMATIVA_POP_PARTITIONS = DynamicPartitionsDefinition(name="estimativa_pop_years")
CEMPRE_PARTITIONS = DynamicPartitionsDefinition(name="cempre_years")
IPCA_PARTITIONS = DynamicPartitionsDefinition(name="ipca_years")
PMC_PARTITIONS = DynamicPartitionsDefinition(name="pmc_years")
PMS_PARTITIONS = DynamicPartitionsDefinition(name="pms_years")
PNAD_PARTITIONS = DynamicPartitionsDefinition(name="pnad_years")
