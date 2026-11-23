with pib_pivoted as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        max(case when variavel_id = 37 then valor_numerico end) as pib_nominal_mil_brl,
        max(case when variavel_id = 543 then valor_numerico end) as impostos_liquidos_mil_brl,
        max(case when variavel_id = 498 then valor_numerico end) as vab_total_mil_brl,
        max(case when variavel_id = 513 then valor_numerico end) as vab_agropecuaria_mil_brl,
        max(case when variavel_id = 517 then valor_numerico end) as vab_industria_mil_brl,
        max(case when variavel_id = 6575 then valor_numerico end) as vab_servicos_privados_mil_brl,
        max(case when variavel_id = 525 then valor_numerico end) as vab_adm_publica_mil_brl
    from {{ ref('stg_ibge__pib_municipal') }}
    group by 1, 2
),

deflacionado as (
    select
        p.codigo_ibge_municipio,
        p.ano_referencia,
        d.ano_mes_base_deflator,
        d.fator_deflator_anual,
        p.pib_nominal_mil_brl,
        p.pib_nominal_mil_brl * d.fator_deflator_anual as pib_real_mil_brl,
        p.impostos_liquidos_mil_brl,
        p.vab_total_mil_brl,
        p.vab_agropecuaria_mil_brl,
        p.vab_industria_mil_brl,
        p.vab_servicos_privados_mil_brl,
        p.vab_adm_publica_mil_brl,
        case
            when p.vab_total_mil_brl > 0 and p.vab_agropecuaria_mil_brl is not null
                then greatest(p.vab_agropecuaria_mil_brl, 0.0) / p.vab_total_mil_brl
            else cast(null as double)
        end as share_vab_agropecuaria,
        case
            when p.vab_total_mil_brl > 0 and p.vab_industria_mil_brl is not null
                then greatest(p.vab_industria_mil_brl, 0.0) / p.vab_total_mil_brl
            else cast(null as double)
        end as share_vab_industria,
        case
            when p.vab_total_mil_brl > 0 and p.vab_servicos_privados_mil_brl is not null
                then greatest(p.vab_servicos_privados_mil_brl, 0.0) / p.vab_total_mil_brl
            else cast(null as double)
        end as share_vab_servicos_privados,
        case
            when p.vab_total_mil_brl > 0 and p.vab_adm_publica_mil_brl is not null
                then greatest(p.vab_adm_publica_mil_brl, 0.0) / p.vab_total_mil_brl
            else cast(null as double)
        end as share_vab_adm_publica,
        case
            when p.vab_agropecuaria_mil_brl is not null
                and p.vab_industria_mil_brl is not null
                and p.vab_servicos_privados_mil_brl is not null
                and p.vab_adm_publica_mil_brl is not null
                then greatest(p.vab_agropecuaria_mil_brl, 0.0)
                    + greatest(p.vab_industria_mil_brl, 0.0)
                    + greatest(p.vab_servicos_privados_mil_brl, 0.0)
                    + greatest(p.vab_adm_publica_mil_brl, 0.0)
            else cast(null as double)
        end as vab_setores_positivos_mil_brl
    from pib_pivoted as p
    left join {{ ref('int_ipca_deflator_anual') }} as d
        on p.ano_referencia = d.ano_referencia
    where p.pib_nominal_mil_brl is not null
),

enriquecido as (
    select
        cur.*,
        case
            when cur.vab_setores_positivos_mil_brl is not null
                and cur.vab_setores_positivos_mil_brl > 0
                then least(
                    1.0,
                    power(greatest(cur.vab_agropecuaria_mil_brl, 0.0) / cur.vab_setores_positivos_mil_brl, 2)
                    + power(greatest(cur.vab_industria_mil_brl, 0.0) / cur.vab_setores_positivos_mil_brl, 2)
                    + power(greatest(cur.vab_servicos_privados_mil_brl, 0.0) / cur.vab_setores_positivos_mil_brl, 2)
                    + power(greatest(cur.vab_adm_publica_mil_brl, 0.0) / cur.vab_setores_positivos_mil_brl, 2)
                )
            else cast(null as double)
        end as hhi_setorial,
        prev_1a.pib_real_mil_brl as pib_real_lag_1a,
        prev_3a.pib_real_mil_brl as pib_real_lag_3a
    from deflacionado as cur
    left join deflacionado as prev_1a
        on cur.codigo_ibge_municipio = prev_1a.codigo_ibge_municipio
        and prev_1a.ano_referencia = cur.ano_referencia - 1
    left join deflacionado as prev_3a
        on cur.codigo_ibge_municipio = prev_3a.codigo_ibge_municipio
        and prev_3a.ano_referencia = cur.ano_referencia - 3
),

final as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        ano_mes_base_deflator,
        fator_deflator_anual,
        pib_nominal_mil_brl,
        pib_real_mil_brl,
        impostos_liquidos_mil_brl,
        vab_total_mil_brl,
        vab_agropecuaria_mil_brl,
        vab_industria_mil_brl,
        vab_servicos_privados_mil_brl,
        vab_adm_publica_mil_brl,
        share_vab_agropecuaria,
        share_vab_industria,
        share_vab_servicos_privados,
        share_vab_adm_publica,
        hhi_setorial,
        case
            when hhi_setorial is not null then greatest(0.0, least(1.0, 1.0 - hhi_setorial))
            else cast(null as double)
        end as indice_diversificacao_setorial,
        case
            when pib_real_lag_1a is not null and pib_real_lag_1a > 0 and pib_real_mil_brl is not null
                then ((pib_real_mil_brl / pib_real_lag_1a) - 1.0) * 100.0
            else cast(null as double)
        end as crescimento_pib_real_yoy_pct,
        case
            when pib_real_lag_3a is not null and pib_real_lag_3a > 0 and pib_real_mil_brl > 0
                then (power(pib_real_mil_brl / pib_real_lag_3a, 1.0 / 3.0) - 1.0) * 100.0
            else cast(null as double)
        end as cagr_pib_real_3a_pct
    from enriquecido
)

select *
from final
