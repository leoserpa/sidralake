with source as (
    select *
    from {{ source('bronze_ibge', 'cempre_setorial_uf') }}
),

cleaned as (
    select
        cast(localidade_id as integer) as codigo_uf,
        cast(ano_referencia as integer) as ano_referencia,
        cast(categoria_1_id as integer) as categoria_sidra_cnae_id,
        upper(left(trim(categoria_1_nome), 1)) as codigo_secao_cnae,
        trim(categoria_1_nome) as categoria_cnae_nome,
        cast(variavel_id as integer) as variavel_id,
        {{ parse_ibge_value('valor_bruto') }} as valor_numerico,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N3'
        and classificacao_1_id = '12762'
    qualify row_number() over (
        partition by localidade_id, ano_referencia, categoria_1_id, variavel_id
        order by _ingested_at_utc desc
    ) = 1
)

select *
from cleaned
