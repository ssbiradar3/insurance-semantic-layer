with source as (
    select * from {{ ref('raw_policies') }}
)
select
    policy_id,
    policy_number,
    line_of_business,
    cast(effective_date as date)   as effective_date,
    cast(expiration_date as date)  as expiration_date,
    state,
    location_id,
    cast(written_premium as double) as written_premium,
    status
from source
