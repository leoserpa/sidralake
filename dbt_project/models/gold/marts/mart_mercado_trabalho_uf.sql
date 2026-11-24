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

desoc as (
    select
        codigo_uf,
        ano_trimestre,
        ano_referencia,
        trimestre_referencia,
        data_referencia,
        max(case when variavel_id = 4099 then valor_numerico end) as taxa_desocupacao_pct,
        max(case when variavel_id = 4114 then valor_numerico end) as taxa_desocupacao_subocupacao_pct,
        max(case when variavel_id = 4116 then valor_numerico end) as taxa_desocupacao_forca_potencial_pct,
        max(case when variavel_id = 4118 then valor_numerico end) as taxa_subutilizacao_composta_pct
    from {{ ref('stg_ibge__pnad_desocupacao_uf') }}
    group by 1, 2, 3, 4, 5
),

renda as (
    select
        codigo_uf,
        ano_trimestre,
        ano_referencia,
        trimestre_referencia,
        data_referencia,
        max(case when sexo_grupo = 'TOTAL' and variavel_id = 5933 then valor_numerico end)
            as rendimento_medio_real_brl,
        max(case when sexo_grupo = 'HOMENS' and variavel_id = 5933 then valor_numerico end)
            as rendimento_homens_real_brl,
        max(case when sexo_grupo = 'MULHERES' and variavel_id = 5933 then valor_numerico end)
            as rendimento_mulheres_real_brl
    from {{ ref('stg_ibge__pnad_rendimento_uf') }}
    group by 1, 2, 3, 4, 5
),

merged as (
    select
        coalesce(d.codigo_uf, r.codigo_uf) as codigo_uf,
        coalesce(d.ano_trimestre, r.ano_trimestre) as ano_trimestre,
        coalesce(d.ano_referencia, r.ano_referencia) as ano_referencia,
        coalesce(d.trimestre_referencia, r.trimestre_referencia) as trimestre_referencia,
        coalesce(d.data_referencia, r.data_referencia) as data_referencia,
        d.taxa_desocupacao_pct,
        d.taxa_desocupacao_subocupacao_pct,
        d.taxa_desocupacao_forca_potencial_pct,
        d.taxa_subutilizacao_composta_pct,
        r.rendimento_medio_real_brl,
        r.rendimento_homens_real_brl,
        r.rendimento_mulheres_real_brl
    from desoc as d
    full outer join renda as r
        on d.codigo_uf = r.codigo_uf
        and d.ano_trimestre = r.ano_trimestre
),

enriched as (
    select
        m.*,
        u.sigla_uf,
        u.nome_uf,
        u.sigla_regiao,
        u.nome_regiao,
        m.taxa_desocupacao_pct - lag(m.taxa_desocupacao_pct, 4) over (
            partition by m.codigo_uf
            order by m.data_referencia
        ) as var_yoy_desocupacao_pp,
        case
            when lag(m.rendimento_medio_real_brl, 4) over (
                partition by m.codigo_uf
                order by m.data_referencia
            ) > 0
                then (
                    (
                        m.rendimento_medio_real_brl
                        / lag(m.rendimento_medio_real_brl, 4) over (
                            partition by m.codigo_uf
                            order by m.data_referencia
                        )
                    ) - 1.0
                ) * 100.0
            else cast(null as double)
        end as var_yoy_rendimento_real_pct,
        case
            when m.rendimento_homens_real_brl > 0 and m.rendimento_mulheres_real_brl is not null
                then ((m.rendimento_mulheres_real_brl - m.rendimento_homens_real_brl) / m.rendimento_homens_real_brl)
                    * 100.0
            else cast(null as double)
        end as hiato_salarial_genero_pct,
        m.ano_trimestre = max(m.ano_trimestre) over () as is_ultimo_trimestre
    from merged as m
    inner join ufs as u
        on m.codigo_uf = u.codigo_uf
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_uf', 'ano_trimestre']) }} as sk_mercado_trabalho,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(nome_regiao as varchar) as nome_regiao,
        cast(ano_trimestre as varchar) as ano_trimestre,
        cast(cast(trimestre_referencia as varchar) || 'T/' || cast(ano_referencia as varchar) as varchar)
            as label_trimestre,
        cast(ano_referencia as integer) as ano_referencia,
        cast(trimestre_referencia as integer) as trimestre_referencia,
        cast(data_referencia as date) as data_referencia,
        cast(is_ultimo_trimestre as boolean) as is_ultimo_trimestre,
        cast(taxa_desocupacao_pct as double) as taxa_desocupacao_pct,
        cast(taxa_desocupacao_subocupacao_pct as double) as taxa_desocupacao_subocupacao_pct,
        cast(taxa_desocupacao_forca_potencial_pct as double) as taxa_desocupacao_forca_potencial_pct,
        cast(taxa_subutilizacao_composta_pct as double) as taxa_subutilizacao_composta_pct,
        cast(round(var_yoy_desocupacao_pp, 2) as double) as var_yoy_desocupacao_pp,
        cast(rendimento_medio_real_brl as double) as rendimento_medio_real_brl,
        cast(rendimento_homens_real_brl as double) as rendimento_homens_real_brl,
        cast(rendimento_mulheres_real_brl as double) as rendimento_mulheres_real_brl,
        cast(round(var_yoy_rendimento_real_pct, 2) as double) as var_yoy_rendimento_real_pct,
        cast(round(hiato_salarial_genero_pct, 2) as double) as hiato_salarial_genero_pct
    from enriched
)

select *
from final
