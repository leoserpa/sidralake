with source as (
    select *
    from {{ source('bronze_ibge', 'estimativa_populacao') }}
),

cleaned as (
    select
        cast(localidade_id as integer) as codigo_ibge_municipio,
        cast(ano_referencia as integer) as ano_referencia,
        cast(round({{ parse_ibge_value('valor_bruto') }}) as bigint) as populacao_estimada,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N6'
        and cast(variavel_id as integer) = 9324
    qualify row_number() over (
        partition by localidade_id, ano_referencia
        order by _ingested_at_utc desc
    ) = 1
)

select *
from cleaned
