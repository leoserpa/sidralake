with source as (
    select *
    from {{ source('bronze_ibge', 'ipca_mensal') }}
),

cleaned as (
    select
        trim(periodo_id) as ano_mes,
        cast(ano_referencia as integer) as ano_referencia,
        cast(right(trim(periodo_id), 2) as integer) as mes_referencia,
        make_date(
            cast(ano_referencia as integer),
            cast(right(trim(periodo_id), 2) as integer),
            1
        ) as data_referencia,
        cast(variavel_id as integer) as variavel_id,
        {{ parse_ibge_value('valor_bruto') }} as valor_numerico,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N1'
    qualify row_number() over (
        partition by periodo_id, variavel_id
        order by _ingested_at_utc desc
    ) = 1
),

pivoted as (
    select
        ano_mes,
        ano_referencia,
        mes_referencia,
        data_referencia,
        max(case when variavel_id = 2266 then valor_numerico end) as numero_indice_ipca,
        max(case when variavel_id = 63 then valor_numerico end) as variacao_mensal_pct,
        max(case when variavel_id = 2263 then valor_numerico end) as variacao_acum_3m_pct,
        max(case when variavel_id = 2264 then valor_numerico end) as variacao_acum_6m_pct,
        max(case when variavel_id = 69 then valor_numerico end) as variacao_acum_ano_pct,
        max(case when variavel_id = 2265 then valor_numerico end) as variacao_acum_12m_pct,
        max(_ingested_at_utc) as _ingested_at_utc
    from cleaned
    group by 1, 2, 3, 4
)

select *
from pivoted
