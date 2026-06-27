-- Grain: one row per claim, enriched with policy attributes for slicing.
--
-- Incremental: on a refresh, only claims from a newer ingestion batch
-- (loaded_at > the max already loaded) are processed; new claims for existing
-- policies still join because stg_policies is the full set. unique_key dedupes a
-- re-delivered claim. Full rebuild is `dbt build --full-refresh`.
{{ config(
    materialized='incremental',
    unique_key='claim_id',
    on_schema_change='append_new_columns'
) }}
with clm as (
    select * from {{ ref('stg_claims') }}
    {% if is_incremental() %}
    where loaded_at > (select coalesce(max(loaded_at), cast('1900-01-01' as timestamp)) from {{ this }})
    {% endif %}
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
    clm.incurred_loss,
    clm.loaded_at
from clm
inner join pol on clm.policy_id = pol.policy_id
