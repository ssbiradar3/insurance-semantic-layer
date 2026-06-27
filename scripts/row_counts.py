"""Print fact-table row counts and ingestion batches from the local DuckDB.

Used by the scheduled-refresh workflow to make the incremental refresh visible
(how many rows exist, and how many distinct loaded_at batches landed).
"""

import duckdb

con = duckdb.connect("dev.duckdb")
for tbl in ("fct_premium", "fct_claim"):
    n = con.sql(f"select count(*) from main_marts.{tbl}").fetchone()[0]
    batches = con.sql(
        f"select count(distinct loaded_at) from main_marts.{tbl}"
    ).fetchone()[0]
    latest = con.sql(f"select max(loaded_at) from main_marts.{tbl}").fetchone()[0]
    print(f"  {tbl:12} rows={n:<6} batches={batches}  latest_loaded_at={latest}")
