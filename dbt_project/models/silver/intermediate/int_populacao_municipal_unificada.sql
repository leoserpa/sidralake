with censo as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        populacao_residente,
        area_km2,
        'CENSO_2022' as origem_dado,
        false as is_interpolado
    from {{ ref('stg_ibge__censo_populacao') }}
),

area_ref as (
    select
        codigo_ibge_municipio,
        area_km2
    from censo
),

estimativas as (
    select
        e.codigo_ibge_municipio,
        e.ano_referencia,
        e.populacao_estimada as populacao_residente,
        a.area_km2,
        'ESTIMATIVA_IBGE' as origem_dado,
        false as is_interpolado
    from {{ ref('stg_ibge__estimativa_populacao') }} as e
    left join area_ref as a
        on e.codigo_ibge_municipio = a.codigo_ibge_municipio
    where e.ano_referencia <> 2022
        and e.populacao_estimada is not null
),

interpolado_2023 as (
    select
        c.codigo_ibge_municipio,
        2023 as ano_referencia,
        cast(round((c.populacao_residente + e24.populacao_residente) / 2.0) as bigint) as populacao_residente,
        c.area_km2,
        'INTERPOLACAO_LINEAR' as origem_dado,
        true as is_interpolado
    from censo as c
    inner join estimativas as e24
        on c.codigo_ibge_municipio = e24.codigo_ibge_municipio
        and e24.ano_referencia = 2024
    where c.populacao_residente is not null
),

unificado as (
    select * from censo
    union all
    select * from estimativas
    union all
    select * from interpolado_2023
),

final as (
    select
        codigo_ibge_municipio,
        ano_referencia,
        populacao_residente,
        area_km2,
        case
            when area_km2 is not null and area_km2 > 0
                then round(populacao_residente / area_km2, 4)
            else cast(null as double)
        end as densidade_demografica,
        origem_dado,
        is_interpolado
    from unificado
)

select *
from final
