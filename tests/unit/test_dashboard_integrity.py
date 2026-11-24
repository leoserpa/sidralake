"""Testes unitarios e de regressao que protegem o dashboard Evidence.dev contra bugs recorrentes."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import polars as pl
import pytest

from ibge_market_intel import cli
from ibge_market_intel.analytics.bi_export import BI_GOLD_TABLES
from ibge_market_intel.config import PipelineSettings, get_settings
from ibge_market_intel.quality.dashboard_guard import (
    validate_built_dashboard,
    validate_dashboard_queries,
    validate_dashboard_static_contracts,
)


def _seed_synthetic_bi_parquets(parquet_dir: Path) -> None:
    """Gera os 7 Parquets Gold sinteticos cobrindo todos os edge cases reais do IBGE."""
    parquet_dir.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(
        {
            "codigo_secao": ["A", "C", "G", "J"],
            "descricao_secao": [
                "AGRICULTURA, PECUARIA, PRODUCAO FLORESTAL, PESCA E AQUICULTURA",
                "INDUSTRIAS DE TRANSFORMACAO",
                "COMERCIO; REPARACAO DE VEICULOS AUTOMOTORES E MOTOCICLETAS",
                "INFORMACAO E COMUNICACAO",
            ],
            "categoria_sidra_12762_id": [117897, 117899, 117903, 117906],
        }
    ).write_parquet(parquet_dir / "dim_cnae.parquet")

    pl.DataFrame(
        {
            "codigo_ibge_municipio": [3550308, 4106902, 3545803, 5101837],
            "nome_municipio": [
                "São Paulo",
                "Curitiba",
                "Santa Bárbara d'Oeste",
                "Boa Esperança do Norte",
            ],
            "codigo_uf": [35, 41, 35, 51],
            "sigla_uf": ["SP", "PR", "SP", "MT"],
            "nome_uf": ["São Paulo", "Paraná", "São Paulo", "Mato Grosso"],
            "codigo_regiao": [3, 4, 3, 5],
            "sigla_regiao": ["SE", "S", "SE", "CO"],
            "nome_regiao": ["Sudeste", "Sul", "Sudeste", "Centro-Oeste"],
            "nome_regiao_imediata": ["São Paulo", "Curitiba", "Campinas", "Sorriso"],
            "nome_regiao_intermediaria": ["São Paulo", "Curitiba", "Campinas", "Sinop"],
        }
    ).write_parquet(parquet_dir / "dim_geografia.parquet")

    pl.DataFrame(
        {
            "ano_mes": ["201801", "202610"],
            "ano_referencia": [2018, 2026],
            "mes_referencia": [1, 10],
            "data_referencia": [dt.date(2018, 1, 1), dt.date(2026, 10, 1)],
            "numero_indice_ipca": [4900.0, 7658.7],
            "variacao_mensal_pct": [0.29, 0.14],
            "variacao_acum_3m_pct": [1.0, 0.55],
            "variacao_acum_6m_pct": [1.8, 1.9],
            "variacao_acum_ano_pct": [0.29, 4.10],
            "variacao_acum_12m_pct": [2.86, 4.63],
            "ano_mes_base_deflator": ["202610", "202610"],
            "fator_deflator_base_atual": [1.563, 1.0],
        }
    ).write_parquet(parquet_dir / "fct_ipca_mensal.parquet")

    pl.DataFrame(
        {
            "codigo_ibge_municipio": [
                3550308,
                3550308,
                3550308,
                4106902,
                4106902,
                3545803,
                5101837,
            ],
            "ano_referencia": [2021, 2022, 2023, 2022, 2023, 2023, 2025],
            "populacao_residente": [
                11_500_000,
                11_451_999,
                11_673_789,
                1_773_718,
                1_801_472,
                183_347,
                5_500,
            ],
            "area_km2": [1521.1, 1521.1, 1521.1, 434.9, 434.9, 271.0, 4700.0],
            "densidade_demografica": [7560.0, 7528.8, 7674.5, 4078.4, 4142.3, 676.5, 1.17],
            "origem_dado": [
                "ESTIMATIVA",
                "CENSO_2022",
                "ESTIMATIVA",
                "CENSO_2022",
                "ESTIMATIVA",
                "ESTIMATIVA",
                "ESTIMATIVA",
            ],
            "is_interpolado": [False] * 7,
        }
    ).write_parquet(parquet_dir / "fct_populacao_municipal.parquet")

    pl.DataFrame(
        {
            "codigo_uf": [35, 35, 41],
            "sigla_uf": ["SP", "SP", "PR"],
            "nome_uf": ["São Paulo", "São Paulo", "Paraná"],
            "sigla_regiao": ["SE", "SE", "S"],
            "nome_regiao": ["Sudeste", "Sudeste", "Sul"],
            "codigo_secao_cnae": ["G", "J", "A"],
            "descricao_secao_cnae": [
                "COMERCIO; REPARACAO DE VEICULOS",
                "INFORMACAO E COMUNICACAO",
                "AGRICULTURA E PECUARIA",
            ],
            "ano_referencia": [2024, 2024, 2024],
            "num_empresas": [1_500_000, 180_000, None],
            "pessoal_ocupado_total": [4_200_000, 750_000, None],
            "pessoal_ocupado_assalariado": [3_400_000, 620_000, None],
            "massa_salarial_real_mil_brl": [220_000_000.0, 95_000_000.0, None],
            "has_sigilo_estatistico": [False, False, True],
            "quociente_locacional_emprego": [1.05, 1.82, None],
            "quociente_locacional_massa_salarial": [1.10, 2.05, None],
            "market_share_uf_no_setor_pct": [29.8, 52.7, None],
            "crescimento_emprego_setor_yoy_pct": [3.4, 6.2, None],
            "perfil_especializacao": ["BASE_DIVERSIFICADA", "CLUSTER_DOMINANTE", "SIGILO_IBGE"],
        }
    ).write_parquet(parquet_dir / "mart_clusters_setoriais_uf.parquet")

    # Inclui 2021 (com VAB completo) e 2023 (ultimo ano completo com VAB NULL como no IBGE real)
    pl.DataFrame(
        {
            "codigo_ibge_municipio": [3550308, 3550308, 4106902, 4106902, 3545803],
            "ano_referencia": [2021, 2023, 2021, 2023, 2023],
            "is_ultimo_ano_completo": [False, True, False, True, True],
            "nome_municipio": [
                "São Paulo",
                "São Paulo",
                "Curitiba",
                "Curitiba",
                "Santa Bárbara d'Oeste",
            ],
            "codigo_uf": [35, 35, 41, 41, 35],
            "sigla_uf": ["SP", "SP", "PR", "PR", "SP"],
            "nome_uf": ["São Paulo", "São Paulo", "Paraná", "Paraná", "São Paulo"],
            "sigla_regiao": ["SE", "SE", "S", "S", "SE"],
            "nome_regiao": ["Sudeste", "Sudeste", "Sul", "Sul", "Sudeste"],
            "nome_regiao_imediata": ["São Paulo", "São Paulo", "Curitiba", "Curitiba", "Campinas"],
            "nome_regiao_intermediaria": [
                "São Paulo",
                "São Paulo",
                "Curitiba",
                "Curitiba",
                "Campinas",
            ],
            "populacao_residente": [11_500_000, 11_673_789, 1_750_000, 1_773_718, 183_347],
            "area_km2": [1521.1, 1521.1, 434.9, 434.9, 271.0],
            "densidade_demografica": [7560.0, 7674.5, 4023.0, 4078.4, 676.5],
            "origem_populacao": ["ESTIMATIVA"] * 5,
            "is_populacao_interpolada": [False] * 5,
            "ano_mes_base_deflator": ["202610"] * 5,
            "pib_nominal_mil_brl": [
                828_000_000.0,
                1_067_000_000.0,
                98_000_000.0,
                120_000_000.0,
                9_500_000.0,
            ],
            "pib_real_mil_brl": [
                1_050_000_000.0,
                1_234_259_000.0,
                122_000_000.0,
                142_000_000.0,
                11_200_000.0,
            ],
            "pib_per_capita_real_brl": [91_304.0, 105_729.0, 69_714.0, 80_058.0, 61_086.0],
            "share_vab_agropecuaria": [0.001, None, 0.002, None, None],
            "share_vab_industria": [0.095, None, 0.180, None, None],
            "share_vab_servicos_privados": [0.832, None, 0.710, None, None],
            "share_vab_adm_publica": [0.072, None, 0.108, None, None],
            "hhi_setorial": [0.706, None, 0.548, None, None],
            "indice_diversificacao_setorial": [0.294, None, 0.452, None, None],
            "crescimento_pib_real_yoy_pct": [4.1, 3.8, 3.2, 2.9, 5.1],
            "cagr_pib_real_3a_pct": [3.5, 4.89, 2.8, 3.23, 6.4],
            "num_unidades_locais": [1_100_000, 1_200_000, 210_000, 230_000, 18_000],
            "num_empresas_atuantes": [1_050_000, 1_129_470, 195_000, 215_000, 16_500],
            "pessoal_ocupado_total": [6_200_000, 6_500_000, 920_000, 960_000, 62_000],
            "pessoal_ocupado_assalariado": [4_700_000, 4_995_000, 690_000, 726_000, 46_000],
            "massa_salarial_real_mil_brl": [
                350_000_000.0,
                380_000_000.0,
                44_000_000.0,
                47_000_000.0,
                2_100_000.0,
            ],
            "salario_medio_real_brl": [6100.0, 6280.0, 4900.0, 5150.0, 3850.0],
            "salario_medio_sm": [4.3, 4.45, 3.5, 3.65, 2.7],
            "taxa_assalariamento_formal": [0.758, 0.768, 0.750, 0.757, 0.742],
            "empresas_por_1000_hab": [91.3, 96.7, 111.4, 121.2, 90.0],
            "crescimento_empresas_yoy_pct": [5.2, 8.1, 4.0, 6.2, 7.5],
            "crescimento_emprego_yoy_pct": [2.1, 1.65, 1.8, 2.4, 3.2],
            "score_tamanho_mercado": [100.0, 100.0, 99.5, 100.0, 82.0],
            "score_poder_compra": [92.0, 93.5, 86.0, 88.2, 74.5],
            "score_dinamismo": [38.0, 41.0, 35.0, 37.5, 58.0],
            "score_maturidade_empresarial": [88.0, 89.2, 84.0, 85.1, 71.0],
            "ims_score_0_100": [77.1, 78.33, 75.0, 76.8, 69.4],
            "rank_nacional_ims": [25, 23, 35, 31, 180],
            "rank_estadual_ims": [11, 10, 2, 2, 42],
            "rank_regional_ims": [14, 12, 3, 3, 55],
            "tier_mercado": [
                "Tier 1 - Polo Nacional",
                "Tier 1 - Polo Nacional",
                "Tier 1 - Polo Nacional",
                "Tier 1 - Polo Nacional",
                "Tier 2 - Expansao Prioritaria",
            ],
        }
    ).write_parquet(parquet_dir / "mart_inteligencia_mercado_municipal.parquet")

    pl.DataFrame(
        {
            "codigo_uf": [35, 35, 41],
            "sigla_uf": ["SP", "SP", "PR"],
            "nome_uf": ["São Paulo", "São Paulo", "Paraná"],
            "sigla_regiao": ["SE", "SE", "S"],
            "codigo_atividade_pmc": [103154, 103155, 103154],
            "nome_atividade_pmc": [
                "Hipermercados e supermercados",
                "Combustíveis e lubrificantes",
                "Hipermercados e supermercados",
            ],
            "grupo_consumo": [
                "ALIMENTACAO_ATACAREJO",
                "COMBUSTIVEIS",
                "ALIMENTACAO_ATACAREJO",
            ],
            "ano_mes": ["202609", "202609", "202609"],
            "ano_referencia": [2026, 2026, 2026],
            "mes_referencia": [9, 9, 9],
            "data_referencia": [dt.date(2026, 9, 1)] * 3,
            "indice_receita_nominal": [132.5, 118.0, 129.0],
            "indice_volume_vendas": [112.4, 98.5, 110.2],
            "indice_volume_vendas_sa": [113.0, 99.0, 110.8],
            "var_mom_sa_volume_pct": [0.6, -1.2, 0.4],
            "var_yoy_receita_nominal_pct": [7.8, 3.1, 6.9],
            "var_yoy_volume_pct": [3.5, -2.4, 2.8],
            "var_acum_12m_volume_pct": [4.2, -0.8, 3.1],
            "ipca_variacao_mensal_pct": [0.14, 0.14, 0.14],
            "ipca_variacao_acum_12m_pct": [4.58, 4.58, 4.58],
            "spread_preco_vs_volume_yoy_pp": [4.3, 5.5, 4.1],
            "spread_volume_vs_ipca_12m_pp": [-1.08, -6.98, -1.78],
            "media_movel_3m_volume": [111.8, 99.1, 109.7],
            "media_movel_12m_volume": [110.2, 100.4, 108.5],
            "regime_consumo": ["EXPANSAO_REAL", "RETRACAO", "EXPANSAO_REAL"],
        }
    ).write_parquet(parquet_dir / "mart_pulso_consumo_macro.parquet")

    pl.DataFrame(
        {
            "sk_pulso_servicos": ["sk_pms_sp", "sk_pms_pr"],
            "codigo_uf": [35, 41],
            "sigla_uf": ["SP", "PR"],
            "nome_uf": ["São Paulo", "Paraná"],
            "sigla_regiao": ["SE", "S"],
            "nome_regiao": ["Sudeste", "Sul"],
            "ano_mes": ["202609", "202609"],
            "ano_referencia": [2026, 2026],
            "mes_referencia": [9, 9],
            "data_referencia": [dt.date(2026, 9, 1), dt.date(2026, 9, 1)],
            "indice_receita_nominal": [134.9, 128.4],
            "indice_receita_nominal_sa": [134.2, 127.8],
            "var_mom_sa_receita_pct": [0.3, 0.5],
            "var_yoy_receita_nominal_pct": [5.9, 6.2],
            "var_acum_12m_receita_pct": [8.4, 7.5],
            "indice_volume_servicos": [110.9, 108.3],
            "indice_volume_servicos_sa": [109.9, 107.6],
            "var_mom_sa_volume_pct": [-0.2, 0.4],
            "var_yoy_volume_pct": [2.4, 3.1],
            "var_acum_12m_volume_pct": [3.0, 3.6],
            "ipca_variacao_mensal_pct": [0.14, 0.14],
            "ipca_variacao_acum_12m_pct": [4.58, 4.58],
            "spread_preco_vs_volume_yoy_pp": [3.5, 3.1],
            "spread_volume_vs_ipca_12m_pp": [-1.58, -0.98],
            "media_movel_3m_volume": [110.5, 107.9],
            "media_movel_12m_volume": [109.2, 106.5],
            "regime_servicos": ["EXPANSAO_REAL", "EXPANSAO_REAL"],
        }
    ).write_parquet(parquet_dir / "mart_pulso_servicos_uf.parquet")

    pl.DataFrame(
        {
            "sk_mercado_trabalho": ["sk_pnad_sp", "sk_pnad_pr"],
            "codigo_uf": [35, 41],
            "sigla_uf": ["SP", "PR"],
            "nome_uf": ["São Paulo", "Paraná"],
            "sigla_regiao": ["SE", "S"],
            "nome_regiao": ["Sudeste", "Sul"],
            "ano_trimestre": ["202603", "202603"],
            "label_trimestre": ["3T/2026", "3T/2026"],
            "ano_referencia": [2026, 2026],
            "trimestre_referencia": [3, 3],
            "data_referencia": [dt.date(2026, 7, 1), dt.date(2026, 7, 1)],
            "is_ultimo_trimestre": [True, True],
            "taxa_desocupacao_pct": [5.4, 3.9],
            "taxa_desocupacao_subocupacao_pct": [8.3, 6.1],
            "taxa_desocupacao_forca_potencial_pct": [8.1, 6.2],
            "taxa_subutilizacao_composta_pct": [11.0, 8.2],
            "var_yoy_desocupacao_pp": [-0.8, -0.5],
            "rendimento_medio_real_brl": [4543.0, 3980.0],
            "rendimento_homens_real_brl": [5133.0, 4490.0],
            "rendimento_mulheres_real_brl": [3821.0, 3360.0],
            "var_yoy_rendimento_real_pct": [4.2, 5.4],
            "hiato_salarial_genero_pct": [-25.56, -25.17],
        }
    ).write_parquet(parquet_dir / "mart_mercado_trabalho_uf.parquet")


def test_dashboard_static_contracts_pass() -> None:
    """Garante que configuracao, layout, sources, SQL e componentes Evidence estao integros."""
    root = get_settings().project_root
    issues = validate_dashboard_static_contracts(root)
    assert issues == [], "Violacoes estaticas no dashboard:\n" + "\n".join(
        f"  - [{i.rule}] {i.file}: {i.message}" for i in issues
    )


def test_all_dashboard_sql_queries_pass_under_evidence_double_emulation(tmp_path: Path) -> None:
    """Executa todas as queries reais das 7 paginas emulando DOUBLE do DuckDB-WASM."""
    root = get_settings().project_root
    parquet_dir = tmp_path / "parquet_data"
    _seed_synthetic_bi_parquets(parquet_dir)

    executed, issues = validate_dashboard_queries(
        root,
        parquet_dir,
        emulate_evidence_double=True,
        require_non_empty=True,
    )
    assert executed >= 50
    assert issues == [], "Falhas nas queries do dashboard:\n" + "\n".join(
        f"  - [{i.rule}] {i.file}: {i.message}" for i in issues
    )


def test_guard_catches_static_anti_patterns(tmp_path: Path) -> None:
    """Testes negativos: prova que os guardioes bloqueiam os bugs reais que ja ocorreram."""
    dash = tmp_path / "dashboard"
    sources = dash / "sources" / "sidralake"
    pages = dash / "pages"
    wf_dir = tmp_path / ".github" / "workflows"
    sources.mkdir(parents=True)
    pages.mkdir(parents=True)
    wf_dir.mkdir(parents=True)

    # 1. Parquet colocado erroneamente dentro de sources/ e source com caminho errado
    (sources / "bad.parquet").write_bytes(b"PAR1")
    (sources / "dim_cnae.sql").write_text(
        "select * from read_parquet('sources/wrong.parquet')", encoding="utf-8"
    )
    # 2. Layout sem neverShowQueries={true}
    (pages / "+layout.svelte").write_text("<EvidenceDefaultLayout {data} />", encoding="utf-8")
    # 3. Config sem basePath e package.json com typescript v7 e sem script test:e2e
    (dash / "evidence.config.yaml").write_text("deployment:\n  basePath: /\n", encoding="utf-8")
    (dash / "package.json").write_text(
        json.dumps({"devDependencies": {"typescript": "^7.0.0"}, "overrides": {}}),
        encoding="utf-8",
    )
    (wf_dir / "pages.yml").write_text("name: Pages\n", encoding="utf-8")

    # 4. Pagina contendo todos os anti-padroes proibidos (incluindo => antes de data={...})
    (pages / "broken.md").write_text(
        """
```sql q_bad
select
    m.ano_referencia::varchar as ano,
    sigla_uf
from sidralake.tabela_inexistente as m
where codigo_ibge_municipio = '${inputs.cidade.value}'
  and ano_referencia = '${inputs.ano.value}'
```

```sql q_bad
select 1 as x
```

<Dropdown data={q_bad} name=cidade value=nome_municipio defaultValue="São Paulo" />
<BarChart
    data={q_bad}
    x=ano
    y=sigla_uf
    type="stacked"
    swapXY={true}
    labels={true}
    rightPadding=10
/>
<BarChart
    data={q_good_quoted}
    x=ano
    y=sigla_uf
    type="stacked"
    swapXY={true}
    labels={true}
    stackTotalLabel={false}
    rightPadding={32}
/>
<LineChart data={q_missing} x=ano y={["a", "b"]} seriesColors={{'a': '#fff'}} />
<ECharts config={{ fn: (a) => a > 0 }} data={q_missing_after_arrow} />
""",
        encoding="utf-8",
    )

    issues = validate_dashboard_static_contracts(tmp_path)
    rules = {i.rule for i in issues}
    assert {
        "no_binary_in_sources",
        "source_table_parity",
        "source_parquet_path",
        "layout_security_and_ux",
        "evidence_config_basepath",
        "typescript_pin",
        "e2e_smoke_script",
        "pages_workflow_guardrails",
        "page_frontmatter",
        "duplicate_query_name",
        "unknown_source_table",
        "no_double_to_varchar_year_cast",
        "safe_input_casting",
        "missing_query_ref",
        "stacked_barchart_no_double_labels",
        "swapxy_label_padding",
        "city_dropdown_id_binding",
        "multi_y_linechart_color_palette",
    }.issubset(rules)
    # Garante que o scanner de tags Svelte nao truncou em `=>` dentro de <ECharts>
    assert any("q_missing_after_arrow" in i.message for i in issues)
    # Garante que BarChart valido com type="stacked" labels={true} stackTotalLabel={false}
    # e rightPadding={32} nao gera falso positivo em stacked_barchart_no_double_labels / padding
    assert not any(
        i.rule in ("stacked_barchart_no_double_labels", "swapxy_label_padding")
        and "q_good_quoted" in i.message
        for i in issues
    )


def test_guard_catches_runtime_scale_and_format_regressions(tmp_path: Path) -> None:
    """Testes negativos: detecta bug 100x _pct, '2024.0', '202610' e enum cru."""
    parquet_dir = tmp_path / "parquet_data"
    _seed_synthetic_bi_parquets(parquet_dir)

    dash = tmp_path / "dashboard"
    sources = dash / "sources" / "sidralake"
    pages = dash / "pages"
    sources.mkdir(parents=True)
    pages.mkdir(parents=True)

    (pages / "regressao.md").write_text(
        """---
title: Regressao
---

```sql q_regressao
select
    cast(ano_referencia as varchar) as ano,
    '202610' as competencia,
    'EXPANSAO_REAL' as regime,
    cagr_pib_real_3a_pct as cagr_3a_pct,
    52.7 as share_br_pct,
    '4.5%' as texto_pct
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
```

<DataTable data={q_regressao} />
""",
        encoding="utf-8",
    )

    executed, issues = validate_dashboard_queries(
        tmp_path, parquet_dir, emulate_evidence_double=True
    )
    assert executed == 1
    rules = {i.rule for i in issues}
    assert "pct_scale_0_1" in rules
    assert "pct_numeric_type" in rules
    assert "datatable_ano_format" in rules
    assert "competencia_mm_yyyy" in rules
    assert "no_raw_enum_labels" in rules


def test_validate_built_dashboard_and_cli_validate_bi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Valida verificacao de artefato estatico (build/) e comando CLI `sidralake validate-bi`."""
    root = get_settings().project_root
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    # Build incompleto deve falhar (.nojekyll, HTMLs e parquets ausentes)
    bad_issues = validate_built_dashboard(root, build_dir=build_dir)
    bad_rules = {i.rule for i in bad_issues}
    assert {"nojekyll_exists", "route_html_exists", "build_data_table_exists"}.issubset(bad_rules)

    # Monta build estatico valido + 1 erro fatal para testar deteccao em HTML
    (build_dir / ".nojekyll").write_text("", encoding="utf-8")
    data_dir = build_dir / "data" / "sidralake"
    data_dir.mkdir(parents=True)
    for tbl in BI_GOLD_TABLES:
        (data_dir / f"{tbl}.parquet").write_bytes(b"PAR1")

    for md in (root / "dashboard" / "pages").glob("*.md"):
        html_path = (
            build_dir / "index.html" if md.stem == "index" else build_dir / md.stem / "index.html"
        )
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text("<html><body>OK</body></html>", encoding="utf-8")

    assert validate_built_dashboard(root, build_dir=build_dir) == []

    # Injeta Catalog Error no HTML (index.html) e confirma deteccao imediata + SystemExit na CLI
    (build_dir / "index.html").write_text(
        "<html><body>Catalog Error: Table fct_ipca_mensal does not exist</body></html>",
        encoding="utf-8",
    )
    err_issues = validate_built_dashboard(root, build_dir=build_dir)
    assert any(i.rule == "build_html_no_fatal_error" for i in err_issues)

    parquet_dir = tmp_path / "parquet_data"
    _seed_synthetic_bi_parquets(parquet_dir)
    monkeypatch.setattr(cli, "get_settings", lambda: PipelineSettings(project_root=root))

    with pytest.raises(SystemExit, match="FALHA na validacao do dashboard BI"):
        cli.validate_bi(parquet_dir=parquet_dir, check_build=True, build_dir=build_dir)

    # Restaura HTML valido e valida CLI `sidralake validate-bi --check-build`
    (build_dir / "index.html").write_text("<html><body>OK</body></html>", encoding="utf-8")

    cli.main(
        [
            "validate-bi",
            "--parquet-dir",
            str(parquet_dir),
            "--check-build",
            "--build-dir",
            str(build_dir),
        ]
    )
    out = capsys.readouterr().out
    assert "OK: dashboard BI validado" in out

    # --parquet-dir explicito inexistente deve falhar mesmo com --check-build
    with pytest.raises(FileNotFoundError, match="Diretorio Parquet BI nao encontrado"):
        cli.validate_bi(
            parquet_dir=tmp_path / "nao_existe",
            check_build=True,
            build_dir=build_dir,
        )
