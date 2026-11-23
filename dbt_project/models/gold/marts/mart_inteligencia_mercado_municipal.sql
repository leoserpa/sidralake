with geo as (
    select
        sk_municipio,
        codigo_ibge_municipio,
        nome_municipio,
        codigo_uf,
        sigla_uf,
        nome_uf,
        sigla_regiao,
        nome_regiao,
        nome_regiao_imediata,
        nome_regiao_intermediaria
    from {{ ref('dim_geografia') }}
    where is_current
),

anos_disponiveis as (
    select distinct
        codigo_ibge_municipio,
        ano_referencia
    from {{ ref('fct_pib_municipal') }}
    union
    select distinct
        codigo_ibge_municipio,
        ano_referencia
    from {{ ref('fct_cempre_municipal') }}
),

base as (
    select
        g.sk_municipio,
        a.codigo_ibge_municipio,
        a.ano_referencia,
        g.nome_municipio,
        g.codigo_uf,
        g.sigla_uf,
        g.nome_uf,
        g.sigla_regiao,
        g.nome_regiao,
        g.nome_regiao_imediata,
        g.nome_regiao_intermediaria,

        -- Demografia
        pop.populacao_residente,
        pop.area_km2,
        pop.densidade_demografica,
        pop.origem_dado as origem_populacao,
        coalesce(pop.is_interpolado, false) as is_populacao_interpolada,

        -- PIB & Estrutura Produtiva
        pib.ano_mes_base_deflator,
        pib.pib_nominal_mil_brl,
        pib.pib_real_mil_brl,
        case
            when pop.populacao_residente > 0 and pib.pib_real_mil_brl is not null
                then (pib.pib_real_mil_brl * 1000.0) / pop.populacao_residente
            else cast(null as double)
        end as pib_per_capita_real_brl,
        pib.share_vab_agropecuaria,
        pib.share_vab_industria,
        pib.share_vab_servicos_privados,
        pib.share_vab_adm_publica,
        pib.hhi_setorial,
        pib.indice_diversificacao_setorial,
        pib.crescimento_pib_real_yoy_pct,
        pib.cagr_pib_real_3a_pct,

        -- Tecido Empresarial (CEMPRE)
        emp.num_unidades_locais,
        emp.num_empresas_atuantes,
        emp.pessoal_ocupado_total,
        emp.pessoal_ocupado_assalariado,
        emp.massa_salarial_real_mil_brl,
        emp.salario_medio_real_brl,
        emp.salario_medio_sm,
        emp.taxa_assalariamento_formal,
        emp.crescimento_empresas_yoy_pct,
        emp.crescimento_emprego_yoy_pct,
        case
            when pop.populacao_residente > 0 and emp.num_empresas_atuantes is not null
                then (cast(emp.num_empresas_atuantes as double) / pop.populacao_residente) * 1000.0
            else cast(null as double)
        end as empresas_por_1000_hab,

        -- Transformacoes logaritmicas para normalizacao de tamanho de mercado
        case
            when pib.pib_real_mil_brl is not null then ln(1.0 + greatest(pib.pib_real_mil_brl, 0.0))
            else cast(null as double)
        end as ln_pib_real,
        case
            when pop.populacao_residente is not null then ln(1.0 + greatest(cast(pop.populacao_residente as double), 0.0))
            else cast(null as double)
        end as ln_populacao,
        case
            when emp.massa_salarial_real_mil_brl is not null
                then ln(1.0 + greatest(emp.massa_salarial_real_mil_brl, 0.0))
            else cast(null as double)
        end as ln_massa_salarial_real,
        case
            when pop.populacao_residente > 0 and pib.pib_real_mil_brl is not null
                then ln(1.0 + greatest((pib.pib_real_mil_brl * 1000.0) / pop.populacao_residente, 0.0))
            else cast(null as double)
        end as ln_pib_per_capita_real,
        coalesce(pib.cagr_pib_real_3a_pct, pib.crescimento_pib_real_yoy_pct) as dinamismo_pib_pct
    from anos_disponiveis as a
    inner join geo as g
        on a.codigo_ibge_municipio = g.codigo_ibge_municipio
    left join {{ ref('fct_populacao_municipal') }} as pop
        on a.codigo_ibge_municipio = pop.codigo_ibge_municipio
        and a.ano_referencia = pop.ano_referencia
    left join {{ ref('fct_pib_municipal') }} as pib
        on a.codigo_ibge_municipio = pib.codigo_ibge_municipio
        and a.ano_referencia = pib.ano_referencia
    left join {{ ref('fct_cempre_municipal') }} as emp
        on a.codigo_ibge_municipio = emp.codigo_ibge_municipio
        and a.ano_referencia = emp.ano_referencia
),

bounds as (
    select
        ano_referencia,
        quantile_cont(ln_pib_real, 0.01) as p01_ln_pib,
        quantile_cont(ln_pib_real, 0.99) as p99_ln_pib,
        quantile_cont(ln_populacao, 0.01) as p01_ln_pop,
        quantile_cont(ln_populacao, 0.99) as p99_ln_pop,
        quantile_cont(ln_massa_salarial_real, 0.01) as p01_ln_massa,
        quantile_cont(ln_massa_salarial_real, 0.99) as p99_ln_massa,
        quantile_cont(ln_pib_per_capita_real, 0.01) as p01_ln_pib_pc,
        quantile_cont(ln_pib_per_capita_real, 0.99) as p99_ln_pib_pc,
        quantile_cont(salario_medio_real_brl, 0.01) as p01_sal,
        quantile_cont(salario_medio_real_brl, 0.99) as p99_sal,
        quantile_cont(dinamismo_pib_pct, 0.05) as p05_din_pib,
        quantile_cont(dinamismo_pib_pct, 0.95) as p95_din_pib,
        quantile_cont(crescimento_empresas_yoy_pct, 0.05) as p05_cresc_emp,
        quantile_cont(crescimento_empresas_yoy_pct, 0.95) as p95_cresc_emp,
        quantile_cont(crescimento_emprego_yoy_pct, 0.05) as p05_cresc_trab,
        quantile_cont(crescimento_emprego_yoy_pct, 0.95) as p95_cresc_trab,
        quantile_cont(empresas_por_1000_hab, 0.01) as p01_dens_emp,
        quantile_cont(empresas_por_1000_hab, 0.99) as p99_dens_emp,
        quantile_cont(taxa_assalariamento_formal, 0.01) as p01_formal,
        quantile_cont(taxa_assalariamento_formal, 0.99) as p99_formal,
        quantile_cont(indice_diversificacao_setorial, 0.01) as p01_div,
        quantile_cont(indice_diversificacao_setorial, 0.99) as p99_div
    from base
    group by 1
),

normalized as (
    select
        b.*,
        {{ normalize_winsorized('b.ln_pib_real', 'q.p01_ln_pib', 'q.p99_ln_pib') }} as n_pib,
        {{ normalize_winsorized('b.ln_populacao', 'q.p01_ln_pop', 'q.p99_ln_pop') }} as n_pop,
        {{ normalize_winsorized('b.ln_massa_salarial_real', 'q.p01_ln_massa', 'q.p99_ln_massa') }} as n_massa,
        {{ normalize_winsorized('b.ln_pib_per_capita_real', 'q.p01_ln_pib_pc', 'q.p99_ln_pib_pc') }} as n_pib_pc,
        {{ normalize_winsorized('b.salario_medio_real_brl', 'q.p01_sal', 'q.p99_sal') }} as n_sal,
        {{ normalize_winsorized('b.dinamismo_pib_pct', 'q.p05_din_pib', 'q.p95_din_pib') }} as n_din_pib,
        {{ normalize_winsorized('b.crescimento_empresas_yoy_pct', 'q.p05_cresc_emp', 'q.p95_cresc_emp') }} as n_cresc_emp,
        {{ normalize_winsorized('b.crescimento_emprego_yoy_pct', 'q.p05_cresc_trab', 'q.p95_cresc_trab') }} as n_cresc_trab,
        {{ normalize_winsorized('b.empresas_por_1000_hab', 'q.p01_dens_emp', 'q.p99_dens_emp') }} as n_dens_emp,
        {{ normalize_winsorized('b.taxa_assalariamento_formal', 'q.p01_formal', 'q.p99_formal') }} as n_formal,
        {{ normalize_winsorized('b.indice_diversificacao_setorial', 'q.p01_div', 'q.p99_div') }} as n_div
    from base as b
    inner join bounds as q
        on b.ano_referencia = q.ano_referencia
),

pilares as (
    select
        *,
        (
            coalesce(n_pib, 0.0) + coalesce(n_pop, 0.0) + coalesce(n_massa, 0.0)
        ) / nullif(
            (case when n_pib is not null then 1 else 0 end)
            + (case when n_pop is not null then 1 else 0 end)
            + (case when n_massa is not null then 1 else 0 end),
            0
        ) as score_tamanho_mercado,
        (
            coalesce(n_pib_pc, 0.0) + coalesce(n_sal, 0.0)
        ) / nullif(
            (case when n_pib_pc is not null then 1 else 0 end)
            + (case when n_sal is not null then 1 else 0 end),
            0
        ) as score_poder_compra,
        (
            coalesce(n_din_pib, 0.0) + coalesce(n_cresc_emp, 0.0) + coalesce(n_cresc_trab, 0.0)
        ) / nullif(
            (case when n_din_pib is not null then 1 else 0 end)
            + (case when n_cresc_emp is not null then 1 else 0 end)
            + (case when n_cresc_trab is not null then 1 else 0 end),
            0
        ) as score_dinamismo,
        (
            coalesce(n_dens_emp, 0.0) + coalesce(n_formal, 0.0) + coalesce(n_div, 0.0)
        ) / nullif(
            (case when n_dens_emp is not null then 1 else 0 end)
            + (case when n_formal is not null then 1 else 0 end)
            + (case when n_div is not null then 1 else 0 end),
            0
        ) as score_maturidade_empresarial
    from normalized
),

scored as (
    select
        *,
        round(
            (
                coalesce(score_tamanho_mercado * {{ var('ims_weight_market_size') }}, 0.0)
                + coalesce(score_poder_compra * {{ var('ims_weight_purchasing_power') }}, 0.0)
                + coalesce(score_dinamismo * {{ var('ims_weight_dynamism') }}, 0.0)
                + coalesce(score_maturidade_empresarial * {{ var('ims_weight_business_maturity') }}, 0.0)
            ) / nullif(
                (case when score_tamanho_mercado is not null then {{ var('ims_weight_market_size') }} else 0.0 end)
                + (case when score_poder_compra is not null then {{ var('ims_weight_purchasing_power') }} else 0.0 end)
                + (case when score_dinamismo is not null then {{ var('ims_weight_dynamism') }} else 0.0 end)
                + (case when score_maturidade_empresarial is not null then {{ var('ims_weight_business_maturity') }} else 0.0 end),
                0.0
            ),
            2
        ) as ims_score_0_100
    from pilares
),

ultimo_ano_completo as (
    select
        max(ano_referencia) as max_ano_completo
    from scored
    where pib_real_mil_brl is not null
        and num_empresas_atuantes is not null
),

ranked as (
    select
        s.*,
        cast(
            row_number() over (
                partition by s.ano_referencia
                order by s.ims_score_0_100 desc nulls last, s.pib_real_mil_brl desc nulls last, s.codigo_ibge_municipio asc
            ) as integer
        ) as rank_nacional_ims,
        cast(
            row_number() over (
                partition by s.ano_referencia, s.codigo_uf
                order by s.ims_score_0_100 desc nulls last, s.pib_real_mil_brl desc nulls last, s.codigo_ibge_municipio asc
            ) as integer
        ) as rank_estadual_ims,
        cast(
            row_number() over (
                partition by s.ano_referencia, s.sigla_regiao
                order by s.ims_score_0_100 desc nulls last, s.pib_real_mil_brl desc nulls last, s.codigo_ibge_municipio asc
            ) as integer
        ) as rank_regional_ims,
        percent_rank() over (
            partition by s.ano_referencia
            order by s.ims_score_0_100 asc nulls first
        ) as percentil_nacional_ims,
        cast(s.ano_referencia = u.max_ano_completo as boolean) as is_ultimo_ano_completo
    from scored as s
    cross join ultimo_ano_completo as u
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_ibge_municipio', 'ano_referencia']) }} as sk_inteligencia_municipal,
        cast(sk_municipio as varchar) as sk_municipio,
        cast(codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(ano_referencia as integer) as ano_referencia,
        cast(is_ultimo_ano_completo as boolean) as is_ultimo_ano_completo,
        cast(nome_municipio as varchar) as nome_municipio,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(nome_regiao as varchar) as nome_regiao,
        cast(nome_regiao_imediata as varchar) as nome_regiao_imediata,
        cast(nome_regiao_intermediaria as varchar) as nome_regiao_intermediaria,
        cast(populacao_residente as bigint) as populacao_residente,
        cast(area_km2 as double) as area_km2,
        cast(densidade_demografica as double) as densidade_demografica,
        cast(origem_populacao as varchar) as origem_populacao,
        cast(is_populacao_interpolada as boolean) as is_populacao_interpolada,
        cast(ano_mes_base_deflator as varchar) as ano_mes_base_deflator,
        cast(pib_nominal_mil_brl as double) as pib_nominal_mil_brl,
        cast(pib_real_mil_brl as double) as pib_real_mil_brl,
        cast(pib_per_capita_real_brl as double) as pib_per_capita_real_brl,
        cast(share_vab_agropecuaria as double) as share_vab_agropecuaria,
        cast(share_vab_industria as double) as share_vab_industria,
        cast(share_vab_servicos_privados as double) as share_vab_servicos_privados,
        cast(share_vab_adm_publica as double) as share_vab_adm_publica,
        cast(hhi_setorial as double) as hhi_setorial,
        cast(indice_diversificacao_setorial as double) as indice_diversificacao_setorial,
        cast(crescimento_pib_real_yoy_pct as double) as crescimento_pib_real_yoy_pct,
        cast(cagr_pib_real_3a_pct as double) as cagr_pib_real_3a_pct,
        cast(num_unidades_locais as integer) as num_unidades_locais,
        cast(num_empresas_atuantes as integer) as num_empresas_atuantes,
        cast(pessoal_ocupado_total as integer) as pessoal_ocupado_total,
        cast(pessoal_ocupado_assalariado as integer) as pessoal_ocupado_assalariado,
        cast(massa_salarial_real_mil_brl as double) as massa_salarial_real_mil_brl,
        cast(salario_medio_real_brl as double) as salario_medio_real_brl,
        cast(salario_medio_sm as double) as salario_medio_sm,
        cast(taxa_assalariamento_formal as double) as taxa_assalariamento_formal,
        cast(empresas_por_1000_hab as double) as empresas_por_1000_hab,
        cast(crescimento_empresas_yoy_pct as double) as crescimento_empresas_yoy_pct,
        cast(crescimento_emprego_yoy_pct as double) as crescimento_emprego_yoy_pct,
        cast(round(score_tamanho_mercado, 2) as double) as score_tamanho_mercado,
        cast(round(score_poder_compra, 2) as double) as score_poder_compra,
        cast(round(score_dinamismo, 2) as double) as score_dinamismo,
        cast(round(score_maturidade_empresarial, 2) as double) as score_maturidade_empresarial,
        cast(ims_score_0_100 as double) as ims_score_0_100,
        cast(rank_nacional_ims as integer) as rank_nacional_ims,
        cast(rank_estadual_ims as integer) as rank_estadual_ims,
        cast(rank_regional_ims as integer) as rank_regional_ims,
        cast(
            case
                when ims_score_0_100 is null then 'SEM_CLASSIFICACAO'
                when percentil_nacional_ims >= 0.98 then 'Tier 1 - Polo Nacional'
                when percentil_nacional_ims >= 0.90 then 'Tier 2 - Expansao Prioritaria'
                when percentil_nacional_ims >= 0.65 then 'Tier 3 - Emergente'
                else 'Tier 4 - Local / Nicho'
            end as varchar
        ) as tier_mercado
    from ranked
)

select *
from final
