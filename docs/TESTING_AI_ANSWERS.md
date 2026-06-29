# Testing the Answer: the Semantic Layer as the Trust Boundary

> How do you test what a dashboard — or an AI — reports when it sits on top of a
> dataset or tables (sometimes AI-generated)? Short answer: you don't let the
> consumer query raw tables. You put a governed, tested semantic layer in between,
> and the tests on that layer **are** the test of the answer.

## The problem

BI dashboards — and, increasingly, LLM / text-to-SQL agents — answer business
questions by querying tables. If they hit raw or AI-generated tables directly,
every consumer re-derives the metric, and an LLM will cheerfully write SQL that is
*subtly* wrong: wrong join, wrong filter, wrong grain, double counting. You cannot
QA an infinite set of ad-hoc queries. And the failure is quiet — a confident,
wrong number that flows into a pricing or reserving decision.

## The pattern: make the semantic layer the only door

Consumers (a dashboard, an API, an LLM) ask for **governed metrics** — defined
once in MetricFlow — not raw SQL. That collapses *"test every possible query"*
into *"test a finite set of governed definitions."* The semantic layer becomes the
trust boundary; everything below it is tested before any answer is served.

```
  raw / AI-generated tables
        |  (tested transforms: staging -> marts)
  governed semantic layer   <-- the trust boundary; metrics defined once
        |
  dashboard  ·  API  ·  LLM / NL query     all get the same tested number
```

## What makes an answer trustworthy here — and how each part is tested

1. **One definition.** `loss_ratio`, `combined_ratio` exist once
   (`models/semantic/`). A consumer can't silently redefine them.
   `mf validate-configs` proves every metric resolves against the warehouse.
2. **Reconciliation to source.** The `assert_*` tests recompute the headline
   numbers from the raw source of record and fail the build if the gold metric
   drifts. This is literally *"test the answer against the system of record,"*
   on every build.
3. **Logic is unit-tested.** The earned-premium proration has a dbt unit test
   with fixed inputs/outputs, so the math can't regress unnoticed.
4. **Inputs are guarded.** Schema / integrity / domain tests plus volume monitors
   catch a broken or partial upstream load before it ever reaches a metric.
5. **Point-in-time correctness.** The SCD2 snapshot answers "what was the status
   *as of* X," so historical answers aren't quietly rewritten.
6. **It runs every build.** All of the above are in CI — nothing merges red.

## Why this is the answer for AI specifically

- An LLM **constrained to the semantic layer** composes *governed metrics and
  dimensions* (e.g., via MetricFlow) instead of free-form SQL — so its answers are
  bounded by definitions that are already tested. That removes the single largest
  source of wrong AI answers: the model inventing the calculation.
- The number the AI returns has **already passed reconciliation**; if the data
  drifts, the gate fails *before* a stale answer can be served.
- **Proof in this repo:** the Streamlit dashboard (`app/streamlit_app.py`) does
  not write SQL — it calls `mf query` against the semantic layer. That is exactly
  the interface an AI agent should use, and why its numbers are trustworthy by
  construction.

## A reviewer's checklist (how a PM or analyst QAs an answer)

- Is the metric defined **in the semantic layer**, or re-derived in the BI tool /
  app? (Only the former is trustworthy.)
- Does a **reconciliation test** tie it to the source of record? Show me the test.
- When did it last **build green**, and is the source **fresh**?
- For an "as of" question, is there **history (SCD2)** or only current state?
- Can I **reproduce** the number from raw data within tolerance?

## The product view

Trust is a *product feature*, not a nice-to-have. The success metrics are simple:
**zero reconciliation breaches reach a dashboard**, and **metric reuse** — one
definition consumed by BI, APIs, and AI rather than N re-implementations. That is
what turns "self-serve" from a slogan into something underwriters, actuaries, and
finance will actually trust.
