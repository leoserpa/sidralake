with source as (
    select *
    from {{ source('bronze_ibge', 'pmc_varejo_uf') }}
),

cleaned as (
    select
        cast(localidade_id as integer) as codigo_uf,
        trim(periodo_id) as ano_mes,
        cast(ano_referencia as integer) as ano_referencia,
        cast(right(trim(periodo_id), 2) as integer) as mes_referencia,
        make_date(
            cast(ano_referencia as integer),
            cast(right(trim(periodo_id), 2) as integer),
            1
        ) as data_referencia,
        cast(categoria_1_id as integer) as codigo_atividade_pmc,
        trim(categoria_1_nome) as nome_atividade_pmc,
        cast(categoria_2_id as integer) as codigo_tipo_indice,
        case
            when categoria_2_id = '56735' then 'RECEITA_NOMINAL'
            when categoria_2_id = '56736' then 'VOLUME_VENDAS'
            else 'OUTRO'
        end as tipo_indice,
        cast(variavel_id as integer) as variavel_id,
        {{ parse_ibge_value('valor_bruto') }} as valor_numerico,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N3'
        and classificacao_1_id = '85'
        and classificacao_2_id = '11046'
    qualify row_number() over (
        partition by localidade_id, periodo_id, categoria_1_id, categoria_2_id, variavel_id
        order by _ingested_at_utc desc
    ) = 1
)

select *
from cleaned
