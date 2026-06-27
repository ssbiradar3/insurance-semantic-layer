#!/usr/bin/env bash
# Generate and serve the data-observability report: an interactive site with the
# full lineage DAG (sources -> staging -> marts -> snapshot), every model and
# column description, and the latest test results. This is the DuckDB-compatible
# stand-in for an Elementary report (Elementary does not support DuckDB).
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-$(pwd)}"

dbt docs generate          # builds target/catalog.json + manifest with test results
echo "==> Serving lineage + catalog at http://localhost:8080  (Ctrl-C to stop)"
exec dbt docs serve --port 8080
