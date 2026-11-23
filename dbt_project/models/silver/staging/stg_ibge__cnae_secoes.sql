with source as (
    select *
    from {{ source('bronze_ibge', 'cnae_secoes') }}
),

deduplicated as (
    select
        upper(trim(secao_codigo)) as codigo_secao,
        trim(secao_descricao) as descricao_secao,
        cast(categoria_sidra_12762_id as integer) as categoria_sidra_12762_id,
        coalesce(trim(observacoes), '') as observacoes,
        _ingested_at_utc,
        _payload_hash
    from source
    qualify row_number() over (
        partition by upper(trim(secao_codigo))
        order by _ingested_at_utc desc
    ) = 1
)

select *
from deduplicated
