# Insurance Semantic Layer (dbt + MetricFlow)

A trusted, self-serve semantic layer for Property and Casualty insurance, built
on dbt and MetricFlow and running locally on DuckDB with zero warehouse cost.
Synthetic policy, claim, and exposure data is enriched with a third-party vendor
feed, and every metric is reconciled to source and gated in CI before it can
reach a dashboard.

The goal of this repo is not just to define metrics. It is to make them
**trustworthy**: a stakeholder can self-serve `loss_ratio` by state or line of
business and know the number ties back to the raw source, because a
reconciliation test proves it on every build.

## Architecture

```
  seeds (raw P&C data + vendor flood feed)
        |
  staging  (stg_*)            cleaned, typed, one model per source
        |
  marts    (dim_*, fct_*)     gold star schema, vendor feed joined onto exposures
        |
  semantic (sem_*, metrics)   MetricFlow semantic models + governed KPIs
        |
  consumers                   BI tools / APIs / natural-language, all one definition
```

Quality gates run at every layer: schema tests in staging, vendor-join integrity
in marts, reconciliation tests against source, and `mf validate-configs` on the
semantic layer.

## The vendor data story

In a real specialty insurer, exposures are enriched with commercial third-party
feeds. This repo uses a free, openly modelled flood file as a reproducible
stand-in so the project runs anywhere. The mapping:

| Vendor category (real world)        | Stand-in in this repo        |
| ----------------------------------- | ---------------------------- |
| Catastrophe / peril (Verisk, RMS)   | `raw_vendor_flood` flood zone + risk score |
| Property characteristics (CoreLogic)| location attributes in `raw_locations`      |
| Geocoding                           | lat / long in `raw_locations`               |

The vendor feed is joined onto the exposure dimension in `dim_location`, and the
join is validated: a relationships test plus an `UNKNOWN` accepted-values check
proves no exposure is silently dropped or left unmatched.

## Metrics

Defined once in `models/semantic/_metrics.yml`, queryable everywhere:

- Simple: `written_premium`, `earned_premium`, `incurred_loss`, `claim_count`, `policy_count`
- Ratio: `loss_ratio`, `claim_frequency`, `claim_severity`

`loss_ratio` spans two semantic models (loss from claims, premium from policies)
and MetricFlow builds the join automatically through the shared `policy` entity.

## How trust is enforced

1. **Reconciliation tests** (`tests/assert_*`) recompute the headline numbers
   straight from the raw seeds and fail the build if the gold tables diverge by
   more than a tolerance. This is the pattern you extend to compare a metric
   against a legacy or certified source of truth.
2. **Vendor-join integrity** proves the third-party enrichment did not drop or
   fan out rows.
3. **Semantic validation** (`mf validate-configs`) confirms the metrics resolve
   against the warehouse.
4. **CI gate** (`.github/workflows/ci.yml`) runs all of the above on every push
   and pull request. Nothing merges red.

A metric is trusted because it reconciles and passes the gate, not because of who
or what authored it.

## Claude Code automation

- `CLAUDE.md` is the project constitution Claude reads each session.
- `.claude/settings.json` defines a PostToolUse hook: whenever a model, metric,
  or test file is edited, the full gate (`scripts/validate.sh`) runs
  automatically, so a broken or unreconciled metric surfaces immediately instead
  of in production.

## Quickstart

```bash
pip install dbt-duckdb dbt-metricflow
dbt deps
python scripts/generate_data.py
export DBT_PROFILES_DIR=$(pwd)
dbt build              # builds models, runs every test incl. reconciliation
mf validate-configs    # validates the semantic layer
mf query --metrics loss_ratio,claim_frequency --group-by policy__line_of_business
```

## Targeting Snowflake later

Everything is warehouse-agnostic dbt. To run on Snowflake instead of DuckDB,
uncomment the `prod` output in `profiles.yml`, set the `SNOWFLAKE_*` environment
variables, and run `dbt build --target prod`. The models, tests, and metrics do
not change.

## Repo layout

```
seeds/                raw synthetic data + vendor feed (CSV)
models/staging/       cleaned source models + schema tests
models/marts/         gold dim/fct models + vendor join + tests
models/semantic/      MetricFlow semantic models, metrics, time spine
tests/                singular reconciliation / parity tests
scripts/              data generator + the validation gate
.claude/              Claude Code hook config
.github/workflows/    CI
```
