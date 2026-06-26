#!/usr/bin/env bash
# Launch the interactive dashboard. Assumes the warehouse is already built
# (run `bash scripts/validate.sh` or `dbt build` first) and streamlit installed
# (`pip install -r app/requirements.txt`).
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-$(pwd)}"

if [ ! -f dev.duckdb ]; then
  echo "dev.duckdb not found — building first..."
  python scripts/generate_data.py
  dbt build
fi

echo "==> Starting dashboard at http://localhost:8501"
exec streamlit run app/streamlit_app.py
