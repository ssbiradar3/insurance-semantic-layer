with pol as (
    select * from {{ ref('stg_policies') }}
)
select
    policy_id,
    policy_number,
    line_of_business,
    effective_date,
    expiration_date,
    state,
    location_id,
    status
from pol
