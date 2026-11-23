"""Fixtures compartilhadas reproduzindo payloads reais das APIs oficiais do IBGE."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ibge_market_intel.config import PipelineSettings


@pytest.fixture
def tmp_settings(tmp_path: Path) -> PipelineSettings:
    """Retorna PipelineSettings apontando para diretorio temporario isolado."""
    settings = PipelineSettings(
        data_dir=tmp_path / "data",
        max_concurrency=4,
        request_timeout_s=10.0,
        retry_max_attempts=3,
        log_format="console",
    )
    settings.ensure_directories()
    return settings


@pytest.fixture
def sample_localidades_payload() -> list[dict[str, Any]]:
    """Inclui SP, Campinas e o edge case real Boa Esperanca do Norte (microrregiao=None)."""
    return [
        {
            "id": 3550308,
            "nome": "São Paulo",
            "microrregiao": {
                "id": 35061,
                "nome": "São Paulo",
                "mesorregiao": {
                    "id": 3515,
                    "nome": "Metropolitana de São Paulo",
                    "UF": {
                        "id": 35,
                        "sigla": "SP",
                        "nome": "São Paulo",
                        "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"},
                    },
                },
            },
            "regiao-imediata": {
                "id": 350001,
                "nome": "São Paulo",
                "regiao-intermediaria": {
                    "id": 3501,
                    "nome": "São Paulo",
                    "UF": {
                        "id": 35,
                        "sigla": "SP",
                        "nome": "São Paulo",
                        "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"},
                    },
                },
            },
        },
        {
            "id": 3509502,
            "nome": "Campinas",
            "microrregiao": {
                "id": 35032,
                "nome": "Campinas",
                "mesorregiao": {
                    "id": 3507,
                    "nome": "Campinas",
                    "UF": {
                        "id": 35,
                        "sigla": "SP",
                        "nome": "São Paulo",
                        "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"},
                    },
                },
            },
            "regiao-imediata": {
                "id": 350038,
                "nome": "Campinas",
                "regiao-intermediaria": {
                    "id": 3510,
                    "nome": "Campinas",
                    "UF": {
                        "id": 35,
                        "sigla": "SP",
                        "nome": "São Paulo",
                        "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"},
                    },
                },
            },
        },
        {
            "id": 5101837,
            "nome": "Boa Esperança do Norte",
            "microrregiao": None,
            "regiao-imediata": {
                "id": 510012,
                "nome": "Sorriso",
                "regiao-intermediaria": {
                    "id": 5103,
                    "nome": "Sinop",
                    "UF": {
                        "id": 51,
                        "sigla": "MT",
                        "nome": "Mato Grosso",
                        "regiao": {"id": 5, "sigla": "CO", "nome": "Centro-Oeste"},
                    },
                },
            },
        },
    ]


@pytest.fixture
def sample_cnae_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": "A",
            "descricao": "AGRICULTURA, PECUÁRIA, PRODUÇÃO FLORESTAL, PESCA E AQÜICULTURA",
            "observacoes": ["Secao A"],
        },
        {
            "id": "C",
            "descricao": "INDÚSTRIAS DE TRANSFORMAÇÃO",
            "observacoes": [],
        },
        {
            "id": "G",
            "descricao": "COMÉRCIO; REPARAÇÃO DE VEÍCULOS AUTOMOTORES E MOTOCICLETAS",
            "observacoes": ["Comercio atacadista e varejista"],
        },
    ]


@pytest.fixture
def sample_sidra_pib_payload() -> list[dict[str, Any]]:
    """Payload SIDRA 5938 com valores numericos e codigo especial '...'."""
    return [
        {
            "id": "37",
            "variavel": "Produto Interno Bruto a preços correntes",
            "unidade": "Mil Reais",
            "resultados": [
                {
                    "classificacoes": [],
                    "series": [
                        {
                            "localidade": {
                                "id": "3550308",
                                "nivel": {"id": "N6", "nome": "Município"},
                                "nome": "São Paulo - SP",
                            },
                            "serie": {"2023": "828980607"},
                        },
                        {
                            "localidade": {
                                "id": "5101837",
                                "nivel": {"id": "N6", "nome": "Município"},
                                "nome": "Boa Esperança do Norte - MT",
                            },
                            "serie": {"2023": "..."},
                        },
                    ],
                }
            ],
        }
    ]


@pytest.fixture
def sample_sidra_pmc_payload() -> list[dict[str, Any]]:
    """Payload SIDRA 8883 com 2 classificacoes (85 e 11046) e codigos 'X' e '-'."""
    return [
        {
            "id": "7169",
            "variavel": "PMC - Número-índice (2022=100)",
            "unidade": "Número-índice",
            "resultados": [
                {
                    "classificacoes": [
                        {
                            "id": "11046",
                            "nome": "Tipos de índice",
                            "categoria": {"56736": "Índice de volume de vendas"},
                        },
                        {
                            "id": "85",
                            "nome": "Atividades",
                            "categoria": {"90672": "Hipermercados, supermercados"},
                        },
                    ],
                    "series": [
                        {
                            "localidade": {
                                "id": "35",
                                "nivel": {"id": "N3", "nome": "Unidade da Federação"},
                                "nome": "São Paulo",
                            },
                            "serie": {"202401": "104.5", "202402": "-"},
                        },
                        {
                            "localidade": {
                                "id": "51",
                                "nivel": {"id": "N3", "nome": "Unidade da Federação"},
                                "nome": "Mato Grosso",
                            },
                            "serie": {"202401": "X", "202402": ".."},
                        },
                    ],
                }
            ],
        }
    ]
