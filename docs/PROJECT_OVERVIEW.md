# Insurance Semantic Layer — Project Overview

> A one-page narrative of the project. **Live demo:**
> https://insurance-semantic-layer.streamlit.app/ . For the production architecture
> and the local→company migration, see [PRODUCTION.md](PRODUCTION.md).

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
Marine                 0.52041            0.26          0.78041   # underwriting profit
Property               0.62859            0.28          0.90859
Casualty               0.64859            0.30          0.94859
Cyber                  0.83874            0.34          1.17873   # underwriting loss
```

> A subtle bug I caught: my first expense reconciliation test re-derived the rate
> math in SQL and failed by $0.12 — because DuckDB's `round()` is half-away-from-zero
> while Python's is banker's rounding. Rather than loosen the tolerance, I fixed
> the *concept*: a reconciliation should tie the gold fact to the source-of-record
> column (sum-to-sum), not re-implement the math in a different engine.

## What this demonstrates — three lenses

I built this to show the full arc of owning a data product: framing the problem
(**product**), building it to last (**engineering**), and using it to answer a
question (**analytics**).

**Data product manager**
- Frames a real, expensive problem (untrusted metrics → bad pricing/reserving
  decisions) and ships a *product*: governed, self-serve KPIs with trust built in.
- Defines users, the job-to-be-done, success metrics, and a roadmap — see
  [Product thinking](#product-thinking-pm-lens) below.
- Makes explicit trade-offs (e.g. native volume monitors vs. Elementary on a
  zero-infra engine — see [OBSERVABILITY.md](OBSERVABILITY.md)).

**Analytics engineer / data engineer**
- Dimensional modeling and a clean `staging → marts → semantic` structure.
- **Incremental** fact tables with a `loaded_at` watermark, a simulated daily
  refresh, and a scheduled CI job; **SCD2 snapshot** for changing dimensions.
- Trust enforced: schema tests, `dbt_expectations` (incl. volume monitors), a
  **dbt unit test** of the proration logic, and the reconciliation-to-source
  pattern most demos skip — all gated in CI.

**Data analyst**
- Speaks P&C fluently (loss ratio, combined ratio, claim frequency / severity)
  and uses the layer to produce an actual insight — see
  [An analyst's read](#an-analysts-read-analyst-lens).

## Product thinking (PM lens)

- **Users / customers:** actuaries and pricing analysts (need numbers that tie to
  the system of record), underwriting & finance leaders (combined ratio by book),
  and BI developers (one definition to build on).
- **Job to be done:** "Let me self-serve a trusted KPI by state or line of
  business without rebuilding it in a spreadsheet or doubting the number."
- **Success metrics:** metric reuse / adoption (one definition consumed by N
  surfaces), time-to-insight (self-serve vs. a ticket to the data team), and
  *trust* (zero reconciliation breaches reaching a dashboard).
- **Roadmap (prioritized):** ① retention/renewal & `policies_in_force` metrics →
  ② row/column-level access for PII → ③ Elementary anomaly detection on a real
  warehouse → ④ a natural-language query surface over the semantic layer.

## An analyst's read (analyst lens)

Querying the layer (synthetic data, tuned to realistic P&C levels):

- **Marine is the most profitable book** — a 78% combined ratio (0.78), driven by
  the *lowest* claim frequency (0.56) and the *lowest* expense load (26%).
- **Cyber is the only unprofitable book** — a **118% combined ratio (1.18), an
  underwriting loss**: the highest loss ratio (0.84) *and* the highest expense
  load (34%). A double problem — expense discipline alone won't fix it.
- **Property** still runs profitably (91%) despite the highest claim **frequency**
  (0.77) and **severity** (~34.5k) — a high-volume book that's priced for it.
- **Geography:** California is the most profitable state (74%); Colorado (120%),
  Florida (114%), and Washington (104%) run at **underwriting losses** —
  consistent with catastrophe exposure.
- **So what:** the combined-ratio decomposition points underwriting at *Cyber
  loss cost* and the *CO / FL / WA cat-exposed book* first — exactly the action
  the metric layer exists to enable.

## Tech stack

| Layer | Tool |
|---|---|
| Transform | dbt Core (incl. incremental models + SCD2 snapshot) |
| Warehouse | DuckDB locally · warehouse-agnostic (Snowflake-ready) |
| Semantic layer | MetricFlow |
| Testing | dbt generic tests · dbt_expectations (incl. volume monitors) · dbt unit tests · singular reconciliation tests |
| Observability | `dbt docs` lineage/catalog report (Elementary in production) |
| BI / consumer | Streamlit dashboard querying the semantic layer live |
| CI | GitHub Actions (gate on push + scheduled incremental refresh) |
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
