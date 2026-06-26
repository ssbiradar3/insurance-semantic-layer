-- METRIC PARITY: the headline loss ratio computed from the gold facts must match
-- the loss ratio computed independently from raw seeds, within tolerance.
-- This is the pattern you extend to compare a MetricFlow metric against a
-- trusted/legacy source of truth in CI. Fails if the numbers drift apart.
with gold as (
    select
        (select sum(incurred_loss) from {{ ref('fct_claim') }})
        / nullif((select sum(earned_premium) from {{ ref('fct_premium') }}), 0) as lr
),
source as (
    select
        (select sum(paid_loss + case_reserve) from {{ ref('raw_claims') }})
        / nullif((
            select sum(
                written_premium * greatest(0.0, least(1.0,
                    date_diff('day', cast(effective_date as date),
                        least(cast('2026-06-30' as date), cast(expiration_date as date)))
                    / nullif(date_diff('day', cast(effective_date as date),
                                       cast(expiration_date as date)), 0)))
            )
            from {{ ref('raw_policies') }}
        ), 0) as lr
)
select gold.lr as gold_lr, source.lr as source_lr,
       abs(gold.lr - source.lr) as diff
from gold cross join source
where abs(gold.lr - source.lr) > 0.0001
