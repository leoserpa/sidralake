with pib as (
    select *
    from {{ ref('int_pib_municipal_deflacionado') }}
),

geo as (
    select
        sk_municipio,
        codigo_ibge_municipio
    from {{ ref('dim_geografia') }}
    where is_current
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['p.codigo_ibge_municipio', 'p.ano_referencia']) }} as sk_pib_municipal,
        cast(g.sk_municipio as varchar) as sk_municipio,
        cast(p.codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(p.ano_referencia as integer) as ano_referencia,
        cast(p.ano_mes_base_deflator as varchar) as ano_mes_base_deflator,
        cast(p.fator_deflator_anual as double) as fator_deflator_anual,
        cast(p.pib_nominal_mil_brl as double) as pib_nominal_mil_brl,
        cast(p.pib_real_mil_brl as double) as pib_real_mil_brl,
        cast(p.impostos_liquidos_mil_brl as double) as impostos_liquidos_mil_brl,
        cast(p.vab_total_mil_brl as double) as vab_total_mil_brl,
        cast(p.vab_agropecuaria_mil_brl as double) as vab_agropecuaria_mil_brl,
        cast(p.vab_industria_mil_brl as double) as vab_industria_mil_brl,
        cast(p.vab_servicos_privados_mil_brl as double) as vab_servicos_privados_mil_brl,
        cast(p.vab_adm_publica_mil_brl as double) as vab_adm_publica_mil_brl,
        cast(p.share_vab_agropecuaria as double) as share_vab_agropecuaria,
        cast(p.share_vab_industria as double) as share_vab_industria,
        cast(p.share_vab_servicos_privados as double) as share_vab_servicos_privados,
        cast(p.share_vab_adm_publica as double) as share_vab_adm_publica,
        cast(p.hhi_setorial as double) as hhi_setorial,
        cast(p.indice_diversificacao_setorial as double) as indice_diversificacao_setorial,
        cast(p.crescimento_pib_real_yoy_pct as double) as crescimento_pib_real_yoy_pct,
        cast(p.cagr_pib_real_3a_pct as double) as cagr_pib_real_3a_pct
    from pib as p
    inner join geo as g
        on p.codigo_ibge_municipio = g.codigo_ibge_municipio
)

select *
from final
