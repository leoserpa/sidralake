with base_dates as (
    select
        cast(gs as date) as date_day
    from generate_series(
        date '2018-01-01',
        date '2026-12-31',
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
