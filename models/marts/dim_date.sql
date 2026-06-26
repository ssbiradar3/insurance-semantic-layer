-- Time spine required by MetricFlow for any time-based metric (day grain).
with days as (
    select cast(range as date) as date_day
    from range(date '2023-01-01', date '2026-12-31', interval '1 day')
)
select
    date_day,
    extract(year  from date_day) as year,
    extract(month from date_day) as month,
    extract(quarter from date_day) as quarter
from days
