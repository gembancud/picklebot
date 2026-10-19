#!/usr/bin/env bash
# Stage 5F evaluation of one fixed endpoint on the clean-simulator instrument (D-113). Development seeds S..S+15 only.
# Usage: h5f_clean_eval.sh RUN CKFILE TAG SEED [full]   -> results/stage5f-TAG-*.json + summary
# Gate items (D-113; bars unchanged from D-101):
#   v2      drill v2, grid cell 0/0 (no delay), ball noise on, noisy planner spot, 1024 envs, 90 s rallies (seed S):
#           per-shot p, group floors on Wilson lower bounds, P(rally >= 5 / 10)
#   then the Stage 5C battery, clean (h5c_eval.sh on seeds S+10..S+15): court main and falls, move arrival, Stage 5B
#   drill, recovery, rally, style (old and new reference)
# Reported, never gating (D-113):
#   d101    drill v2 on the frozen D-101 mixed-latency condition (the task's sim-to-real), 1024 envs, 90 s (seed S+3)
#   v2-c10  drill v2 at cell 0/10 and v2-b40c20 at 40/20, 512 envs, 40 s (seed S+4)
#   move-c10  the move drill at command 10 ms, 2048 envs, 24 s (seed S+5)
#   "full" (run 0 and the final) adds drill v2 at 0/0 with the clean planner spot and with no spot (seeds S+1, S+2).
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; MODE=${5:-run}; R=results/stage5f-$TAG; FAIL=0; MARK=$(mktemp)
check() { if [ $1 -ne 0 ] || [ ! "$2" -nt "$MARK" ]; then echo "EVAL JOB FAILED: $2 (exit $1)"; FAIL=1; fi; }
# PICKLEBOT_RESUME=1: keep a job's existing output (an interrupted evaluation of the same endpoint and seeds).
skip() { [ "${PICKLEBOT_RESUME:-0}" = 1 ] && [ -s "$1" ] && { echo "kept $1"; return 0; }; return 1; }
TV2=Picklebot-Latent-Court-V2-Res-G1; TC=Picklebot-Latent-Court-Res-G1; T5B=Picklebot-Latent-Drill3-Prior5-Res-G1
E="bash scripts/stage2_eval.sh $RUN $CK"
V="--task $TV2 --envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally"
skip $R-v2.json || { $E $V --planner noisy --grid 0 0 --seed $S --json $R-v2.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-v2.json; }
if [ "$MODE" = full ]; then
  skip $R-v2-cleanspot.json || { $E $V --planner clean --grid 0 0 --seed $((S+1)) --json $R-v2-cleanspot.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-v2-cleanspot.json; }
  skip $R-v2-nospot.json || { $E $V --planner off --grid 0 0 --seed $((S+2)) --json $R-v2-nospot.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-v2-nospot.json; }
fi
skip $R-d101.json || { $E $V --planner noisy --seed $((S+3)) --json $R-d101.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-d101.json; }
W="--task $TV2 --envs 512 --seconds 40 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy"
skip $R-v2-c10.json || { $E $W --grid 0 10 --seed $((S+4)) --json $R-v2-c10.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-v2-c10.json; }
skip $R-v2-b40c20.json || { $E $W --grid 40 20 --seed $((S+4)) --json $R-v2-b40c20.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-v2-b40c20.json; }
M="--task $TC --envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint"
skip $R-move-c10.json || { $E $M --grid 0 10 --seed $((S+5)) --json $R-move-c10.json > /tmp/h5fc_$TAG.log 2>&1; check $? $R-move-c10.json; }
# The "s5f-" prefix keeps earlier stages' results/stage5c-TAG-* files (e.g. Stage 5E run 0's run0-s5d01) from being overwritten.
bash scripts/h5c_eval.sh $RUN $CK s5f-$TAG-5c $((S+10)) $TC $T5B || FAIL=1
[ $FAIL -eq 0 ] || echo "WARNING: at least one evaluation job failed; the summary below may be incomplete"
~/envs/picklebot-mj/bin/python scripts/h5f_clean_summary.py $TAG --json $R-summary.json
exit $FAIL
