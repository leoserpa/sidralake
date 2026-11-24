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

pivoted as (
    select
        codigo_uf,
        ano_mes,
        ano_referencia,
        mes_referencia,
        data_referencia,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 7167 then valor_numerico end)
            as indice_receita_nominal,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 7168 then valor_numerico end)
            as indice_receita_nominal_sa,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11623 then valor_numerico end)
            as var_mom_sa_receita_pct,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11624 then valor_numerico end)
            as var_yoy_receita_nominal_pct,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11626 then valor_numerico end)
            as var_acum_12m_receita_pct,
        max(case when tipo_indice = 'VOLUME_SERVICOS' and variavel_id = 7167 then valor_numerico end)
            as indice_volume_servicos,
        max(case when tipo_indice = 'VOLUME_SERVICOS' and variavel_id = 7168 then valor_numerico end)
            as indice_volume_servicos_sa,
        max(case when tipo_indice = 'VOLUME_SERVICOS' and variavel_id = 11623 then valor_numerico end)
            as var_mom_sa_volume_pct,
        max(case when tipo_indice = 'VOLUME_SERVICOS' and variavel_id = 11624 then valor_numerico end)
            as var_yoy_volume_pct,
        max(case when tipo_indice = 'VOLUME_SERVICOS' and variavel_id = 11626 then valor_numerico end)
            as var_acum_12m_volume_pct
    from {{ ref('stg_ibge__pms_servicos_uf') }}
    group by 1, 2, 3, 4, 5
),

joined as (
    select
        p.*,
        u.sigla_uf,
        u.nome_uf,
        u.sigla_regiao,
        u.nome_regiao,
        i.variacao_mensal_pct as ipca_variacao_mensal_pct,
        i.variacao_acum_12m_pct as ipca_variacao_acum_12m_pct
    from pivoted as p
    inner join ufs as u
        on p.codigo_uf = u.codigo_uf
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
        avg(indice_volume_servicos) over (
            partition by codigo_uf
            order by data_referencia
            rows between 2 preceding and current row
        ) as media_movel_3m_volume,
        avg(indice_volume_servicos) over (
            partition by codigo_uf
            order by data_referencia
            rows between 11 preceding and current row
        ) as media_movel_12m_volume
    from joined
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_uf', 'ano_mes']) }} as sk_pulso_servicos,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(nome_regiao as varchar) as nome_regiao,
        cast(ano_mes as varchar) as ano_mes,
        cast(ano_referencia as integer) as ano_referencia,
        cast(mes_referencia as integer) as mes_referencia,
        cast(data_referencia as date) as data_referencia,
        cast(indice_receita_nominal as double) as indice_receita_nominal,
        cast(indice_receita_nominal_sa as double) as indice_receita_nominal_sa,
        cast(var_mom_sa_receita_pct as double) as var_mom_sa_receita_pct,
        cast(var_yoy_receita_nominal_pct as double) as var_yoy_receita_nominal_pct,
        cast(var_acum_12m_receita_pct as double) as var_acum_12m_receita_pct,
        cast(indice_volume_servicos as double) as indice_volume_servicos,
        cast(indice_volume_servicos_sa as double) as indice_volume_servicos_sa,
        cast(var_mom_sa_volume_pct as double) as var_mom_sa_volume_pct,
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
        ) as regime_servicos
    from rolling
)

select *
from final
