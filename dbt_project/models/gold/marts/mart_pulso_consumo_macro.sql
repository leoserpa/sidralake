with ufs as (
    select distinct
        codigo_uf,
        sigla_uf,
        nome_uf,
        sigla_regiao,
        nome_regiao
    from {{ ref('dim_geografia') }}
    where is_current
),

base as (
    select
        p.codigo_uf,
        u.sigla_uf,
        u.nome_uf,
        u.sigla_regiao,
        p.codigo_atividade_pmc,
        a.nome_atividade_pmc,
        a.grupo_consumo,
        p.ano_mes,
        p.ano_referencia,
        p.mes_referencia,
        p.data_referencia,
        p.indice_receita_nominal,
        p.indice_volume_vendas,
        p.indice_volume_vendas_sa,
        p.var_mom_sa_volume_pct,
        p.var_yoy_receita_nominal_pct,
        p.var_yoy_volume_pct,
        p.var_acum_12m_receita_pct,
        p.var_acum_12m_volume_pct,
        i.variacao_mensal_pct as ipca_variacao_mensal_pct,
        i.variacao_acum_12m_pct as ipca_variacao_acum_12m_pct
    from {{ ref('fct_pmc_varejo_mensal') }} as p
    inner join ufs as u
        on p.codigo_uf = u.codigo_uf
    inner join {{ ref('dim_atividade_varejo') }} as a
        on p.codigo_atividade_pmc = a.codigo_atividade_pmc
    left join {{ ref('fct_ipca_mensal') }} as i
        on p.ano_mes = i.ano_mes
),

rolling as (
    select
        *,
        case
            when var_yoy_receita_nominal_pct is not null and var_yoy_volume_pct is not null
                then var_yoy_receita_nominal_pct - var_yoy_volume_pct
            else cast(null as double)
        end as spread_preco_vs_volume_yoy_pp,
        case
            when var_acum_12m_volume_pct is not null and ipca_variacao_acum_12m_pct is not null
                then var_acum_12m_volume_pct - ipca_variacao_acum_12m_pct
            else cast(null as double)
        end as spread_volume_vs_ipca_12m_pp,
        avg(indice_volume_vendas) over (
            partition by codigo_uf, codigo_atividade_pmc
            order by data_referencia
            rows between 2 preceding and current row
        ) as media_movel_3m_volume,
        avg(indice_volume_vendas) over (
            partition by codigo_uf, codigo_atividade_pmc
            order by data_referencia
            rows between 11 preceding and current row
        ) as media_movel_12m_volume
    from base
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_uf', 'codigo_atividade_pmc', 'ano_mes']) }} as sk_pulso_consumo,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(codigo_atividade_pmc as integer) as codigo_atividade_pmc,
        cast(nome_atividade_pmc as varchar) as nome_atividade_pmc,
        cast(grupo_consumo as varchar) as grupo_consumo,
        cast(ano_mes as varchar) as ano_mes,
        cast(ano_referencia as integer) as ano_referencia,
        cast(mes_referencia as integer) as mes_referencia,
        cast(data_referencia as date) as data_referencia,
        cast(indice_receita_nominal as double) as indice_receita_nominal,
        cast(indice_volume_vendas as double) as indice_volume_vendas,
        cast(indice_volume_vendas_sa as double) as indice_volume_vendas_sa,
        cast(var_mom_sa_volume_pct as double) as var_mom_sa_volume_pct,
        cast(var_yoy_receita_nominal_pct as double) as var_yoy_receita_nominal_pct,
        cast(var_yoy_volume_pct as double) as var_yoy_volume_pct,
        cast(var_acum_12m_volume_pct as double) as var_acum_12m_volume_pct,
        cast(ipca_variacao_mensal_pct as double) as ipca_variacao_mensal_pct,
        cast(ipca_variacao_acum_12m_pct as double) as ipca_variacao_acum_12m_pct,
        cast(round(spread_preco_vs_volume_yoy_pp, 2) as double) as spread_preco_vs_volume_yoy_pp,
        cast(round(spread_volume_vs_ipca_12m_pp, 2) as double) as spread_volume_vs_ipca_12m_pp,
        cast(round(media_movel_3m_volume, 2) as double) as media_movel_3m_volume,
        cast(round(media_movel_12m_volume, 2) as double) as media_movel_12m_volume,
        cast(
            case
                when var_yoy_volume_pct is null then 'SEM_DADO'
                when var_yoy_volume_pct > 2.0 then 'EXPANSAO_REAL'
                when var_yoy_volume_pct >= 0.0 and coalesce(spread_preco_vs_volume_yoy_pp, 0.0) > 4.0
                    then 'PRESSAO_INFLACIONARIA'
                when var_yoy_volume_pct >= -2.0 then 'ESTABILIDADE'
                else 'RETRACAO'
            end as varchar
        ) as regime_consumo
    from rolling
)

select *
from final
