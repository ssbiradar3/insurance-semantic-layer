-- METRIC PARITY: the combined ratio (loss ratio + expense ratio) computed from
-- the gold facts must match the combined ratio computed independently from raw
-- seeds, within tolerance. This mirrors assert_loss_ratio_parity and is the
-- pattern for comparing a derived MetricFlow metric to a trusted source of truth
-- in CI. Fails if the numbers drift apart.
with rate(line_of_business, expense_rate) as (
    values ('Property', 0.28), ('Casualty', 0.30), ('Marine', 0.26), ('Cyber', 0.34)
),
gold as (
    select
        (select sum(incurred_loss) from {{ ref('fct_claim') }})
            / nullif((select sum(earned_premium) from {{ ref('fct_premium') }}), 0)
        + (select sum(underwriting_expense) from {{ ref('fct_premium') }})
            / nullif((select sum(written_premium) from {{ ref('fct_premium') }}), 0) as cr
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
            ), 0)
        + (
            select sum(round(p.written_premium * r.expense_rate, 2))
            from {{ ref('raw_policies') }} p
            join rate r on p.line_of_business = r.line_of_business
          )
            / nullif((select sum(written_premium) from {{ ref('raw_policies') }}), 0) as cr
)
select gold.cr as gold_cr, source.cr as source_cr,
       abs(gold.cr - source.cr) as diff
from gold cross join source
where abs(gold.cr - source.cr) > 0.0001
