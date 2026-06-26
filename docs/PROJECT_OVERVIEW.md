# Insurance Semantic Layer — Project Overview

> A one-page narrative for a hiring manager or portfolio reader. For the
> production architecture and the local→company migration, see
> [PRODUCTION.md](PRODUCTION.md).

## TL;DR

I built a **trusted, self-serve semantic layer for Property & Casualty insurance**
on dbt + MetricFlow. Stakeholders can self-serve governed KPIs like `loss_ratio`
and `combined_ratio` by state or line of business, and **every metric is
reconciled back to source and gated in CI before it can reach a dashboard**. The
point isn't just defining metrics — it's making them *provably trustworthy*.

## The problem

In insurance, the same KPI is computed five different ways in five different
tools — a number in a Tableau dashboard rarely matches the actuarial system of
record, and nobody can explain why. Analysts rebuild `loss_ratio` in spreadsheets;
definitions drift; trust erodes. The expensive failure isn't a broken pipeline —
it's a **silently wrong number** that leaks into a pricing or reserving decision.

## The solution

One governed definition per metric, defined once and queryable everywhere, with
**reconciliation tests that prove the number ties back to the raw source on every
build**. A metric is trusted because it reconciles and passes the gate — not
because of who authored it.

## Architecture

```
  raw sources (policy admin, claims system, locations, vendor cat feed)
        |
  staging  (stg_*)            cleaned, typed, one model per source
        |
  marts    (dim_*, fct_*)     gold star schema; vendor feed joined onto exposures
        |
  semantic (sem_*, metrics)   MetricFlow semantic models + governed KPIs
        |
  consumers                   BI / API / natural language — all one definition
```

Quality gates run at **every** layer:
- **Staging** — schema tests (unique, not_null, accepted_values, ranges).
- **Marts** — vendor-join integrity (no exposure silently dropped or fanned out).
- **Reconciliation** — singular tests recompute headline numbers straight from
  the raw source of record and fail the build if the gold tables diverge.
- **Semantic** — `mf validate-configs` confirms every metric resolves against
  the warehouse.
- **CI** — all of the above run on every push and pull request. Nothing merges red.

## What makes it different: trust is enforced, not assumed

The differentiator is the **reconciliation pattern**. For example
[`assert_loss_ratio_parity.sql`](../tests/assert_loss_ratio_parity.sql) computes
the loss ratio independently from the raw seeds and fails if it drifts from the
gold metric by more than a tolerance. This is exactly the control an actuary or
auditor asks for: *prove this dashboard number equals the system of record.*

## Worked example: `combined_ratio` end-to-end

`combined_ratio` (loss ratio + expense ratio) is the headline P&C
underwriting-profitability KPI — below 1.0 is an underwriting profit. I added it
as a complete vertical slice that honors the trust rule:

1. **Source** — `underwriting_expense` generated deterministically per policy.
2. **Staging → marts** — flows through `stg_policies` → `fct_premium`.
3. **Semantic** — an `expense_ratio` ratio metric and a `combined_ratio` *derived*
   metric (`loss_ratio + expense_ratio`), composed in MetricFlow.
4. **Trust** — two reconciliation tests tie the gold metric to the source of
   record and verify the combined ratio against an independent recomputation.

```bash
mf query --metrics loss_ratio,expense_ratio,combined_ratio \
         --group-by policy__line_of_business
```

```
line_of_business    loss_ratio   expense_ratio   combined_ratio
Property               2.52033            0.28          2.80033
Casualty               2.59643            0.30          2.89643
Marine                 2.08353            0.26          2.34353
Cyber                  3.36258            0.34          3.70258
```

> A subtle bug I caught: my first expense reconciliation test re-derived the rate
> math in SQL and failed by $0.12 — because DuckDB's `round()` is half-away-from-zero
> while Python's is banker's rounding. Rather than loosen the tolerance, I fixed
> the *concept*: a reconciliation should tie the gold fact to the source-of-record
> column (sum-to-sum), not re-implement the math in a different engine.

## What this demonstrates

- **Analytics / data engineering** — dimensional modeling, dbt project structure,
  staging→marts→semantic layering, incremental-ready facts.
- **Semantic layer & metrics governance** — MetricFlow entities, measures, ratio
  and derived metrics, one global namespace.
- **Data quality & trust** — generic tests, `dbt_expectations`, and a
  reconciliation-to-source pattern most demos skip entirely.
- **Engineering discipline** — CI gate, a pre-edit hook that runs the gate
  automatically, warehouse-agnostic config, clean git history.
- **Domain fluency** — P&C metrics (loss ratio, combined ratio, claim frequency /
  severity), vendor catastrophe enrichment, actuarial reconciliation.

## Tech stack

| Layer | Tool |
|---|---|
| Transform | dbt Core |
| Warehouse | DuckDB locally · warehouse-agnostic (Snowflake-ready) |
| Semantic layer | MetricFlow |
| Testing | dbt generic tests · dbt_expectations · singular reconciliation tests |
| CI | GitHub Actions |
| Automation | Claude Code PostToolUse hook runs the gate on every model edit |

## Run it in ~90 seconds

```bash
pip install dbt-duckdb dbt-metricflow
dbt deps
python scripts/generate_data.py
export DBT_PROFILES_DIR=$(pwd)
dbt build            # builds models + runs every test incl. reconciliation
mf validate-configs  # validates the semantic layer
mf query --metrics combined_ratio --group-by policy__line_of_business
```

## How it scales to a company

Everything here is warehouse-agnostic. Going to production is mostly swapping the
*engine and surrounding infrastructure*, not rewriting logic: DuckDB → Snowflake,
`seeds/` → declared `sources`, wrapped in ingestion + orchestration + CI-against-the-warehouse + governance. The modeling, metrics, tests, and trust gate
transfer as-is. Full walkthrough in [PRODUCTION.md](PRODUCTION.md).
