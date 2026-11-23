with source as (
    select *
    from {{ source('bronze_ibge', 'localidades') }}
),

deduplicated as (
    select
        cast(municipio_id as integer) as codigo_ibge_municipio,
        trim(municipio_nome) as nome_municipio,
        cast(uf_id as integer) as codigo_uf,
        upper(trim(uf_sigla)) as sigla_uf,
        trim(uf_nome) as nome_uf,
        cast(regiao_id as integer) as codigo_regiao,
        upper(trim(regiao_sigla)) as sigla_regiao,
        trim(regiao_nome) as nome_regiao,
        cast(regiao_imediata_id as integer) as codigo_regiao_imediata,
        trim(regiao_imediata_nome) as nome_regiao_imediata,
        cast(regiao_intermediaria_id as integer) as codigo_regiao_intermediaria,
        trim(regiao_intermediaria_nome) as nome_regiao_intermediaria,
        cast(microrregiao_id as integer) as codigo_microrregiao,
        trim(microrregiao_nome) as nome_microrregiao,
        cast(mesorregiao_id as integer) as codigo_mesorregiao,
        trim(mesorregiao_nome) as nome_mesorregiao,
        _ingested_at_utc,
        _payload_hash
    from source
    qualify row_number() over (
        partition by municipio_id
        order by _ingested_at_utc desc
    ) = 1
)

select *
from deduplicated
