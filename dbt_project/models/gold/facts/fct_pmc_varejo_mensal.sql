with pivoted as (
    select
        codigo_uf,
        codigo_atividade_pmc,
        ano_mes,
        ano_referencia,
        mes_referencia,
        data_referencia,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 7169 then valor_numerico end) as indice_receita_nominal,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 7170 then valor_numerico end) as indice_receita_nominal_sa,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11708 then valor_numerico end) as var_mom_sa_receita_pct,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11709 then valor_numerico end) as var_yoy_receita_nominal_pct,
        max(case when tipo_indice = 'RECEITA_NOMINAL' and variavel_id = 11711 then valor_numerico end) as var_acum_12m_receita_pct,
        max(case when tipo_indice = 'VOLUME_VENDAS' and variavel_id = 7169 then valor_numerico end) as indice_volume_vendas,
        max(case when tipo_indice = 'VOLUME_VENDAS' and variavel_id = 7170 then valor_numerico end) as indice_volume_vendas_sa,
        max(case when tipo_indice = 'VOLUME_VENDAS' and variavel_id = 11708 then valor_numerico end) as var_mom_sa_volume_pct,
        max(case when tipo_indice = 'VOLUME_VENDAS' and variavel_id = 11709 then valor_numerico end) as var_yoy_volume_pct,
        max(case when tipo_indice = 'VOLUME_VENDAS' and variavel_id = 11711 then valor_numerico end) as var_acum_12m_volume_pct
    from {{ ref('stg_ibge__pmc_varejo_uf') }}
    group by 1, 2, 3, 4, 5, 6
),

ativ as (
    select
        sk_atividade_varejo,
        codigo_atividade_pmc
    from {{ ref('dim_atividade_varejo') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['p.codigo_uf', 'p.codigo_atividade_pmc', 'p.ano_mes']) }} as sk_pmc_mensal,
        cast(p.codigo_uf as integer) as codigo_uf,
        cast(a.sk_atividade_varejo as varchar) as sk_atividade_varejo,
        cast(p.codigo_atividade_pmc as integer) as codigo_atividade_pmc,
        cast(p.ano_mes as varchar) as ano_mes,
        cast(p.ano_referencia as integer) as ano_referencia,
        cast(p.mes_referencia as integer) as mes_referencia,
        cast(p.data_referencia as date) as data_referencia,
        cast(p.indice_receita_nominal as double) as indice_receita_nominal,
        cast(p.indice_receita_nominal_sa as double) as indice_receita_nominal_sa,
        cast(p.var_mom_sa_receita_pct as double) as var_mom_sa_receita_pct,
        cast(p.var_yoy_receita_nominal_pct as double) as var_yoy_receita_nominal_pct,
        cast(p.var_acum_12m_receita_pct as double) as var_acum_12m_receita_pct,
        cast(p.indice_volume_vendas as double) as indice_volume_vendas,
        cast(p.indice_volume_vendas_sa as double) as indice_volume_vendas_sa,
        cast(p.var_mom_sa_volume_pct as double) as var_mom_sa_volume_pct,
        cast(p.var_yoy_volume_pct as double) as var_yoy_volume_pct,
        cast(p.var_acum_12m_volume_pct as double) as var_acum_12m_volume_pct
    from pivoted as p
    inner join ativ as a
        on p.codigo_atividade_pmc = a.codigo_atividade_pmc
)

select *
from final
