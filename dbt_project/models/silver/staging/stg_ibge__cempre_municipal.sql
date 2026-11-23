with source as (
    select *
    from {{ source('bronze_ibge', 'cempre_municipal') }}
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
)

select *
from cleaned
