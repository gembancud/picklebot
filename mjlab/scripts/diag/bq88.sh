#!/usr/bin/env bash
# D-225 (panel round 88: (iii) 3 of 5; forms differed, least new code: architecture's). Read only: what makes the first
# hand-off hard? C = rally-d1s3lr3 model_32598 (d1 base, lam_r 2), mean actions, standard pairs reads on dev 4220378 and
# 4220379 (2,048 envs, 120 s). launch_state.ball_by_class: legal returns of feeder balls vs handed balls (keep_alive,
# |velocity|, |spin| at contact) and the receiver's speed at a hand-off by class (logging only).
#   Validity per read and pooled: H1-RECON (d1_rule.h1_recon, unchanged) and >= 200 per class (d1_rule.ball_route).
#   Route (d1_rule.ball_route): BALL-STATE -> (ii) keep_alive x2 on the feeder-ball return (its own entry);
#   RECEIVER -> panel; NEITHER -> panel. Reported: h1_route on the pool, handoff_stale and its early part by bin.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/bq88; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/bq88.done; exit 0; }
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
echo "D-225: first hand-off ball quality on C; reads dev 4220378, 4220379" | tee $R-summary.txt
for s in 4220378 4220379; do
  [ -s $R-read-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --json $R-read-$s.json > $R-read-$s.log 2>&1
  python - "$s" <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
s = sys.argv[1]
f = f"results/bq88-read-{s}.json"
q = json.load(open(f))
ok, line = dr.h1_recon([f])
has = "ball_by_class" in q.get("launch_state", {})
print(f"{s} " + line + f"; ball_by_class present {has}; handoff_stale {q['pairs'].get('handoff_stale')} early by bin {q['pairs'].get('handoff_stale_early_by_d')}")
PY
  grep -q -- "^$s .*-> VALID; ball_by_class present True" $R-summary.txt || stop "INVALID (read $s)"
done
python - <<'PY' | tee -a $R-summary.txt
import sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
f = ["results/bq88-read-4220378.json", "results/bq88-read-4220379.json"]
ok, line = dr.h1_recon(f)
print("pooled " + line)
v, lines = dr.ball_route(f)
for x in lines:
    print(x)
hv, hl = dr.h1_route(f)
print(f"(reported) h1_route on this pool: {hv}; " + hl[0])
print(f"RESULT {v if ok else 'INVALID'}")
PY
v=$(grep "^RESULT" $R-summary.txt | tail -1 | cut -d' ' -f2)
stop "$v"
