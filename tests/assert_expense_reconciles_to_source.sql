-- RECONCILIATION: total underwriting expense in the gold fact must equal the
-- underwriting expense in the raw source of record (raw_policies). If the model
-- drops a row, fans out on a join, or corrupts the value between source and
-- gold, the totals diverge and this test fails. Returns rows only on failure
-- (tolerance 0.01). The per-LOB rate logic itself is cross-checked independently
-- by assert_combined_ratio_parity.
with source_total as (
    select round(sum(underwriting_expense), 2) as amt from {{ ref('raw_policies') }}
),
gold_total as (
    select round(sum(underwriting_expense), 2) as amt from {{ ref('fct_premium') }}
)
select
    s.amt as source_expense,
    g.amt as gold_expense,
    abs(s.amt - g.amt) as diff
from source_total s
cross join gold_total g
where abs(s.amt - g.amt) > 0.01
