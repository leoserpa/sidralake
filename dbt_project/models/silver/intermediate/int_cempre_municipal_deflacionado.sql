with cempre_pivoted as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        cast(round(max(case when variavel_id = 706 then valor_numerico end)) as integer) as num_unidades_locais,
        cast(round(max(case when variavel_id = 367 then valor_numerico end)) as integer) as num_empresas_atuantes,
        cast(round(max(case when variavel_id = 707 then valor_numerico end)) as integer) as pessoal_ocupado_total,
        cast(round(max(case when variavel_id = 708 then valor_numerico end)) as integer) as pessoal_ocupado_assalariado,
        cast(round(max(case when variavel_id = 5944 then valor_numerico end)) as integer) as pessoal_assalariado_medio,
        max(case when variavel_id = 662 then valor_numerico end) as massa_salarial_nominal_mil_brl,
        max(case when variavel_id = 1606 then valor_numerico end) as salario_medio_sm,
        max(case when variavel_id = 10143 then valor_numerico end) as salario_medio_nominal_brl
    from {{ ref('stg_ibge__cempre_municipal') }}
    group by 1, 2
),

deflacionado as (
    select
        c.codigo_ibge_municipio,
        c.ano_referencia,
        d.ano_mes_base_deflator,
        c.num_unidades_locais,
        c.num_empresas_atuantes,
        c.pessoal_ocupado_total,
        c.pessoal_ocupado_assalariado,
        c.pessoal_assalariado_medio,
        c.massa_salarial_nominal_mil_brl,
        c.massa_salarial_nominal_mil_brl * d.fator_deflator_anual as massa_salarial_real_mil_brl,
        c.salario_medio_sm,
        c.salario_medio_nominal_brl,
        c.salario_medio_nominal_brl * d.fator_deflator_anual as salario_medio_real_brl,
        case
            when c.pessoal_ocupado_total > 0
                then cast(c.pessoal_ocupado_assalariado as double) / c.pessoal_ocupado_total
            else cast(null as double)
        end as taxa_assalariamento_formal
    from cempre_pivoted as c
    left join {{ ref('int_ipca_deflator_anual') }} as d
        on c.ano_referencia = d.ano_referencia
),

com_yoy as (
    select
        cur.*,
        prev_1a.num_empresas_atuantes as empresas_lag_1a,
        prev_1a.pessoal_ocupado_total as pessoal_lag_1a
    from deflacionado as cur
    left join deflacionado as prev_1a
        on cur.codigo_ibge_municipio = prev_1a.codigo_ibge_municipio
        and prev_1a.ano_referencia = cur.ano_referencia - 1
),

final as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        ano_mes_base_deflator,
        num_unidades_locais,
        num_empresas_atuantes,
        pessoal_ocupado_total,
        pessoal_ocupado_assalariado,
        pessoal_assalariado_medio,
        massa_salarial_nominal_mil_brl,
        massa_salarial_real_mil_brl,
        salario_medio_sm,
        salario_medio_nominal_brl,
        salario_medio_real_brl,
        taxa_assalariamento_formal,
        case
            when empresas_lag_1a is not null and empresas_lag_1a > 0
                then ((cast(num_empresas_atuantes as double) / empresas_lag_1a) - 1.0) * 100.0
            else cast(null as double)
        end as crescimento_empresas_yoy_pct,
        case
            when pessoal_lag_1a is not null and pessoal_lag_1a > 0
                then ((cast(pessoal_ocupado_total as double) / pessoal_lag_1a) - 1.0) * 100.0
            else cast(null as double)
        end as crescimento_emprego_yoy_pct
    from com_yoy
)

select *
from final
