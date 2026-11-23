with snap as (
    select *
    from {{ ref('snap_ibge_municipios') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_ibge_municipio', 'dbt_valid_from']) }} as sk_municipio,
        cast(codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(nome_municipio as varchar) as nome_municipio,
        cast(codigo_uf as integer) as codigo_uf,
        cast(sigla_uf as varchar) as sigla_uf,
        cast(nome_uf as varchar) as nome_uf,
        cast(codigo_regiao as integer) as codigo_regiao,
        cast(sigla_regiao as varchar) as sigla_regiao,
        cast(nome_regiao as varchar) as nome_regiao,
        cast(codigo_regiao_imediata as integer) as codigo_regiao_imediata,
        cast(nome_regiao_imediata as varchar) as nome_regiao_imediata,
        cast(codigo_regiao_intermediaria as integer) as codigo_regiao_intermediaria,
        cast(nome_regiao_intermediaria as varchar) as nome_regiao_intermediaria,
        cast(codigo_microrregiao as integer) as codigo_microrregiao,
        cast(nome_microrregiao as varchar) as nome_microrregiao,
        cast(codigo_mesorregiao as integer) as codigo_mesorregiao,
        cast(nome_mesorregiao as varchar) as nome_mesorregiao,
        cast(dbt_valid_from as timestamp) as valid_from,
        cast(dbt_valid_to as timestamp) as valid_to,
        cast(dbt_valid_to is null as boolean) as is_current
    from snap
)

select *
from final
