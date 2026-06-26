with source as (
    select * from {{ ref('raw_coverages') }}
)
select
    coverage_id,
    policy_id,
    coverage_type,
    cast(coverage_limit as double)   as coverage_limit,
    cast(coverage_premium as double) as coverage_premium
from source
