with geo as (
    select
        codigo_ibge_municipio,
        nome_municipio,
        sigla_uf,
        nome_regiao,
        codigo_regiao_imediata,
        nome_regiao_imediata
    from {{ ref('dim_geografia') }}
    where is_current
),

pop_ranked as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        populacao_residente,
        area_km2,
        densidade_demografica,
        row_number() over (
            partition by codigo_ibge_municipio
            order by ano_referencia desc
        ) as rn_ult
    from {{ ref('fct_populacao_municipal') }}
),

pop_ult as (
    select
        codigo_ibge_municipio,
        ano_referencia as ano_populacao_atual,
        populacao_residente as populacao_atual,
        area_km2,
        densidade_demografica
    from pop_ranked
    where rn_ult = 1
),

pop_censo_2022 as (
    select
        codigo_ibge_municipio,
        populacao_residente as populacao_censo_2022
    from {{ ref('fct_populacao_municipal') }}
    where ano_referencia = 2022
),

mercado_ult as (
    select
        codigo_ibge_municipio,
        pib_real_mil_brl,
        massa_salarial_real_mil_brl,
        ims_score_0_100
    from {{ ref('mart_inteligencia_mercado_municipal') }}
    where is_ultimo_ano_completo
),

final as (
    select
        cast(g.codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(g.nome_municipio as varchar) as nome_municipio,
        cast(g.sigla_uf as varchar) as sigla_uf,
        cast(g.nome_regiao as varchar) as nome_regiao,
        cast(g.codigo_regiao_imediata as integer) as codigo_regiao_imediata,
        cast(g.nome_regiao_imediata as varchar) as nome_regiao_imediata,
        cast(u.ano_populacao_atual as integer) as ano_populacao_atual,
        cast(u.populacao_atual as bigint) as populacao_atual,
        cast(c.populacao_censo_2022 as bigint) as populacao_censo_2022,
        cast(
            case
                when c.populacao_censo_2022 is not null and u.ano_populacao_atual > 2022
                    then u.populacao_atual - c.populacao_censo_2022
            end as bigint
        ) as saldo_populacional_desde_2022,
        cast(
            case
                when c.populacao_censo_2022 > 0 and u.ano_populacao_atual > 2022
                    then round(
                        (u.populacao_atual - c.populacao_censo_2022) * 100.0
                        / c.populacao_censo_2022,
                        2
                    )
            end as double
        ) as crescimento_populacional_desde_2022_pct,
        cast(
            row_number() over (
                partition by g.sigla_uf
                order by coalesce(u.populacao_atual, 0) desc, g.nome_municipio asc
            ) as integer
        ) as rank_populacao_uf,
        cast(u.area_km2 as double) as area_km2,
        cast(u.densidade_demografica as double) as densidade_demografica,
        cast(m.pib_real_mil_brl as double) as pib_real_mil_brl,
        cast(m.massa_salarial_real_mil_brl as double) as massa_salarial_real_mil_brl,
        cast(m.ims_score_0_100 as double) as ims_score_0_100
    from geo as g
    left join pop_ult as u
        on g.codigo_ibge_municipio = u.codigo_ibge_municipio
    left join pop_censo_2022 as c
        on g.codigo_ibge_municipio = c.codigo_ibge_municipio
    left join mercado_ult as m
        on g.codigo_ibge_municipio = m.codigo_ibge_municipio
)

select *
from final
