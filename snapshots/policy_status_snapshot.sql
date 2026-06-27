-- SCD2 history of policy status. dbt snapshots capture how a mutable attribute
-- changes over time: each run compares the current source to the latest stored
-- version and, when `status` changes, closes the old record (sets dbt_valid_to)
-- and opens a new one. This is the "handles change" counterpart to the
-- incremental facts (which handle new rows). Status is dimensional only here, so
-- this does not affect any reconciliation.
{% snapshot policy_status_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='policy_id',
        strategy='check',
        check_cols=['status'],
        invalidate_hard_deletes=True
    )
}}
select
    policy_id,
    policy_number,
    line_of_business,
    status,
    loaded_at
from {{ ref('stg_policies') }}
{% endsnapshot %}
