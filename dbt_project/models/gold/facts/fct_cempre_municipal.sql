with cempre as (
    select *
    from {{ ref('int_cempre_municipal_deflacionado') }}
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
        {{ dbt_utils.generate_surrogate_key(['c.codigo_ibge_municipio', 'c.ano_referencia']) }} as sk_cempre_municipal,
        cast(g.sk_municipio as varchar) as sk_municipio,
        cast(c.codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(c.ano_referencia as integer) as ano_referencia,
        cast(c.ano_mes_base_deflator as varchar) as ano_mes_base_deflator,
        cast(c.num_unidades_locais as integer) as num_unidades_locais,
        cast(c.num_empresas_atuantes as integer) as num_empresas_atuantes,
        cast(c.pessoal_ocupado_total as integer) as pessoal_ocupado_total,
        cast(c.pessoal_ocupado_assalariado as integer) as pessoal_ocupado_assalariado,
        cast(c.pessoal_assalariado_medio as integer) as pessoal_assalariado_medio,
        cast(c.massa_salarial_nominal_mil_brl as double) as massa_salarial_nominal_mil_brl,
        cast(c.massa_salarial_real_mil_brl as double) as massa_salarial_real_mil_brl,
        cast(c.salario_medio_sm as double) as salario_medio_sm,
        cast(c.salario_medio_nominal_brl as double) as salario_medio_nominal_brl,
        cast(c.salario_medio_real_brl as double) as salario_medio_real_brl,
        cast(c.taxa_assalariamento_formal as double) as taxa_assalariamento_formal,
        cast(c.crescimento_empresas_yoy_pct as double) as crescimento_empresas_yoy_pct,
        cast(c.crescimento_emprego_yoy_pct as double) as crescimento_emprego_yoy_pct
    from cempre as c
    inner join geo as g
        on c.codigo_ibge_municipio = g.codigo_ibge_municipio
)

select *
from final
