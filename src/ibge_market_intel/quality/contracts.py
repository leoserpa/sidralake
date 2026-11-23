"""Contratos de dados Pandera (Polars) atuando como Circuit Breakers na camada Bronze."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaError, SchemaErrors

from ibge_market_intel.ingestion.catalogs import VALID_UF_SIGLAS

# Padrao oficial de valores aceitos na camada Bronze do SIDRA:
# numero (com sinal/decimal opcional) OU codigos especiais do IBGE (-, .., ..., X, vazio)
_IBGE_VALUE_REGEX = r"^(?:-|\.\.|\.\.\.|X||-?\d+(?:[.,]\d+)?)$"
_IBGE_SPECIAL_CODES = frozenset({"-", "..", "...", "X", ""})
_VALID_VALUE_PATTERN = re.compile(_IBGE_VALUE_REGEX)


class BronzeLocalidadesSchema(pa.DataFrameModel):
    """Contrato de schema da tabela Bronze de municipios do IBGE."""

    municipio_id: int = pa.Field(ge=1100000, le=5399999, unique=True)
    municipio_nome: str = pa.Field(str_length={"min_value": 2})
    uf_id: int = pa.Field(ge=11, le=53)
    uf_sigla: str = pa.Field(isin=sorted(VALID_UF_SIGLAS))
    uf_nome: str = pa.Field(str_length={"min_value": 3})
    regiao_id: int = pa.Field(ge=1, le=5)
    regiao_sigla: str = pa.Field(isin=["N", "NE", "SE", "S", "CO"])
    regiao_nome: str = pa.Field(str_length={"min_value": 3})
    regiao_imediata_id: int = pa.Field(gt=0)
    regiao_imediata_nome: str = pa.Field(str_length={"min_value": 2})
    regiao_intermediaria_id: int = pa.Field(gt=0)
    regiao_intermediaria_nome: str = pa.Field(str_length={"min_value": 2})
    microrregiao_id: int | None = pa.Field(nullable=True)
    microrregiao_nome: str | None = pa.Field(nullable=True)
    mesorregiao_id: int | None = pa.Field(nullable=True)
    mesorregiao_nome: str | None = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = True


class BronzeCnaeSchema(pa.DataFrameModel):
    """Contrato de schema da tabela Bronze de secoes CNAE 2.0."""

    secao_codigo: str = pa.Field(str_matches=r"^[A-U]$", unique=True)
    secao_descricao: str = pa.Field(str_length={"min_value": 5})
    categoria_sidra_12762_id: int = pa.Field(gt=0, unique=True)
    observacoes: str = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = True


class BronzeSidraSchema(pa.DataFrameModel):
    """Contrato canonico de todas as tabelas SIDRA na camada Bronze."""

    agregado_id: int = pa.Field(gt=0)
    variavel_id: int = pa.Field(gt=0)
    variavel_nome: str = pa.Field(str_length={"min_value": 2})
    unidade: str = pa.Field(nullable=True)
    localidade_id: str = pa.Field(str_matches=r"^\d{1,7}$")
    localidade_nome: str = pa.Field(str_length={"min_value": 2})
    nivel_territorial: str = pa.Field(isin=["N1", "N2", "N3", "N6", "N7", "N8", "N9"])
    classificacao_1_id: str = pa.Field(nullable=False)
    categoria_1_id: str = pa.Field(nullable=False)
    categoria_1_nome: str = pa.Field(nullable=False)
    classificacao_2_id: str = pa.Field(nullable=False)
    categoria_2_id: str = pa.Field(nullable=False)
    categoria_2_nome: str = pa.Field(nullable=False)
    periodo_id: str = pa.Field(str_matches=r"^\d{4}(\d{2})?$")
    ano_referencia: str = pa.Field(str_matches=r"^\d{4}$")
    valor_bruto: str = pa.Field(nullable=False)

    class Config:
        strict = False
        coerce = True


@dataclass(frozen=True)
class QualityReport:
    """Resultado consolidado de validacao de contrato + estatisticas de observabilidade."""

    dataset_name: str
    passed: bool
    row_count: int
    distinct_localidades: int
    duplicate_key_rows: int
    invalid_value_rows: int
    secrecy_x_rate: float
    unavailable_rate: float
    exact_zero_rate: float
    error_message: str | None = None


def _missing_schema_columns(
    df: pl.DataFrame,
    schema_cls: type[pa.DataFrameModel],
) -> list[str]:
    schema = schema_cls.to_schema()
    return [
        col
        for col, col_schema in schema.columns.items()
        if col_schema.required and col not in df.columns
    ]


def validate_localidades_contract(df: pl.DataFrame) -> QualityReport:
    """Valida contrato Pandera da tabela bronze_localidades."""
    if df.height == 0:
        return QualityReport(
            dataset_name="localidades",
            passed=False,
            row_count=0,
            distinct_localidades=0,
            duplicate_key_rows=0,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message="Tabela bronze_localidades vazia.",
        )
    missing_cols = _missing_schema_columns(df, BronzeLocalidadesSchema)
    if missing_cols:
        has_mun = "municipio_id" in df.columns
        distinct_muns = df["municipio_id"].n_unique() if has_mun else 0
        dup_rows = (df.height - distinct_muns) if has_mun else 0
        return QualityReport(
            dataset_name="localidades",
            passed=False,
            row_count=df.height,
            distinct_localidades=distinct_muns,
            duplicate_key_rows=dup_rows,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=(
                f"Colunas obrigatorias ausentes em localidades: {', '.join(missing_cols)}"
            ),
        )
    try:
        BronzeLocalidadesSchema.validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as exc:
        has_mun = "municipio_id" in df.columns
        distinct_muns = df["municipio_id"].n_unique() if has_mun else 0
        dup_rows = (df.height - distinct_muns) if has_mun else 0
        return QualityReport(
            dataset_name="localidades",
            passed=False,
            row_count=df.height,
            distinct_localidades=distinct_muns,
            duplicate_key_rows=dup_rows,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=str(exc),
        )

    return QualityReport(
        dataset_name="localidades",
        passed=True,
        row_count=df.height,
        distinct_localidades=df["municipio_id"].n_unique(),
        duplicate_key_rows=0,
        invalid_value_rows=0,
        secrecy_x_rate=0.0,
        unavailable_rate=0.0,
        exact_zero_rate=0.0,
    )


def validate_cnae_contract(df: pl.DataFrame) -> QualityReport:
    """Valida contrato Pandera da tabela bronze_cnae_secoes."""
    if df.height == 0:
        return QualityReport(
            dataset_name="cnae_secoes",
            passed=False,
            row_count=0,
            distinct_localidades=0,
            duplicate_key_rows=0,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message="Tabela bronze_cnae_secoes vazia.",
        )
    missing_cols = _missing_schema_columns(df, BronzeCnaeSchema)
    if missing_cols:
        has_secao = "secao_codigo" in df.columns
        dup_rows = (df.height - df["secao_codigo"].n_unique()) if has_secao else 0
        return QualityReport(
            dataset_name="cnae_secoes",
            passed=False,
            row_count=df.height,
            distinct_localidades=0,
            duplicate_key_rows=dup_rows,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=(
                f"Colunas obrigatorias ausentes em cnae_secoes: {', '.join(missing_cols)}"
            ),
        )
    try:
        BronzeCnaeSchema.validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as exc:
        has_secao = "secao_codigo" in df.columns
        dup_rows = (df.height - df["secao_codigo"].n_unique()) if has_secao else 0
        return QualityReport(
            dataset_name="cnae_secoes",
            passed=False,
            row_count=df.height,
            distinct_localidades=0,
            duplicate_key_rows=dup_rows,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=str(exc),
        )

    return QualityReport(
        dataset_name="cnae_secoes",
        passed=True,
        row_count=df.height,
        distinct_localidades=df.height,
        duplicate_key_rows=0,
        invalid_value_rows=0,
        secrecy_x_rate=0.0,
        unavailable_rate=0.0,
        exact_zero_rate=0.0,
    )


def validate_sidra_contract(
    df: pl.DataFrame,
    dataset_name: str,
    *,
    allow_empty: bool = False,
) -> QualityReport:
    """Valida contrato Pandera, unicidade da chave natural e dominio de valores SIDRA."""
    total = df.height
    if total == 0:
        return QualityReport(
            dataset_name=dataset_name,
            passed=allow_empty,
            row_count=0,
            distinct_localidades=0,
            duplicate_key_rows=0,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=None if allow_empty else f"Dataset {dataset_name} retornou 0 linhas.",
        )

    key_cols = [
        "agregado_id",
        "variavel_id",
        "localidade_id",
        "classificacao_1_id",
        "categoria_1_id",
        "classificacao_2_id",
        "categoria_2_id",
        "periodo_id",
    ]
    missing_cols = _missing_schema_columns(df, BronzeSidraSchema)
    if missing_cols:
        return QualityReport(
            dataset_name=dataset_name,
            passed=False,
            row_count=total,
            distinct_localidades=(
                df["localidade_id"].n_unique() if "localidade_id" in df.columns else 0
            ),
            duplicate_key_rows=0,
            invalid_value_rows=0,
            secrecy_x_rate=0.0,
            unavailable_rate=0.0,
            exact_zero_rate=0.0,
            error_message=(
                f"Colunas obrigatorias ausentes em {dataset_name}: {', '.join(missing_cols)}"
            ),
        )

    distinct_locs = df["localidade_id"].n_unique()
    dup_rows = total - df.unique(subset=key_cols).height

    # Verifica aderencia ao dominio oficial IBGE (numero ou codigo especial -, .., ..., X, vazio)
    valor_str = df["valor_bruto"].cast(pl.String())
    invalid_mask = ~valor_str.str.contains(_IBGE_VALUE_REGEX)
    invalid_rows = int(invalid_mask.sum())

    secrecy_x_rate = round(float((valor_str == "X").sum()) / total, 6)
    unavailable_rate = round(float(valor_str.is_in(["..", "...", ""]).sum()) / total, 6)
    exact_zero_rate = round(float((valor_str == "-").sum()) / total, 6)

    errors: list[str] = []
    try:
        BronzeSidraSchema.validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as exc:
        errors.append(f"Pandera schema violation: {exc}")

    if dup_rows > 0:
        errors.append(f"Encontradas {dup_rows} linhas duplicadas na chave natural SIDRA.")
    if invalid_rows > 0:
        bad_samples = df.filter(invalid_mask)["valor_bruto"].unique().head(5).to_list()
        errors.append(
            f"Encontrados {invalid_rows} valores fora do padrao IBGE. Amostras: {bad_samples}"
        )

    return QualityReport(
        dataset_name=dataset_name,
        passed=len(errors) == 0,
        row_count=total,
        distinct_localidades=distinct_locs,
        duplicate_key_rows=dup_rows,
        invalid_value_rows=invalid_rows,
        secrecy_x_rate=secrecy_x_rate,
        unavailable_rate=unavailable_rate,
        exact_zero_rate=exact_zero_rate,
        error_message=" | ".join(errors) if errors else None,
    )
