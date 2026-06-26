-- Grain: one row per policy.
-- written_premium comes straight from the policy.
-- earned_premium is pro-rated to a fixed snapshot date so the number is
-- deterministic and reconcilable.
with pol as (
    select * from {{ ref('stg_policies') }}
),
snapshot_date as (
    select cast('2026-06-30' as date) as as_of
),
earned as (
    select
        pol.policy_id,
        pol.line_of_business,
        pol.state,
        pol.location_id,
        pol.effective_date,
        pol.expiration_date,
        pol.written_premium,
        greatest(0.0, least(1.0,
            date_diff('day', pol.effective_date,
                      least(s.as_of, pol.expiration_date))
            / nullif(date_diff('day', pol.effective_date, pol.expiration_date), 0)
        )) as earned_fraction
    from pol
    cross join snapshot_date s
)
select
    policy_id,
    line_of_business,
    state,
    location_id,
    effective_date,
    written_premium,
    round(written_premium * earned_fraction, 2) as earned_premium
from earned
