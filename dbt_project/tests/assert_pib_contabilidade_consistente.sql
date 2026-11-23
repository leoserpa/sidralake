-- Reconciliacao contabil macroeconomica: PIB = VAB Total + Impostos Liquidos sobre Produtos
-- Tolera ate 1% (ou R$ 5 mil) devido a arredondamentos em milhares de reais do IBGE.
select
    codigo_ibge_municipio,
    ano_referencia,
    pib_nominal_mil_brl,
    vab_total_mil_brl,
    impostos_liquidos_mil_brl,
    abs(pib_nominal_mil_brl - (vab_total_mil_brl + impostos_liquidos_mil_brl)) as diferenca_abs
from {{ ref('fct_pib_municipal') }}
where pib_nominal_mil_brl is not null
    and vab_total_mil_brl is not null
    and impostos_liquidos_mil_brl is not null
    and abs(pib_nominal_mil_brl - (vab_total_mil_brl + impostos_liquidos_mil_brl))
        > greatest(5.0, abs(pib_nominal_mil_brl) * 0.01)
