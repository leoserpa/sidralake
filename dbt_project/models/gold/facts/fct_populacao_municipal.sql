with pop as (
    select *
    from {{ ref('int_populacao_municipal_unificada') }}
),

geo as (
    select
        sk_municipio,
        codigo_ibge_municipio
    from {{ ref('dim_geografia') }}
    where is_current
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['p.codigo_ibge_municipio', 'p.ano_referencia']) }} as sk_populacao_municipal,
        cast(g.sk_municipio as varchar) as sk_municipio,
        cast(p.codigo_ibge_municipio as integer) as codigo_ibge_municipio,
        cast(p.ano_referencia as integer) as ano_referencia,
        cast(p.populacao_residente as bigint) as populacao_residente,
        cast(p.area_km2 as double) as area_km2,
        cast(p.densidade_demografica as double) as densidade_demografica,
        cast(p.origem_dado as varchar) as origem_dado,
        cast(p.is_interpolado as boolean) as is_interpolado
    from pop as p
    inner join geo as g
        on p.codigo_ibge_municipio = g.codigo_ibge_municipio
)

select *
from final
