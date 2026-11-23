with pivoted as (
    select
        codigo_uf,
        ano_referencia,
        codigo_secao_cnae,
        cast(round(max(case when variavel_id = 2585 then valor_numerico end)) as integer) as num_empresas,
        cast(round(max(case when variavel_id = 707 then valor_numerico end)) as integer) as pessoal_ocupado_total,
        cast(round(max(case when variavel_id = 708 then valor_numerico end)) as integer) as pessoal_ocupado_assalariado,
        max(case when variavel_id = 662 then valor_numerico end) as massa_salarial_nominal_mil_brl,
        bool_or(status_valor_ibge = 'SIGILO_ESTATISTICO') as has_sigilo_estatistico
    from {{ ref('stg_ibge__cempre_setorial_uf') }}
    group by 1, 2, 3
),

cnae as (
    select
        sk_cnae_secao,
        codigo_secao
    from {{ ref('dim_cnae') }}
    where is_current
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['p.codigo_uf', 'p.codigo_secao_cnae', 'p.ano_referencia']) }} as sk_cempre_setorial_uf,
        cast(p.codigo_uf as integer) as codigo_uf,
        cast(c.sk_cnae_secao as varchar) as sk_cnae_secao,
        cast(p.codigo_secao_cnae as varchar) as codigo_secao_cnae,
        cast(p.ano_referencia as integer) as ano_referencia,
        cast(p.num_empresas as integer) as num_empresas,
        cast(p.pessoal_ocupado_total as integer) as pessoal_ocupado_total,
        cast(p.pessoal_ocupado_assalariado as integer) as pessoal_ocupado_assalariado,
        cast(p.massa_salarial_nominal_mil_brl as double) as massa_salarial_nominal_mil_brl,
        cast(
            p.massa_salarial_nominal_mil_brl * d.fator_deflator_anual as double
        ) as massa_salarial_real_mil_brl,
        cast(p.has_sigilo_estatistico as boolean) as has_sigilo_estatistico
    from pivoted as p
    inner join cnae as c
        on p.codigo_secao_cnae = c.codigo_secao
    left join {{ ref('int_ipca_deflator_anual') }} as d
        on p.ano_referencia = d.ano_referencia
)

select *
from final
