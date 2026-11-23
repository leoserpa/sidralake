with snap as (
    select *
    from {{ ref('snap_ibge_cnae_secoes') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_secao', 'dbt_valid_from']) }} as sk_cnae_secao,
        cast(codigo_secao as varchar) as codigo_secao,
        cast(descricao_secao as varchar) as descricao_secao,
        cast(categoria_sidra_12762_id as integer) as categoria_sidra_12762_id,
        cast(dbt_valid_from as timestamp) as valid_from,
        cast(dbt_valid_to as timestamp) as valid_to,
        cast(dbt_valid_to is null as boolean) as is_current
    from snap
)

select *
from final
