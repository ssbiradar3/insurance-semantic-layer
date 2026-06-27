"""
Generate synthetic Property & Casualty insurance data plus a stand-in vendor feed.

Outputs deterministic CSV seeds into ../seeds so `dbt seed` can load them.
The vendor flood file simulates a commercial third-party enrichment (the kind of
feed a specialty insurer buys from Verisk / Moody's RMS / CoreLogic), built here
from free, openly modelled values so the repo stays fully reproducible.

Run:  python scripts/generate_data.py
"""

import csv
import os
import random
from datetime import date, timedelta

random.seed(42)  # deterministic: same data every run, so reconciliation is stable

SEEDS = os.path.join(os.path.dirname(__file__), "..", "seeds")
os.makedirs(SEEDS, exist_ok=True)

STATES = ["CA", "TX", "FL", "NY", "WA", "IL", "GA", "CO"]
LOBS = ["Property", "Casualty", "Marine", "Cyber"]
PERILS = ["Wind", "Fire", "Water", "Theft", "Liability", "Flood"]
FLOOD_ZONES = ["X", "A", "AE", "VE"]  # FEMA-style zone codes
COVERAGE_TYPES = {
    "Property": ["Building", "Contents", "BusinessInterruption"],
    "Casualty": ["GeneralLiability", "ProductsLiability"],
    "Marine": ["Hull", "Cargo"],
    "Cyber": ["DataBreach", "BusinessInterruption"],
}

# Underwriting expense as a fraction of written premium, by line of business
# (commission + general expense). Applied deterministically with NO random draw,
# so existing policy / coverage / claim data stays byte-identical. This is the
# source basis for the expense_ratio and combined_ratio metrics.
EXPENSE_RATE = {"Property": 0.28, "Casualty": 0.30, "Marine": 0.26, "Cyber": 0.34}

# Ingestion timestamp stamped on every row of the initial load. Real warehouses
# carry a "loaded_at" so downstream models can process only new rows. The
# incremental facts (fct_premium, fct_claim) use it as their watermark, and
# scripts/simulate_refresh.py appends later batches with a newer timestamp.
INITIAL_LOAD_TS = "2026-06-01 00:00:00"

N_LOCATIONS = 60
N_POLICIES = 600


def write_csv(name, header, rows):
    path = os.path.join(SEEDS, name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name:28} {len(rows):>5} rows")


# ---------------------------------------------------------------- locations
locations = []
for loc_id in range(1, N_LOCATIONS + 1):
    state = random.choice(STATES)
    locations.append([
        loc_id,
        f"{random.randint(100, 9999)} Main St",
        f"City_{loc_id}",
        state,
        f"{random.randint(10000, 99999):05d}",
        round(random.uniform(25.0, 48.0), 4),
        round(random.uniform(-124.0, -71.0), 4),
    ])
write_csv("raw_locations.csv",
          ["location_id", "address", "city", "state", "zip", "latitude", "longitude"],
          locations)

# ------------------------------------------------------ vendor flood feed
# One row per location: the third-party enrichment we will join onto exposures.
vendor_flood = []
for loc in locations:
    loc_id = loc[0]
    zone = random.choices(FLOOD_ZONES, weights=[60, 20, 15, 5])[0]
    score = {"X": (1, 20), "A": (40, 60), "AE": (55, 75), "VE": (80, 99)}[zone]
    vendor_flood.append([
        loc_id,
        zone,
        random.randint(*score),
        "FEMA_NFHL_v2026",  # source tag, as a real vendor extract would carry
    ])
write_csv("raw_vendor_flood.csv",
          ["location_id", "flood_zone", "flood_risk_score", "vendor_source"],
          vendor_flood)

# ---------------------------------------------------------------- policies
policies = []
coverages = []
cov_id = 1
start_window = date(2023, 1, 1)
for pol_id in range(1, N_POLICIES + 1):
    lob = random.choice(LOBS)
    loc = random.choice(locations)
    eff = start_window + timedelta(days=random.randint(0, 900))
    exp = eff + timedelta(days=365)
    # build premium from coverage parts so it reconciles exactly
    parts = COVERAGE_TYPES[lob]
    pol_written = 0
    pol_cov_rows = []
    for ct in parts:
        limit = random.choice([100_000, 250_000, 500_000, 1_000_000, 5_000_000])
        prem = round(limit * random.uniform(0.004, 0.018), 2)
        pol_written += prem
        pol_cov_rows.append([cov_id, pol_id, ct, limit, prem])
        cov_id += 1
    pol_written = round(pol_written, 2)
    underwriting_expense = round(pol_written * EXPENSE_RATE[lob], 2)
    status = random.choices(["Active", "Cancelled", "Expired"], weights=[70, 8, 22])[0]
    policies.append([
        pol_id, f"POL-{pol_id:05d}", lob, eff.isoformat(), exp.isoformat(),
        loc[3], loc[0], pol_written, underwriting_expense, status, INITIAL_LOAD_TS,
    ])
    coverages.extend(pol_cov_rows)

write_csv("raw_policies.csv",
          ["policy_id", "policy_number", "line_of_business", "effective_date",
           "expiration_date", "state", "location_id", "written_premium",
           "underwriting_expense", "status", "loaded_at"],
          policies)
write_csv("raw_coverages.csv",
          ["coverage_id", "policy_id", "coverage_type", "coverage_limit",
           "coverage_premium"],
          coverages)

# ---------------------------------------------------------------- claims
claims = []
claim_id = 1
for pol in policies:
    pol_id = pol[0]
    eff = date.fromisoformat(pol[3])
    # ~35% of policies have at least one claim
    if random.random() < 0.35:
        for _ in range(random.randint(1, 3)):
            loss = eff + timedelta(days=random.randint(5, 360))
            report = loss + timedelta(days=random.randint(0, 45))
            paid = round(random.uniform(500, 250_000), 2)
            reserve = round(paid * random.uniform(0.0, 0.6), 2)
            cstatus = random.choices(["Closed", "Open"], weights=[75, 25])[0]
            if cstatus == "Closed":
                reserve = 0.0
            claims.append([
                claim_id, pol_id, loss.isoformat(), report.isoformat(),
                cstatus, paid, reserve, random.choice(PERILS), INITIAL_LOAD_TS,
            ])
            claim_id += 1

write_csv("raw_claims.csv",
          ["claim_id", "policy_id", "loss_date", "report_date", "claim_status",
           "paid_loss", "case_reserve", "peril", "loaded_at"],
          claims)

print("\nDone. Seed totals:")
print(f"  policies={len(policies)} coverages={len(coverages)} "
      f"claims={len(claims)} locations={len(locations)}")
