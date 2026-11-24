with base_dates as (
    select
        cast(gs as date) as date_day
    from generate_series(
        date '2018-01-01',
        make_date(cast(extract(year from current_date) as integer) + 1, 12, 31),
        interval 1 day
    ) as t (gs)
),

final as (
    select
        date_day
    from base_dates
)

select *
from final
