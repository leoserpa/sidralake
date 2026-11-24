"""Catalogo tipado e verificado das APIs e agregados SIDRA do IBGE."""

from __future__ import annotations

from dataclasses import dataclass

# 27 Unidades da Federacao oficiais do IBGE
UF_CODES: tuple[int, ...] = (
    11,
    12,
    13,
    14,
    15,
    16,
    17,  # Norte
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,  # Nordeste
    31,
    32,
    33,
    35,  # Sudeste
    41,
    42,
    43,  # Sul
    50,
    51,
    52,
    53,  # Centro-Oeste
)

VALID_UF_SIGLAS: frozenset[str] = frozenset(
    {
        "RO",
        "AC",
        "AM",
        "RR",
        "PA",
        "AP",
        "TO",
        "MA",
        "PI",
        "CE",
        "RN",
        "PB",
        "PE",
        "AL",
        "SE",
        "BA",
        "MG",
        "ES",
        "RJ",
        "SP",
        "PR",
        "SC",
        "RS",
        "MS",
        "MT",
        "GO",
        "DF",
    }
)

# 21 secoes CNAE 2.0 na classificacao SIDRA 12762 (verificadas ao vivo no agregado 9418)
CNAE_SIDRA_SECOES_12762: dict[str, int] = {
    "A": 116830,
    "B": 116880,
    "C": 116910,
    "D": 117296,
    "E": 117307,
    "F": 117329,
    "G": 117363,
    "H": 117484,
    "I": 117543,
    "J": 117555,
    "K": 117608,
    "L": 117666,
    "M": 117673,
    "N": 117714,
    "O": 117774,
    "P": 117788,
    "Q": 117810,
    "R": 117838,
    "S": 117861,
    "T": 117888,
    "U": 117892,
}

# 14 atividades da PMC (classificacao SIDRA 85, agregado 8883)
PMC_ATIVIDADES_85: tuple[int, ...] = (
    90671,  # Combustiveis e lubrificantes
    90672,  # Hipermercados, supermercados, produtos alimenticios, bebidas e fumo
    103154,  # Hipermercados e supermercados
    90673,  # Tecidos, vestuario e calcados
    2759,  # Moveis e eletrodomesticos
    31555,  # Moveis
    31556,  # Eletrodomesticos
    103155,  # Artigos farmaceuticos, medicos, ortopedicos, perfumaria e cosmeticos
    103156,  # Livros, jornais, revistas e papelaria
    103157,  # Equipamentos e materiais para escritorio, informatica e comunicacao
    103158,  # Outros artigos de uso pessoal e domestico
    103159,  # Veiculos, motocicletas, partes e pecas
    2762,  # Material de construcao
    56741,  # Atacado especializado em produtos alimenticios, bebidas e fumo
)

# Janelas padrao de backfill (particionadas por ano_referencia)
PIB_YEARS: tuple[str, ...] = ("2018", "2019", "2020", "2021", "2022", "2023")
CENSO_YEARS: tuple[str, ...] = ("2022",)
ESTIMATIVA_POP_YEARS: tuple[str, ...] = ("2018", "2019", "2020", "2021", "2024", "2025", "2026")
CEMPRE_YEARS: tuple[str, ...] = ("2022", "2023", "2024")
IPCA_YEARS: tuple[str, ...] = (
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026",
)
PMC_YEARS: tuple[str, ...] = ("2020", "2021", "2022", "2023", "2024", "2025", "2026")


@dataclass(frozen=True)
class AgregadoSpec:
    """Especificacao declarativa de um agregado da API SIDRA/Agregados v3 do IBGE."""

    table_name: str
    agregado_id: int
    descricao: str
    variaveis: tuple[int, ...]
    nivel_territorial: str  # "N1", "N3", "N6"
    periodicidade: str  # "anual" | "mensal"
    classificacoes: dict[int, tuple[int, ...]]
    chunk_by_uf: bool = False
    chunk_months_half_year: bool = False
    min_year: int = 2018

    def classificacao_param(self) -> str | None:
        if not self.classificacoes:
            return None
        parts = [
            f"{cid}[{','.join(str(v) for v in sorted(cats))}]"
            for cid, cats in sorted(self.classificacoes.items())
        ]
        return "|".join(parts)


PIB_MUNICIPAL_SPEC = AgregadoSpec(
    table_name="pib_municipal",
    agregado_id=5938,
    descricao="PIB dos Municipios a precos correntes, impostos e VAB por setor",
    variaveis=(37, 543, 498, 513, 517, 6575, 525),
    nivel_territorial="N6",
    periodicidade="anual",
    classificacoes={},
    chunk_by_uf=True,
    min_year=2018,
)

CENSO_POPULACAO_SPEC = AgregadoSpec(
    table_name="censo_populacao",
    agregado_id=4714,
    descricao="Censo Demografico 2022: Populacao residente, area territorial e densidade",
    variaveis=(93, 6318, 614),
    nivel_territorial="N6",
    periodicidade="anual",
    classificacoes={},
    chunk_by_uf=False,
    min_year=2022,
)

ESTIMATIVA_POPULACAO_SPEC = AgregadoSpec(
    table_name="estimativa_populacao",
    agregado_id=6579,
    descricao="Estimativas anuais de populacao residente por municipio",
    variaveis=(9324,),
    nivel_territorial="N6",
    periodicidade="anual",
    classificacoes={},
    chunk_by_uf=False,
    min_year=2018,
)

CEMPRE_MUNICIPAL_SPEC = AgregadoSpec(
    table_name="cempre_municipal",
    agregado_id=9509,
    descricao="CEMPRE (nova serie 2022+): empresas, unidades locais, emprego e salarios municipais",
    variaveis=(706, 367, 707, 708, 5944, 662, 1606, 10143),
    nivel_territorial="N6",
    periodicidade="anual",
    classificacoes={},
    chunk_by_uf=True,
    min_year=2022,
)

CEMPRE_SETORIAL_UF_SPEC = AgregadoSpec(
    table_name="cempre_setorial_uf",
    agregado_id=9418,
    descricao="CEMPRE setorial (nova serie 2022+) por UF e secao CNAE 2.0",
    variaveis=(2585, 707, 708, 662),
    nivel_territorial="N3",
    periodicidade="anual",
    classificacoes={12762: tuple(CNAE_SIDRA_SECOES_12762.values())},
    chunk_by_uf=False,
    min_year=2022,
)

IPCA_MENSAL_SPEC = AgregadoSpec(
    table_name="ipca_mensal",
    agregado_id=1737,
    descricao="IPCA serie historica mensal (numero-indice e variacoes)",
    variaveis=(2266, 63, 2263, 2264, 69, 2265),
    nivel_territorial="N1",
    periodicidade="mensal",
    classificacoes={},
    chunk_by_uf=False,
    min_year=2018,
)

PMC_VAREJO_UF_SPEC = AgregadoSpec(
    table_name="pmc_varejo_uf",
    agregado_id=8883,
    descricao="PMC varejo ampliado por UF, tipo de indice e 14 atividades comerciais",
    variaveis=(7169, 7170, 11708, 11709, 11710, 11711),
    nivel_territorial="N3",
    periodicidade="mensal",
    classificacoes={
        11046: (56735, 56736),
        85: PMC_ATIVIDADES_85,
    },
    chunk_by_uf=False,
    chunk_months_half_year=True,
    min_year=2020,
)

ALL_SIDRA_SPECS: dict[str, AgregadoSpec] = {
    spec.table_name: spec
    for spec in (
        PIB_MUNICIPAL_SPEC,
        CENSO_POPULACAO_SPEC,
        ESTIMATIVA_POPULACAO_SPEC,
        CEMPRE_MUNICIPAL_SPEC,
        CEMPRE_SETORIAL_UF_SPEC,
        IPCA_MENSAL_SPEC,
        PMC_VAREJO_UF_SPEC,
    )
}
