-- RECONCILIATION: total incurred loss in the gold fact must equal paid + reserve
-- from the raw claims source. Guards against claims dropped by the policy join.
with source_total as (
    select round(sum(paid_loss + case_reserve), 2) as amt from {{ ref('raw_claims') }}
),
gold_total as (
    select round(sum(incurred_loss), 2) as amt from {{ ref('fct_claim') }}
)
select s.amt, g.amt, abs(s.amt - g.amt) as diff
from source_total s cross join gold_total g
where abs(s.amt - g.amt) > 0.01
