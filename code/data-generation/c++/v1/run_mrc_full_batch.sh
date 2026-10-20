#!/usr/bin/env bash
# Batch exact m(r,c,o,a) table generation for r=1..24, c=r..40.
# Usage: ./run_mrc_full_batch.sh [OUTPUT_DIRECTORY] [extra mrc_batch_generate.py arguments...]
set -euo pipefail
cd -- "$(dirname -- "$0")"
OUT_DIR="${1:-../data}"
if [ "$#" -gt 0 ]; then shift; fi
exec python3 -u mrc_batch_generate.py \
  --r-min 1 --r-max 24 --c-max 40 \
  --out-dir "$OUT_DIR" \
  "$@"
