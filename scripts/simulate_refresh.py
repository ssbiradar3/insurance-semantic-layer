"""
Simulate the next daily ingestion batch.

Appends a new, dated batch of policies (plus their coverages and some claims) to
the seed CSVs with a `loaded_at` one day newer than anything already loaded.
Re-running `dbt build` then processes ONLY this batch through the incremental
facts (`fct_premium`, `fct_claim`) — exactly how a nightly refresh behaves in
production. The reconciliation tests still tie gold to source because the new
rows are internally consistent (coverages sum to written premium, etc.).

Run:
    python scripts/simulate_refresh.py                # ~25 new policies
    python scripts/simulate_refresh.py --policies 50
    dbt build                                         # incremental: only the new batch

To reset to the clean initial load, just re-run `python scripts/generate_data.py`.
"""

import argparse
import csv
import os
import random
from datetime import datetime, timedelta

SEEDS = os.path.join(os.path.dirname(__file__), "..", "seeds")

LOBS = ["Property", "Casualty", "Marine", "Cyber"]
PERILS = ["Wind", "Fire", "Water", "Theft", "Liability", "Flood"]
COVERAGE_TYPES = {
    "Property": ["Building", "Contents", "BusinessInterruption"],
    "Casualty": ["GeneralLiability", "ProductsLiability"],
    "Marine": ["Hull", "Cargo"],
    "Cyber": ["DataBreach", "BusinessInterruption"],
}
# Must match scripts/generate_data.py so appended rows reconcile identically.
EXPENSE_RATE = {"Property": 0.28, "Casualty": 0.30, "Marine": 0.26, "Cyber": 0.34}


def read_csv(name):
    with open(os.path.join(SEEDS, name), newline="") as f:
        r = csv.reader(f)
        header = next(r)
        return header, list(r)


def append_rows(name, rows):
    with open(os.path.join(SEEDS, name), "a", newline="") as f:
        csv.writer(f).writerows(rows)


def write_full(name, header, rows):
    with open(os.path.join(SEEDS, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Append a simulated daily ingestion batch.")
    ap.add_argument("--policies", type=int, default=25, help="new policies to add")
    ap.add_argument("--cancellations", type=int, default=5,
                    help="existing Active policies to cancel (drives SCD2 history)")
    args = ap.parse_args()

    pol_header, pol_rows = read_csv("raw_policies.csv")
    _, cov_rows = read_csv("raw_coverages.csv")
    _, clm_rows = read_csv("raw_claims.csv")
    _, loc_rows = read_csv("raw_locations.csv")

    col = {c: i for i, c in enumerate(pol_header)}
    next_pol = max(int(r[0]) for r in pol_rows) + 1
    next_cov = max(int(r[0]) for r in cov_rows) + 1
    next_clm = max(int(r[0]) for r in clm_rows) + 1

    # Next batch = the day after the latest load already in the seeds.
    last_load = max(datetime.fromisoformat(r[col["loaded_at"]]) for r in pol_rows)
    batch_ts = last_load + timedelta(days=1)
    batch_str = batch_ts.isoformat(sep=" ")

    # Deterministic per batch date (timezone-independent), distinct from the base
    # load (seed=42), so the same batch date yields the same rows on any machine.
    random.seed(int(batch_ts.strftime("%Y%m%d")))

    locations = [(int(r[0]), r[3]) for r in loc_rows]  # (location_id, state)

    new_pol, new_cov, new_clm = [], [], []
    for _ in range(args.policies):
        pid = next_pol
        next_pol += 1
        lob = random.choice(LOBS)
        loc_id, state = random.choice(locations)
        # Mid-term policy so it earns premium against the 2026-06-30 snapshot.
        eff = batch_ts.date() - timedelta(days=random.randint(120, 420))
        exp = eff + timedelta(days=365)

        written = 0.0
        for ct in COVERAGE_TYPES[lob]:
            limit = random.choice([100_000, 250_000, 500_000, 1_000_000, 5_000_000])
            prem = round(limit * random.uniform(0.004, 0.018), 2)
            written += prem
            new_cov.append([next_cov, pid, ct, limit, prem])
            next_cov += 1
        written = round(written, 2)
        expense = round(written * EXPENSE_RATE[lob], 2)
        new_pol.append([
            pid, f"POL-{pid:05d}", lob, eff.isoformat(), exp.isoformat(),
            state, loc_id, written, expense, "Active", batch_str,
        ])

        # ~35% of new policies arrive with a claim, like the base generator.
        if random.random() < 0.35:
            for _ in range(random.randint(1, 2)):
                loss = eff + timedelta(days=random.randint(5, 300))
                report = loss + timedelta(days=random.randint(0, 30))
                paid = round(random.uniform(500, 62_000), 2)   # realistic severity (see generate_data.py)
                reserve = round(paid * random.uniform(0.0, 0.6), 2)
                cstatus = random.choices(["Closed", "Open"], weights=[75, 25])[0]
                if cstatus == "Closed":
                    reserve = 0.0
                new_clm.append([
                    next_clm, pid, loss.isoformat(), report.isoformat(),
                    cstatus, paid, reserve, random.choice(PERILS), batch_str,
                ])
                next_clm += 1

    # Status changes: cancel a few existing Active policies, stamping this batch's
    # loaded_at. The SCD2 snapshot records the Active -> Cancelled transition;
    # the incremental fact re-processes the touched rows (status is not a fact
    # column, so reconciliation is unaffected).
    active_idx = [i for i, r in enumerate(pol_rows) if r[col["status"]] == "Active"]
    cancel_idx = random.sample(active_idx, min(args.cancellations, len(active_idx)))
    for i in cancel_idx:
        pol_rows[i][col["status"]] = "Cancelled"
        pol_rows[i][col["loaded_at"]] = batch_str

    # Existing policies (some now cancelled) are rewritten; new rows appended.
    write_full("raw_policies.csv", pol_header, pol_rows + new_pol)
    append_rows("raw_coverages.csv", new_cov)
    append_rows("raw_claims.csv", new_clm)

    print(f"Appended ingestion batch  loaded_at = {batch_str}")
    print(f"  policies +{len(new_pol)}   coverages +{len(new_cov)}   "
          f"claims +{len(new_clm)}   cancellations {len(cancel_idx)}")
    print("Next: `dbt build` — incremental facts process the batch; the snapshot")
    print("records the status changes as SCD2 history.")


if __name__ == "__main__":
    main()
