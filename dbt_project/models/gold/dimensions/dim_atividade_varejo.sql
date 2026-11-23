with atividades as (
    select distinct
        codigo_atividade_pmc,
        nome_atividade_pmc
    from {{ ref('stg_ibge__pmc_varejo_uf') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['codigo_atividade_pmc']) }} as sk_atividade_varejo,
        cast(codigo_atividade_pmc as integer) as codigo_atividade_pmc,
        cast(nome_atividade_pmc as varchar) as nome_atividade_pmc,
        cast(
            case
                when codigo_atividade_pmc in (90672, 103154, 56741) then 'ALIMENTACAO_ATACAREJO'
                when codigo_atividade_pmc in (2759, 31555, 31556, 103157, 103158) then 'BENS_DURAVEIS_LAR'
                when codigo_atividade_pmc in (103159, 2762) then 'AUTOMOTIVO_CONSTRUCAO'
                when codigo_atividade_pmc = 90671 then 'COMBUSTIVEIS'
                else 'FARMACIA_VESTUARIO_CONVENIENCIA'
            end as varchar
        ) as grupo_consumo
    from atividades
)

select *
from final
