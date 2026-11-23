"""Testes unitarios para o escritor ACID Delta Lake (idempotencia, MERGE e time travel)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
from deltalake import DeltaTable

from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter, compute_dataframe_hash


def test_partition_overwrite_is_idempotent_and_preserves_time_travel(tmp_path: Path) -> None:
    writer = DeltaLakeWriter(tmp_path / "bronze")
    df_2022 = pl.DataFrame({"ano_referencia": ["2022", "2022"], "id": [1, 2], "val": ["10", "20"]})
    df_2023_v1 = pl.DataFrame(
        {"ano_referencia": ["2023", "2023"], "id": [1, 2], "val": ["11", "21"]}
    )
    df_2023_v2 = pl.DataFrame(
        {"ano_referencia": ["2023", "2023"], "id": [1, 2], "val": ["15", "25"]}
    )

    r0 = writer.write_partition_overwrite(
        df_2022,
        "pib_test",
        partition_col="ano_referencia",
        partition_value="2022",
        ingestion_id="run-1",
        source_url="https://ibge/2022",
    )
    r1 = writer.write_partition_overwrite(
        df_2023_v1,
        "pib_test",
        partition_col="ano_referencia",
        partition_value="2023",
        ingestion_id="run-2",
        source_url="https://ibge/2023",
    )
    # Reprocessa a mesma particao 2023 -> nao pode duplicar linhas e deve preservar 2022!
    r2 = writer.write_partition_overwrite(
        df_2023_v2,
        "pib_test",
        partition_col="ano_referencia",
        partition_value="2023",
        ingestion_id="run-3",
        source_url="https://ibge/2023",
    )

    assert (r0.delta_version, r1.delta_version, r2.delta_version) == (0, 1, 2)

    dt_latest = DeltaTable(str(writer.table_path("pib_test")))
    latest_df = pl.from_arrow(dt_latest.to_pyarrow_table(engine="datafusion"))
    assert isinstance(latest_df, pl.DataFrame)
    assert latest_df.height == 4
    vals_2023 = sorted(latest_df.filter(pl.col("ano_referencia") == "2023")["val"].to_list())
    assert vals_2023 == ["15", "25"]

    # Time travel para versao 1 recupera exatamente o estado anterior de 2023
    dt_v1 = DeltaTable(str(writer.table_path("pib_test")), version=1)
    v1_df = pl.from_arrow(dt_v1.to_pyarrow_table(engine="datafusion"))
    assert isinstance(v1_df, pl.DataFrame)
    assert sorted(v1_df.filter(pl.col("ano_referencia") == "2023")["val"].to_list()) == ["11", "21"]


def test_upsert_merge_updates_and_inserts_without_duplicates(tmp_path: Path) -> None:
    writer = DeltaLakeWriter(tmp_path / "bronze")
    df1 = pl.DataFrame({"codigo": [1, 2], "nome": ["Alpha", "Beta"]})
    df2 = pl.DataFrame({"codigo": [2, 3], "nome": ["Beta Rev", "Gamma"]})

    writer.upsert_merge(df1, "dim_test", merge_keys=["codigo"], ingestion_id="r1", source_url="u1")
    writer.upsert_merge(df2, "dim_test", merge_keys=["codigo"], ingestion_id="r2", source_url="u2")

    dt = DeltaTable(str(writer.table_path("dim_test")))
    result = pl.from_arrow(dt.to_pyarrow_table(engine="datafusion"))
    assert isinstance(result, pl.DataFrame)
    assert result.height == 3
    by_id = dict(zip(result["codigo"].to_list(), result["nome"].to_list(), strict=True))
    assert by_id == {1: "Alpha", 2: "Beta Rev", 3: "Gamma"}


def test_dataframe_hash_is_order_independent() -> None:
    df_a = pl.DataFrame({"id": [2, 1], "val": ["b", "a"], "_ingestion_id": ["x", "x"]})
    df_b = pl.DataFrame({"val": ["a", "b"], "id": [1, 2], "_ingestion_id": ["y", "y"]})
    assert compute_dataframe_hash(df_a) == compute_dataframe_hash(df_b)
