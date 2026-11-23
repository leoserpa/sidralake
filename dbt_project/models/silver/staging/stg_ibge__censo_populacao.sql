with source as (
    select *
    from {{ source('bronze_ibge', 'censo_populacao') }}
),

cleaned as (
    select
        cast(localidade_id as integer) as codigo_ibge_municipio,
        cast(ano_referencia as integer) as ano_referencia,
        cast(variavel_id as integer) as variavel_id,
        {{ parse_ibge_value('valor_bruto') }} as valor_numerico,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N6'
    qualify row_number() over (
        partition by localidade_id, ano_referencia, variavel_id
        order by _ingested_at_utc desc
    ) = 1
),

pivoted as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        cast(round(max(case when variavel_id = 93 then valor_numerico end)) as bigint) as populacao_residente,
        max(case when variavel_id = 6318 then valor_numerico end) as area_km2,
        max(case when variavel_id = 614 then valor_numerico end) as densidade_demografica,
        max(_ingested_at_utc) as _ingested_at_utc
    from cleaned
    group by 1, 2
)

select *
from pivoted
