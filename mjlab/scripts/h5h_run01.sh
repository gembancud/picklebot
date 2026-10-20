#!/usr/bin/env bash
# Stage 5H run 1 (D-129, panel round 17): back to the Stage 5F executor. Run 4's recipe exactly (court-feed mix 0.4,
# training seed 73, 12,288 envs, 800 iterations, parent s5d-01-rally/model_1800) with one reward change: the pace term
# return_shaping replaced, at the same weight and place, by keep_alive_landing (planner.keep_alive_score of the real
# legal landing: the box x 4.7-5.7, |y| <= 1 and flight 1.3-1.5 s, linear tails of 1 m and 0.5 s). Run 4 is the A/B.
# Endpoint: iteration 2600 or the last checkpoint before the 7000 s cap.
# Early kill at model_2100 (as run 4; a crashed evaluation never kills, D-112), parent read on the same seeds first:
#   drill v2 0/0, 256 envs, 30 s, seed 4217000: > 5 points below the parent;
#   move drill clean, 256 envs, 20 s, seed 4217001: arrival < 90 % in any direction;
#   court drill clean, 256 envs, 24 s, seed 4217002: court main > 5 points below the parent; court falls > 7.4 % per
#   episode; the keep-alive box share of legal landings not above the parent's (D-129's progress line).
# Endpoint: h5f_clean_eval.sh (D-113 stage rules) on seeds 4217010-4217025; R2 own-ball (record 4217030, replay 4217031)
# and R4 pairs (4217032) on development seeds, report only (the readiness seeds stay for the readiness read).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5h-01-keepalive; L=artifacts/train/logs/picklebot_return_stand; R=results/stage5h-01
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-G1
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4217000"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4217001"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4217002"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $EV --json $R-parent-early-v2.json > /tmp/h01.log 2>&1; echo "parent early v2: $?"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $CV --json $R-parent-early-court.json > /tmp/h01.log 2>&1; echo "parent early court: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_2100.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV"; do
    python scripts/stage2_eval.py --checkpoint $D/model_2100.pt ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/h01e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, math, sys
R = sys.argv[1]
ld = lambda k: json.load(open(f"{R}-{k}.json"))
def wilson(k, n, z=1.96):
    if n == 0: return [0.0, 0.0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]
p0, p1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
pc, ec = ld("parent-early-court"), ld("early-court")
c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
f1 = ec["robot_fall_rate_per_episode"]
box = lambda d: (d["contact_diagnostics"]["landings_in_keep_alive_box"], d["contact_diagnostics"]["legal_landings"])
(b0, n0), (b1, n1) = box(pc), box(ec)
arr = min(s["arrival_rate"] for s in ld("early-move")["move_drill"]["sectors"] if s["sector"] < 8 and s.get("arrival_rate") is not None)
print(f"early: drill v2 p {p0} -> {p1} ({100 * (p1 - p0):+.1f}; kill below -5); court main {c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5) "
      f"{ec['legal_return_ci95']}; court falls/episode {f1} (kill > 0.074); move arrival min {arr} (kill below 0.90)")
print(f"early: keep-alive box share of legal landings {b0}/{n0} = {b0 / max(n0, 1):.4f} {wilson(b0, n0)} -> {b1}/{n1} = {b1 / max(n1, 1):.4f} "
      f"{wilson(b1, n1)} (kill if not above); flight {pc['contact_diagnostics']['flight_time_mean_s']} -> {ec['contact_diagnostics']['flight_time_mean_s']} s; "
      f"ball out {pc['contact_diagnostics']['ball_speed_out_mean']} -> {ec['contact_diagnostics']['ball_speed_out_mean']} m/s")
ok = p1 >= p0 - 0.05 and c1 >= c0 - 0.05 and arr >= 0.90 and f1 <= 0.074 and b1 / max(n1, 1) > b0 / max(n0, 1)
sys.exit(0 if ok else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN $T --agent.seed 73 \
  --agent.max-iterations 800 --agent.resume True --agent.load-run 2026-10-17_06-13-47_s5d-01-rally --agent.load-checkpoint model_1800.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) s5h01 4217010
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 1024 --seconds 90 --rally --seed 4217030 \
  --record-returns $PWD/$R-r2-returns.pt --json $R-r2-record.json > /tmp/h01r.log 2>&1; echo "R2 record: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 1024 --seconds 40 --rally --seed 4217031 \
  --replay-file $PWD/$R-r2-returns.pt --json $R-r2.json > /tmp/h01r.log 2>&1; echo "R2 replay: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 2048 --seconds 120 --rally --pairs --seed 4217032 \
  --json $R-r4.json > /tmp/h01p.log 2>&1; echo "R4 pairs: $?"
python - "$R" <<'PY'
import json, sys
R = sys.argv[1]
r2 = json.load(open(R + "-r2.json")); p = json.load(open(R + "-r4.json"))["pairs"]
print(f"R2 (dev seeds): legal {r2['legal_return_rate']:.4f} {r2['legal_return_ci95']} of {r2['episodes']}; falls per shot {r2['falls'] / max(r2['episodes'], 1):.4f}")
print(f"R4 (dev seeds): rallies {p['rallies']}; P(4+) {p['p_len_ge_4']}; mean {p['mean_len']}; own-ball {p['sides_own_ball']}")
PY
