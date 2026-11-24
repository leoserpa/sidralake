with source as (
    select *
    from {{ source('bronze_ibge', 'pnad_rendimento_uf') }}
),

cleaned as (
    select
        cast(localidade_id as integer) as codigo_uf,
        trim(periodo_id) as ano_trimestre,
        cast(ano_referencia as integer) as ano_referencia,
        cast(right(trim(periodo_id), 2) as integer) as trimestre_referencia,
        make_date(
            cast(ano_referencia as integer),
            ((cast(right(trim(periodo_id), 2) as integer) - 1) * 3) + 1,
            1
        ) as data_referencia,
        case
            when categoria_1_id = '6794' then 'TOTAL'
            when categoria_1_id = '4' then 'HOMENS'
            when categoria_1_id = '5' then 'MULHERES'
            else 'OUTRO'
        end as sexo_grupo,
        cast(variavel_id as integer) as variavel_id,
        {{ parse_ibge_value('valor_bruto') }} as valor_numerico,
        {{ parse_ibge_status('valor_bruto') }} as status_valor_ibge,
        _ingested_at_utc
    from source
    where nivel_territorial = 'N3'
        and classificacao_1_id = '2'
    qualify row_number() over (
        partition by localidade_id, periodo_id, categoria_1_id, variavel_id
        order by _ingested_at_utc desc
    ) = 1
)

select *
from cleaned
