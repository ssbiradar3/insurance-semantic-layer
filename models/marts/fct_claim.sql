-- Grain: one row per claim, enriched with policy attributes for slicing.
with clm as (
    select * from {{ ref('stg_claims') }}
),
pol as (
    select * from {{ ref('stg_policies') }}
)
select
    clm.claim_id,
    clm.policy_id,
    pol.line_of_business,
    pol.state,
    pol.location_id,
    clm.loss_date,
    clm.peril,
    clm.claim_status,
    clm.paid_loss,
    clm.case_reserve,
    clm.incurred_loss
from clm
inner join pol on clm.policy_id = pol.policy_id
