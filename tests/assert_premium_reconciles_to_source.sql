-- RECONCILIATION: total written premium in the gold fact must equal the sum of
-- coverage parts in the raw source. If a join fans out or drops rows, the totals
-- diverge and this test fails. Returns rows only on failure (tolerance 0.01).
with source_total as (
    select round(sum(coverage_premium), 2) as amt from {{ ref('raw_coverages') }}
),
gold_total as (
    select round(sum(written_premium), 2) as amt from {{ ref('fct_premium') }}
)
select
    s.amt as source_premium,
    g.amt as gold_premium,
    abs(s.amt - g.amt) as diff
from source_total s
cross join gold_total g
where abs(s.amt - g.amt) > 0.01
