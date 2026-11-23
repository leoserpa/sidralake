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

cnae as (
    select
        sk_cnae_secao,
        codigo_secao,
        descricao_secao
    from {{ ref('dim_cnae') }}
    where is_current
),

base as (
    select
        f.codigo_uf,
        u.sigla_uf,
        u.nome_uf,
        u.sigla_regiao,
        u.nome_regiao,
        f.codigo_secao_cnae,
        c.descricao_secao as descricao_secao_cnae,
        f.ano_referencia,
        f.num_empresas,
        f.pessoal_ocupado_total,
        f.pessoal_ocupado_assalariado,
        f.massa_salarial_real_mil_brl,
        f.has_sigilo_estatistico
    from {{ ref('fct_cempre_setorial_uf') }} as f
    inner join ufs as u
        on f.codigo_uf = u.codigo_uf
    inner join cnae as c
        on f.codigo_secao_cnae = c.codigo_secao
),

totais as (
    select
        b.*,
        prev_1a.pessoal_ocupado_total as emprego_lag_1a,
        sum(b.pessoal_ocupado_total) over (
            partition by b.ano_referencia, b.codigo_uf
        ) as emprego_total_uf,
        bool_and(b.pessoal_ocupado_total is not null) over (
            partition by b.ano_referencia, b.codigo_uf
        ) as emprego_uf_completo,
        sum(b.pessoal_ocupado_total) over (
            partition by b.ano_referencia, b.codigo_secao_cnae
        ) as emprego_total_setor_br,
        bool_and(b.pessoal_ocupado_total is not null) over (
            partition by b.ano_referencia, b.codigo_secao_cnae
        ) as emprego_setor_br_completo,
        sum(b.pessoal_ocupado_total) over (
            partition by b.ano_referencia
        ) as emprego_total_br,
        bool_and(b.pessoal_ocupado_total is not null) over (
            partition by b.ano_referencia
        ) as emprego_br_completo,
        sum(b.massa_salarial_real_mil_brl) over (
            partition by b.ano_referencia, b.codigo_uf
        ) as massa_total_uf,
        bool_and(b.massa_salarial_real_mil_brl is not null) over (
            partition by b.ano_referencia, b.codigo_uf
        ) as massa_uf_completo,
        sum(b.massa_salarial_real_mil_brl) over (
            partition by b.ano_referencia, b.codigo_secao_cnae
        ) as massa_total_setor_br,
        bool_and(b.massa_salarial_real_mil_brl is not null) over (
            partition by b.ano_referencia, b.codigo_secao_cnae
        ) as massa_setor_br_completo,
        sum(b.massa_salarial_real_mil_brl) over (
            partition by b.ano_referencia
        ) as massa_total_br,
        bool_and(b.massa_salarial_real_mil_brl is not null) over (
            partition by b.ano_referencia
        ) as massa_br_completo
    from base as b
    left join base as prev_1a
        on b.codigo_uf = prev_1a.codigo_uf
        and b.codigo_secao_cnae = prev_1a.codigo_secao_cnae
        and prev_1a.ano_referencia = b.ano_referencia - 1
),

calculado as (
    select
        *,
        case
            when pessoal_ocupado_total is not null
                and emprego_uf_completo
                and emprego_setor_br_completo
                and emprego_br_completo
                and emprego_total_uf > 0
                and emprego_total_setor_br > 0
                and emprego_total_br > 0
                then (cast(pessoal_ocupado_total as double) / emprego_total_uf)
                    / nullif(cast(emprego_total_setor_br as double) / emprego_total_br, 0.0)
            else cast(null as double)
        end as quociente_locacional_emprego,
        case
            when massa_salarial_real_mil_brl is not null
                and massa_uf_completo
                and massa_setor_br_completo
                and massa_br_completo
                and massa_total_uf > 0
                and massa_total_setor_br > 0
                and massa_total_br > 0
                then (massa_salarial_real_mil_brl / massa_total_uf)
                    / nullif(massa_total_setor_br / massa_total_br, 0.0)
            else cast(null as double)
        end as quociente_locacional_massa_salarial,
        case
            when pessoal_ocupado_total is not null
                and emprego_setor_br_completo
                and emprego_total_setor_br > 0
                then (cast(pessoal_ocupado_total as double) / emprego_total_setor_br) * 100.0
            else cast(null as double)
        end as market_share_uf_no_setor_pct,
        case
            when emprego_lag_1a is not null and emprego_lag_1a > 0 and pessoal_ocupado_total is not null
                then ((cast(pessoal_ocupado_total as double) / emprego_lag_1a) - 1.0) * 100.0
            else cast(null as double)
        end as crescimento_emprego_setor_yoy_pct
    from totais
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_uf', 'codigo_secao_cnae', 'ano_referencia']) }} as sk_cluster_setorial,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(nome_regiao as varchar) as nome_regiao,
        cast(codigo_secao_cnae as varchar) as codigo_secao_cnae,
        cast(descricao_secao_cnae as varchar) as descricao_secao_cnae,
        cast(ano_referencia as integer) as ano_referencia,
        cast(num_empresas as integer) as num_empresas,
        cast(pessoal_ocupado_total as integer) as pessoal_ocupado_total,
        cast(pessoal_ocupado_assalariado as integer) as pessoal_ocupado_assalariado,
        cast(massa_salarial_real_mil_brl as double) as massa_salarial_real_mil_brl,
        cast(has_sigilo_estatistico as boolean) as has_sigilo_estatistico,
        cast(round(quociente_locacional_emprego, 4) as double) as quociente_locacional_emprego,
        cast(round(quociente_locacional_massa_salarial, 4) as double) as quociente_locacional_massa_salarial,
        cast(round(market_share_uf_no_setor_pct, 4) as double) as market_share_uf_no_setor_pct,
        cast(round(crescimento_emprego_setor_yoy_pct, 2) as double) as crescimento_emprego_setor_yoy_pct,
        cast(
            case
                when quociente_locacional_emprego is null then 'SIGILO_OU_INDISPONIVEL'
                when quociente_locacional_emprego >= 1.50 then 'CLUSTER_DOMINANTE'
                when quociente_locacional_emprego >= 1.25 then 'CLUSTER_ESPECIALIZADO'
                when quociente_locacional_emprego >= 0.85 then 'EQUILIBRADO_MEDIA_NACIONAL'
                else 'SUB_REPRESENTADO'
            end as varchar
        ) as perfil_especializacao
    from calculado
)

select *
from final
