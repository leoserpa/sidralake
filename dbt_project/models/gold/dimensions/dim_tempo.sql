with date_spine as (
    select
        cast(gs as date) as data_referencia
    from generate_series(
        date '2018-01-01',
        date '2026-12-01',
        interval 1 month
    ) as t (gs)
),

final as (
    select
        cast(strftime(data_referencia, '%Y%m') as integer) as sk_tempo,
        data_referencia,
        cast(extract(year from data_referencia) as integer) as ano_referencia,
        cast(extract(month from data_referencia) as integer) as mes_referencia,
        cast(strftime(data_referencia, '%Y%m') as varchar) as ano_mes,
        cast(extract(quarter from data_referencia) as integer) as trimestre,
        cast(
            case
                when extract(month from data_referencia) <= 6 then 1
                else 2
            end as integer
        ) as semestre,
        cast(extract(year from data_referencia) = 2022 as boolean) as is_ano_censitario
    from date_spine
)

select *
from final
