"""Contratos Pydantic v2 para payloads HTTP das APIs do IBGE e normalizacao tabular."""

from __future__ import annotations

from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from ibge_market_intel.ingestion.catalogs import CNAE_SIDRA_SECOES_12762


class IBGERegiaoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    sigla: str
    nome: str


class IBGEUfPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    sigla: str
    nome: str
    regiao: IBGERegiaoPayload


class IBGEMesorregiaoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    nome: str
    UF: IBGEUfPayload


class IBGEMicrorregiaoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    nome: str
    mesorregiao: IBGEMesorregiaoPayload


class IBGERegiaoIntermediariaPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    nome: str
    UF: IBGEUfPayload


class IBGERegiaoImediataPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    nome: str
    regiao_intermediaria: IBGERegiaoIntermediariaPayload = Field(alias="regiao-intermediaria")


class LocalidadeMunicipioPayload(BaseModel):
    """Contrato do payload de municipio (/api/v1/localidades/municipios).

    Trata explicitamente o caso real observado em Boa Esperanca do Norte (5101837),
    onde `microrregiao` e `None`, derivando UF/Regiao via `regiao-imediata`.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int
    nome: str
    microrregiao: IBGEMicrorregiaoPayload | None = None
    regiao_imediata: IBGERegiaoImediataPayload = Field(alias="regiao-imediata")


class CnaeSecaoPayload(BaseModel):
    """Contrato do payload de secao CNAE (/api/v2/cnae/secoes)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    descricao: str
    observacoes: list[str] = Field(default_factory=list)


class SidraClassificacaoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str
    categoria: dict[str, str]


class SidraNivelPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str


class SidraLocalidadePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nivel: SidraNivelPayload
    nome: str


class SidraSeriePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    localidade: SidraLocalidadePayload
    serie: dict[str, str | None]


class SidraResultadoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    classificacoes: list[SidraClassificacaoPayload] = Field(default_factory=list)
    series: list[SidraSeriePayload] = Field(default_factory=list)


class SidraVariavelPayload(BaseModel):
    """Contrato do payload de resposta da API de Agregados/SIDRA v3."""

    model_config = ConfigDict(extra="ignore")

    id: str
    variavel: str
    unidade: str | None = ""
    resultados: list[SidraResultadoPayload] = Field(default_factory=list)


SIDRA_BRONZE_SCHEMA: dict[str, pl.DataType] = {
    "agregado_id": pl.Int32(),
    "variavel_id": pl.Int32(),
    "variavel_nome": pl.String(),
    "unidade": pl.String(),
    "localidade_id": pl.String(),
    "localidade_nome": pl.String(),
    "nivel_territorial": pl.String(),
    "classificacao_1_id": pl.String(),
    "categoria_1_id": pl.String(),
    "categoria_1_nome": pl.String(),
    "classificacao_2_id": pl.String(),
    "categoria_2_id": pl.String(),
    "categoria_2_nome": pl.String(),
    "periodo_id": pl.String(),
    "ano_referencia": pl.String(),
    "valor_bruto": pl.String(),
}


def empty_sidra_dataframe() -> pl.DataFrame:
    """Retorna um DataFrame Polars vazio com o schema canonico Bronze do SIDRA."""
    return pl.DataFrame(schema=SIDRA_BRONZE_SCHEMA)


def parse_localidades_payload(raw_items: list[dict[str, Any]]) -> pl.DataFrame:
    """Valida payloads de municipios via Pydantic e normaliza em Polars DataFrame."""
    rows: list[dict[str, Any]] = []
    for item in raw_items:
        mun = LocalidadeMunicipioPayload.model_validate(item)
        uf = mun.regiao_imediata.regiao_intermediaria.UF
        regiao = uf.regiao
        rows.append(
            {
                "municipio_id": mun.id,
                "municipio_nome": mun.nome.strip(),
                "uf_id": uf.id,
                "uf_sigla": uf.sigla.strip().upper(),
                "uf_nome": uf.nome.strip(),
                "regiao_id": regiao.id,
                "regiao_sigla": regiao.sigla.strip().upper(),
                "regiao_nome": regiao.nome.strip(),
                "regiao_imediata_id": mun.regiao_imediata.id,
                "regiao_imediata_nome": mun.regiao_imediata.nome.strip(),
                "regiao_intermediaria_id": mun.regiao_imediata.regiao_intermediaria.id,
                "regiao_intermediaria_nome": mun.regiao_imediata.regiao_intermediaria.nome.strip(),
                "microrregiao_id": mun.microrregiao.id if mun.microrregiao else None,
                "microrregiao_nome": (mun.microrregiao.nome.strip() if mun.microrregiao else None),
                "mesorregiao_id": (mun.microrregiao.mesorregiao.id if mun.microrregiao else None),
                "mesorregiao_nome": (
                    mun.microrregiao.mesorregiao.nome.strip() if mun.microrregiao else None
                ),
            }
        )

    return pl.DataFrame(
        rows,
        schema={
            "municipio_id": pl.Int32(),
            "municipio_nome": pl.String(),
            "uf_id": pl.Int16(),
            "uf_sigla": pl.String(),
            "uf_nome": pl.String(),
            "regiao_id": pl.Int8(),
            "regiao_sigla": pl.String(),
            "regiao_nome": pl.String(),
            "regiao_imediata_id": pl.Int32(),
            "regiao_imediata_nome": pl.String(),
            "regiao_intermediaria_id": pl.Int32(),
            "regiao_intermediaria_nome": pl.String(),
            "microrregiao_id": pl.Int32(),
            "microrregiao_nome": pl.String(),
            "mesorregiao_id": pl.Int32(),
            "mesorregiao_nome": pl.String(),
        },
    ).sort("municipio_id")


def parse_cnae_payload(raw_items: list[dict[str, Any]]) -> pl.DataFrame:
    """Valida payloads de secoes CNAE via Pydantic e enriquece com ID SIDRA 12762."""
    rows: list[dict[str, Any]] = []
    for item in raw_items:
        secao = CnaeSecaoPayload.model_validate(item)
        codigo = secao.id.strip().upper()
        rows.append(
            {
                "secao_codigo": codigo,
                "secao_descricao": secao.descricao.strip(),
                "categoria_sidra_12762_id": CNAE_SIDRA_SECOES_12762.get(codigo),
                "observacoes": "\n".join(secao.observacoes).strip() if secao.observacoes else "",
            }
        )

    return pl.DataFrame(
        rows,
        schema={
            "secao_codigo": pl.String(),
            "secao_descricao": pl.String(),
            "categoria_sidra_12762_id": pl.Int32(),
            "observacoes": pl.String(),
        },
    ).sort("secao_codigo")


def _extract_classification(
    sorted_cls: list[SidraClassificacaoPayload],
    idx: int,
) -> tuple[str, str, str]:
    if idx >= len(sorted_cls):
        return ("NONE", "NONE", "Total")
    cls_obj = sorted_cls[idx]
    if not cls_obj.categoria:
        return (cls_obj.id, "NONE", "Total")
    cat_id, cat_nome = next(iter(cls_obj.categoria.items()))
    return (cls_obj.id, str(cat_id), str(cat_nome).strip())


def flatten_sidra_response(
    agregado_id: int,
    raw_items: list[dict[str, Any]],
) -> pl.DataFrame:
    """Valida e achata a resposta JSON da API SIDRA/Agregados v3 para formato Bronze tabular.

    Preserva `valor_bruto` como string imutavel (incluindo '-', '..', '...', 'X').
    Ordena classificacoes por ID inteiro para garantir mapeamento deterministico.
    """
    rows: list[dict[str, Any]] = []

    for raw_var in raw_items:
        var_payload = SidraVariavelPayload.model_validate(raw_var)
        var_id = int(var_payload.id)

        for resultado in var_payload.resultados:
            sorted_cls = sorted(resultado.classificacoes, key=lambda c: int(c.id))
            cls1_id, cat1_id, cat1_nome = _extract_classification(sorted_cls, 0)
            cls2_id, cat2_id, cat2_nome = _extract_classification(sorted_cls, 1)

            for serie_obj in resultado.series:
                loc = serie_obj.localidade
                for periodo_id, valor_bruto in serie_obj.serie.items():
                    periodo_str = str(periodo_id).strip()
                    rows.append(
                        {
                            "agregado_id": agregado_id,
                            "variavel_id": var_id,
                            "variavel_nome": var_payload.variavel.strip(),
                            "unidade": (var_payload.unidade or "").strip(),
                            "localidade_id": str(loc.id).strip(),
                            "localidade_nome": loc.nome.strip(),
                            "nivel_territorial": loc.nivel.id.strip(),
                            "classificacao_1_id": cls1_id,
                            "categoria_1_id": cat1_id,
                            "categoria_1_nome": cat1_nome,
                            "classificacao_2_id": cls2_id,
                            "categoria_2_id": cat2_id,
                            "categoria_2_nome": cat2_nome,
                            "periodo_id": periodo_str,
                            "ano_referencia": periodo_str[:4],
                            "valor_bruto": "" if valor_bruto is None else str(valor_bruto).strip(),
                        }
                    )

    if not rows:
        return empty_sidra_dataframe()

    return pl.DataFrame(rows, schema=SIDRA_BRONZE_SCHEMA)
