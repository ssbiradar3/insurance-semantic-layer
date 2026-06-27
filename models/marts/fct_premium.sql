-- Grain: one row per policy.
-- written_premium comes straight from the policy.
-- earned_premium is pro-rated to a fixed snapshot date so the number is
-- deterministic and reconcilable.
--
-- Incremental: on a refresh, only policies from a newer ingestion batch
-- (loaded_at > the max already loaded) are processed. unique_key dedupes if a
-- policy is re-delivered. A full rebuild is `dbt build --full-refresh`.
{{ config(
    materialized='incremental',
    unique_key='policy_id',
    on_schema_change='append_new_columns'
) }}
with pol as (
    select * from {{ ref('stg_policies') }}
    {% if is_incremental() %}
    where loaded_at > (select coalesce(max(loaded_at), cast('1900-01-01' as timestamp)) from {{ this }})
    {% endif %}
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
        pol.underwriting_expense,
        pol.loaded_at,
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
    underwriting_expense,
    loaded_at,
    round(written_premium * earned_fraction, 2) as earned_premium
from earned
