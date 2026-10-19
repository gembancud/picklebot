#!/usr/bin/env bash
# Stage 5F run 0 on the clean-simulator instrument (D-113): the start point and both comparators, before any training run.
# Re-run with PICKLEBOT_RESUME=1 after the 21:27 stop (tag collision fixed): finished jobs are kept.
# Seeds from the run-0 block (seed ledger): Stage 5D run 1 4210300-15, run 22 4210320-35, Stage 5E run 3 4210340-55.
set -uo pipefail
cd "$(dirname "$0")/.."
PICKLEBOT_RESUME=1 bash scripts/h5f_clean_eval.sh s5d-01-rally model_1800.pt run0-s5d01 4210300 full; echo "run0 s5d01: $?"
PICKLEBOT_RESUME=1 bash scripts/h5f_clean_eval.sh s5c-22-res-rally model_900.pt run0-s5c22 4210320 full; echo "run0 s5c22: $?"
PICKLEBOT_RESUME=1 bash scripts/h5f_clean_eval.sh s5e-03-v2-mixlat model_2700.pt run0-s5e03 4210340 full; echo "run0 s5e03: $?"
