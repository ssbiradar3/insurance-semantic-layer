# Source-to-Target Mapping (STM)

> How each governed number is built from the raw source of record, and the
> reconciliation control that proves the target ties back to source. This is the
> artifact a data analyst hands to developers as a build spec (with acceptance
> criteria) and uses to obtain business sign-off before a number reaches the EDW,
> the GL, or an externally-reported result.

**Flow:** raw seeds (system of record) → staging (`stg_*`) → marts (gold `dim_*` /
`fct_*`) → semantic metrics. "Target" is the gold column or metric a consumer
sees; "Source" is the raw column it must reconcile back to. Every target has a
**reconciliation control** that runs on every build / in CI.

## 1. Premium facts → `fct_premium` (grain: one row per policy)

| Target (gold) | Source (system of record) | Transformation / business rule | Reconciliation control (acceptance criteria) |
|---|---|---|---|
| `fct_premium.written_premium` | `raw_coverages.coverage_premium` (rolled to policy) | Written premium = sum of coverage premiums for the policy. | **`assert_premium_reconciles_to_source`** — Σ `coverage_premium` = Σ `written_premium` (tolerance 0.01). |
| `fct_premium.earned_premium` | `raw_policies.written_premium`, `effective_date`, `expiration_date` | Pro-rated to the 2026-06-30 snapshot: `written × clamp((snapshot − eff) / (exp − eff), 0, 1)`. | **`assert_loss_ratio_parity`** recomputes earned premium from raw and ties it to the gold total (tolerance 1e-4). |
| `fct_premium.underwriting_expense` | `raw_policies.underwriting_expense` | Carried 1:1 from source (source value = written premium × per-line-of-business expense rate). | **`assert_expense_reconciles_to_source`** — Σ gold = Σ source column (tolerance 0.01). |
| `fct_premium.loaded_at` | `raw_policies.loaded_at` | Ingestion-batch watermark; drives the incremental load. | `not_null`. |

## 2. Claim facts → `fct_claim` (grain: one row per claim)

| Target (gold) | Source | Transformation / business rule | Reconciliation control |
|---|---|---|---|
| `fct_claim.incurred_loss` | `raw_claims.paid_loss`, `raw_claims.case_reserve` | Incurred loss = `paid_loss + case_reserve`. | **`assert_claims_reconcile_to_source`** — Σ (`paid_loss` + `case_reserve`) = Σ `incurred_loss` (tolerance 0.01). |
| `fct_claim.policy_id`, `line_of_business`, `state` | `raw_claims.policy_id` → `stg_policies` | Inner join to the policy to attach slicing attributes. | `relationships`: `fct_claim.policy_id` → `dim_policy.policy_id`. |

## 3. Reference / master data → `dim_location`

| Target (gold) | Source | Transformation / business rule | Reconciliation control |
|---|---|---|---|
| `dim_location.flood_zone` | `raw_vendor_flood.flood_zone` joined on `location_id` | Third-party (Verisk / RMS-style) enrichment joined onto the exposure; unmatched exposures coded `UNKNOWN`. | `relationships` + `accepted_values ['X','A','AE','VE','UNKNOWN']` — proves no exposure is silently dropped or mis-coded by the join. |

## 4. Governed metrics (semantic layer, defined once in `models/semantic/`)

| Metric (target) | Composed from | Definition | Reconciliation control |
|---|---|---|---|
| `loss_ratio` | `incurred_loss` / `earned_premium` | Incurred loss over earned premium. | `assert_loss_ratio_parity` (gold vs. recomputed-from-source). |
| `expense_ratio` | `underwriting_expense` / `written_premium` | Underwriting expense over written premium (trade basis). | Covered by the premium + expense reconciliations above. |
| `combined_ratio` | `loss_ratio` + `expense_ratio` | Derived metric; the headline underwriting-profitability KPI. | `assert_combined_ratio_parity` (gold vs. recomputed-from-source). |

## Why this matters for the GL and financial reporting

These targets are the kind of numbers that feed an **EDW, Oracle GL, and ceded
reinsurance**, and that roll up into **externally-reported financial results** —
where a silently wrong figure is an audit / regulatory issue, not a dashboard nit.

The reconciliation controls above are **"full source-to-target reconciliation"
expressed as code**: they run on every build and in CI, so a number cannot reach
the EDW or a financial report unless it still ties back to the system of record
within tolerance. It is the same control you would place on a GL feed or a
Schedule F / ceded-reinsurance figure — automated, versioned, and gated, rather
than a manual tie-out in a spreadsheet that no one can reproduce six months later.

## How an analyst would use this STM

- **Build spec for developers** — each row gives source, rule, and target.
- **Acceptance criteria** — each row's reconciliation control *is* the sign-off
  criterion. "Validate the developer's work" and "obtain business sign-off"
  become: is the gate green, and does the reconciliation tie out within tolerance?
- **Release evidence** — the CI run is the reproducible proof attached to the
  story before code is released to production.
