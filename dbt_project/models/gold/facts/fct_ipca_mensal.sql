with ipca as (
    select *
    from {{ ref('stg_ibge__ipca_mensal') }}
),

base_atual as (
    select
        ano_mes as ano_mes_base_deflator,
        numero_indice_ipca as numero_indice_base_atual
    from ipca
    where numero_indice_ipca is not null
    order by ano_mes desc
    limit 1
),

final as (
    select
        cast(i.ano_mes as varchar) as ano_mes,
        cast(i.ano_referencia as integer) as ano_referencia,
        cast(i.mes_referencia as integer) as mes_referencia,
        cast(i.data_referencia as date) as data_referencia,
        cast(i.numero_indice_ipca as double) as numero_indice_ipca,
        cast(i.variacao_mensal_pct as double) as variacao_mensal_pct,
        cast(i.variacao_acum_3m_pct as double) as variacao_acum_3m_pct,
        cast(i.variacao_acum_6m_pct as double) as variacao_acum_6m_pct,
        cast(i.variacao_acum_ano_pct as double) as variacao_acum_ano_pct,
        cast(i.variacao_acum_12m_pct as double) as variacao_acum_12m_pct,
        cast(b.ano_mes_base_deflator as varchar) as ano_mes_base_deflator,
        cast(b.numero_indice_base_atual / nullif(i.numero_indice_ipca, 0) as double) as fator_deflator_base_atual
    from ipca as i
    cross join base_atual as b
)

select *
from final
