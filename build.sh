#!/usr/bin/env bash
set -u

export SPECTRAL_BRIDGE_TIMESTAMP="${SPECTRAL_BRIDGE_TIMESTAMP:-2026-06-13T00:00:00+00:00}"
export SPECTRAL_BRIDGE_SOURCE_COMMIT="${SPECTRAL_BRIDGE_SOURCE_COMMIT:-release-artifact-v0.1.0}"

if [ -z "${PYTHON:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

failures=0

run_required() {
  echo "==> $*"
  "$@"
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "FAILED: $*"
    failures=$((failures + 1))
  fi
}

run_optional_python() {
  echo "==> $PYTHON $*"
  "$PYTHON" "$@"
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "FAILED: $PYTHON $*"
    failures=$((failures + 1))
  fi
}

run_required "$PYTHON" projects/montgomery-rmt/scripts/run_gate1_low_high.py \
  --blocks gate0_default,block_1e12_10k,block_1e21_10k
run_required "$PYTHON" projects/montgomery-rmt/scripts/run_gate1_sensitivity.py \
  --blocks gate0_default,block_1e12_10k,block_1e21_10k \
  --figure-prefix paper_gate1_sensitivity_
run_required "$PYTHON" projects/montgomery-rmt/scripts/export_lean_certificates.py
run_optional_python projects/montgomery-rmt/scripts/export_interval_residual_certificates.py

if command -v lake >/dev/null 2>&1; then
  run_required lake build
else
  echo "SKIP: lake not found"
fi

run_required "$PYTHON" projects/montgomery-rmt/scripts/audit_paper_package.py
run_required "$PYTHON" projects/montgomery-rmt/scripts/build_preprint_package.py
run_required "$PYTHON" projects/montgomery-rmt/scripts/audit_paper_package.py \
  --package-dir projects/montgomery-rmt/dist/preprint_package

if [ "$failures" -ne 0 ]; then
  echo "Build completed with $failures failure(s)."
  exit 1
fi

echo "Build completed successfully."
