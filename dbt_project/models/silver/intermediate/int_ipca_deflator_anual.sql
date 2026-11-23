with ipca_mensal as (
    select
        ano_mes,
        ano_referencia,
        mes_referencia,
        data_referencia,
        numero_indice_ipca,
        variacao_mensal_pct,
        variacao_acum_3m_pct,
        variacao_acum_6m_pct,
        variacao_acum_ano_pct,
        variacao_acum_12m_pct
    from {{ ref('stg_ibge__ipca_mensal') }}
    where numero_indice_ipca is not null
),

indice_base_atual as (
    select
        ano_mes as ano_mes_base_deflator,
        numero_indice_ipca as numero_indice_base_atual
    from ipca_mensal
    order by ano_mes desc
    limit 1
),

mensal_com_deflator as (
    select
        m.ano_mes,
        m.ano_referencia,
        m.mes_referencia,
        m.data_referencia,
        m.numero_indice_ipca,
        m.variacao_mensal_pct,
        m.variacao_acum_3m_pct,
        m.variacao_acum_6m_pct,
        m.variacao_acum_ano_pct,
        m.variacao_acum_12m_pct,
        b.ano_mes_base_deflator,
        b.numero_indice_base_atual,
        b.numero_indice_base_atual / nullif(m.numero_indice_ipca, 0) as fator_deflator_mensal
    from ipca_mensal as m
    cross join indice_base_atual as b
),

deflator_anual as (
    select
        ano_referencia,
        max(ano_mes_base_deflator) as ano_mes_base_deflator,
        avg(numero_indice_ipca) as numero_indice_medio_anual,
        max(numero_indice_base_atual) / nullif(avg(numero_indice_ipca), 0) as fator_deflator_anual,
        count(*) as meses_observados_no_ano
    from mensal_com_deflator
    group by 1
)

select *
from deflator_anual
