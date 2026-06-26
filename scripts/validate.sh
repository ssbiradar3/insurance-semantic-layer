#!/usr/bin/env bash
# The quality gate. Run by the Claude Code hook on every edit and by CI on every
# push. Build everything, run every test (including reconciliation), then
# validate the semantic layer. Any failure exits non-zero and blocks the change.
set -euo pipefail
export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-$(pwd)}"

echo "==> dbt build (models + all tests + reconciliation)"
dbt build

echo "==> MetricFlow: validate semantic layer"
mf validate-configs

echo "==> Gate passed."
