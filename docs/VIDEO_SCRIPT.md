# Demo Video — Script, Shot List & Submission Kit

A film-ready script for a **3–5 minute** walkthrough you can send to a hiring
manager or pin to your portfolio/LinkedIn. It follows a **problem → solution →
proof → impact** arc. There's a tight **60–90s LinkedIn cut** at the bottom.

> Replace `[Your name]` and adjust the role framing (analytics engineer / data
> engineer / BI engineer) to match the job you're targeting.

---

## 0. Before you hit record (pre-flight checklist)

**Tools**
- [ ] Screen recorder with webcam bubble: **Loom** (easiest to share) or OBS / QuickTime.
- [ ] Record at 1080p. Webcam in a corner for the intro/outro builds trust.
- [ ] Quiet room, external mic if you have one. Test audio levels first.

**Terminal**
- [ ] Big font (18pt+), light-on-dark theme, clear the scrollback.
- [ ] `cd ~/projects/insurance-semantic-layer-clean && source .venv/bin/activate && export DBT_PROFILES_DIR=$(pwd)`
- [ ] Pre-run once so packages are warm and `dev.duckdb` exists (you'll re-run live).
- [ ] Have these commands staged in your history (press ↑) so you don't fumble:
  - `python scripts/generate_data.py`
  - `dbt build`
  - `mf validate-configs`
  - `mf query --metrics loss_ratio,expense_ratio,combined_ratio --group-by policy__line_of_business`

**Editor / browser tabs (to flash on screen)**
- [ ] `README.md`, `models/semantic/_metrics.yml`, `tests/assert_loss_ratio_parity.sql`
- [ ] The GitHub repo page + the green CI check.
- [ ] `docs/PROJECT_OVERVIEW.md` for the closing.

**Do a dry run once.** Aim for under 5 minutes. It's fine to edit out dead air.

---

## 1. Full script (3–5 min)

> Format: **[ON SCREEN]** = what the viewer sees · *spoken* = what you say.
> Timings are targets, not handcuffs.

### Scene 1 — Hook & the problem (0:00–0:35)
**[ON SCREEN]** Webcam, friendly. Then cut to the README title.

*"Hi, I'm [Your name]. In insurance, the same number — say, loss ratio — gets
calculated five different ways in five different tools, and the figure on a
dashboard rarely matches the actuarial system of record. The expensive failure
isn't a pipeline that breaks loudly — it's a number that's silently wrong and
leaks into a pricing or reserving decision. So I built a semantic layer whose
whole job is to make insurance metrics **provably trustworthy**."*

### Scene 2 — What it is, in one breath (0:35–1:05)
**[ON SCREEN]** Scroll the README architecture diagram (seeds → staging → marts → semantic).

*"It's a Property & Casualty semantic layer built on dbt and MetricFlow. Raw
policy, claim, and exposure data flows through staging into a gold star schema,
then into a MetricFlow semantic layer where every KPI is defined exactly once.
A vendor catastrophe feed — standing in for something like Verisk or Moody's RMS —
gets joined onto the exposures. Analysts self-serve metrics like loss ratio and
combined ratio by state or line of business, all from one definition."*

### Scene 3 — The differentiator: trust is enforced (1:05–1:55)
**[ON SCREEN]** Open `tests/assert_loss_ratio_parity.sql`. Highlight the tolerance line.

*"Here's the part most demos skip. Every metric is reconciled to source. This
test recomputes loss ratio straight from the raw data and fails the build if the
gold number drifts by more than a tiny tolerance. So a metric isn't trusted
because I wrote it — it's trusted because it ties back to the system of record and
passes the gate. That's the exact control an actuary or auditor asks for."*

### Scene 4 — Live proof: build the whole thing (1:55–2:45)
**[ON SCREEN]** Terminal. Run the commands; let the green output scroll.

*"Let me prove it runs. I'll regenerate the data, then build everything."*
- Run `python scripts/generate_data.py` then `dbt build`.

*"That's every model plus every test — including the reconciliation tests —
passing. Sixty-two green checks. Now I validate the semantic layer."*
- Run `mf validate-configs`.

*"All metrics resolve against the warehouse. Zero errors."*

### Scene 5 — A real feature, end to end (2:45–3:45)
**[ON SCREEN]** Open `models/semantic/_metrics.yml`, scroll to `combined_ratio`.

*"To show how you'd actually work in this, I added the combined ratio — loss ratio
plus expense ratio — which is the headline underwriting-profitability metric;
under 1.0 means the book made an underwriting profit. I added expense data at the
source, flowed it through the layers, defined it as a derived metric in MetricFlow,
and — following the project's own rule — added a reconciliation test for it. Then
I can just query it."*
- Run `mf query --metrics loss_ratio,expense_ratio,combined_ratio --group-by policy__line_of_business`.

*"One definition, queryable by any dimension. And notice combined ratio is
exactly loss ratio plus expense ratio — MetricFlow composes it."*

> **Optional 15s credibility beat:** *"One nice catch along the way — my first
> reconciliation test failed by twelve cents, because DuckDB and Python round
> halves differently. Instead of loosening the tolerance to hide it, I fixed the
> concept: tie the gold fact to the source column, not a re-derivation. Trust over
> a green checkmark."*

### Scene 6 — How it scales to a company (3:45–4:25)
**[ON SCREEN]** Flash `docs/PRODUCTION.md` mapping table, then `profiles.yml` prod target.

*"This runs locally on DuckDB with zero setup, but it's warehouse-agnostic. In a
company you swap DuckDB for Snowflake or BigQuery, point dbt at real source tables
instead of CSV seeds — that's a one-line change per model — and wrap it in
ingestion, orchestration, and CI against the warehouse. The models, metrics, and
trust tests transfer as-is. I documented that whole migration."*

### Scene 7 — Close & call to action (4:25–4:50)
**[ON SCREEN]** Webcam. Then GitHub repo with the green CI badge.

*"So that's a trusted, self-serve insurance semantic layer — modeling, metrics
governance, and a reconciliation-to-source discipline that keeps wrong numbers out
of production. The code, a full write-up, and the production architecture are all
on my GitHub, linked below. I'd love to talk about how this maps to your team's
metrics stack. Thanks for watching."*

---

## 2. LinkedIn / 60–90 second cut

*"In insurance, the same KPI gets computed five different ways and the dashboard
never matches the system of record. I built a P&C semantic layer on dbt and
MetricFlow where every metric — loss ratio, combined ratio, claim frequency — is
reconciled back to source and gated in CI. If a number drifts from the raw data,
the build fails. Here it is building green end to end [show `dbt build` + the
`mf query` result], including a combined-ratio metric I added with its own
reconciliation test. It runs locally on DuckDB but it's warehouse-agnostic —
Snowflake-ready with a one-line change. Code and a full write-up are in the
comments. #dbt #analyticsengineering #insurance #dataengineering"*

---

## 3. Submission kit

### Where to host
- **Loom** — easiest; gives a thumbnail, instant link, and view tracking. Best for
  a direct message to a hiring manager.
- **YouTube (unlisted)** — best for embedding in a portfolio site / README.
- Keep it **public or unlisted**, never "private" (the hiring manager must be able
  to open it without a login).

### Message to a hiring manager (email / LinkedIn / application note)

> **Subject:** Insurance semantic layer — short demo (4 min)
>
> Hi [Name],
>
> For the [role] role, I wanted to show rather than tell. I built a trusted,
> self-serve **P&C insurance semantic layer** on dbt + MetricFlow where every
> metric (loss ratio, combined ratio, claim frequency/severity) is **reconciled to
> source and gated in CI** — if a number drifts from the system of record, the
> build fails.
>
> - 4-minute walkthrough: [video link]
> - Code + write-up: https://github.com/ssbiradar3/insurance-semantic-layer
> - Production architecture (how it runs on Snowflake): see `docs/PRODUCTION.md`
>
> It runs locally with zero setup if you'd like to poke at it. Happy to walk
> through how it maps to your metrics stack.
>
> Best,
> [Your name]

### Portfolio page blurb (under the embedded video)
> **Trusted Insurance Semantic Layer** — dbt · MetricFlow · DuckDB/Snowflake.
> Self-serve P&C KPIs with reconciliation-to-source tests and a CI trust gate.
> [Repo] · [Project overview] · [Production architecture]

### Final polish checklist
- [ ] Under 5 minutes; trim dead air and long build scrolls (speed-ramp them).
- [ ] Add captions/subtitles (auto-generate in Loom/YouTube, then fix metric names
      — "loss ratio", "combined ratio", "MetricFlow", "dbt").
- [ ] First frame is a readable title or your face, not a blank terminal
      (thumbnail matters).
- [ ] Repo link + `docs/PROJECT_OVERVIEW.md` link in the description/comments.
- [ ] Watch it back once on mute — does the screen alone tell the story?
- [ ] Pin the repo on your GitHub profile so it's the first thing they see.
