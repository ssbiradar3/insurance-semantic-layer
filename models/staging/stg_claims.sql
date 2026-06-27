with source as (
    select * from {{ ref('raw_claims') }}
)
select
    claim_id,
    policy_id,
    cast(loss_date as date)   as loss_date,
    cast(report_date as date) as report_date,
    claim_status,
    cast(paid_loss as double)    as paid_loss,
    cast(case_reserve as double) as case_reserve,
    cast(paid_loss as double) + cast(case_reserve as double) as incurred_loss,
    peril,
    cast(loaded_at as timestamp) as loaded_at
from source
