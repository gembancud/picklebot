#!/usr/bin/env bash
# Stage 5H run 2 (D-130, panel round 18): run 1's task with 40 % of feeds one of run 1's own legal returns, mirrored
# (Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Own-G1; replay set recorded from run 1's endpoint on development
# seed 4217040). Parent run 1's endpoint s5h-01-keepalive/model_2599, training seed 74, 12,288 envs, 800 iterations.
# Endpoint: iteration 3399 or the last checkpoint before the 7000 s cap.
# Early kill at model_2900 (as run 1: 300 of 800 iterations; a crashed evaluation never kills, D-112), parent read first:
#   drill v2 0/0 (seed 4217100), move drill (4217101), court drill (4217102): drill v2 or court main > 5 points below the
#   parent, arrival < 90 %, court falls > 7.4 % per episode;
#   progress (D-130): own-ball legal, the R2 protocol at 512 envs (record 60 s on 4217103, replay 30 s on 4217104), not
#   above 10.4 % (the upper bound of run 1's endpoint R2, 10.0 % [9.5, 10.4]). Box share reported.
# Endpoint: h5f_clean_eval.sh on 4217110-4217125; R2 (record 4217130, replay 4217131) and R4 (4217132), development seeds.
# Stop rule (D-130): R2 at the endpoint below 20 % ends Stage 5H; back to the user with the interim video.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5h-02-own; L=artifacts/train/logs/picklebot_return_stand; R=results/stage5h-02
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Own-G1
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4217100"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4217101"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4217102"
bash scripts/stage2_eval.sh s5h-01-keepalive model_2599.pt $EV --json $R-parent-early-v2.json > /tmp/h01.log 2>&1; echo "parent early v2: $?"
bash scripts/stage2_eval.sh s5h-01-keepalive model_2599.pt $CV --json $R-parent-early-court.json > /tmp/h01.log 2>&1; echo "parent early court: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_2900.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV"; do
    python scripts/stage2_eval.py --checkpoint $D/model_2900.pt ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/h01e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  OA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally"
  python scripts/stage2_eval.py --checkpoint $D/model_2900.pt $OA --envs 512 --seconds 60 --seed 4217103     --record-returns $PWD/$R-early-r2-returns.pt --json $R-early-r2-record.json > /tmp/h02e.log 2>&1     || { echo "EARLY EVALUATION CRASHED (no kill): r2 record"; exit 2; }
  python scripts/stage2_eval.py --checkpoint $D/model_2900.pt $OA --envs 512 --seconds 30 --seed 4217104     --replay-file $PWD/$R-early-r2-returns.pt --json $R-early-r2.json > /tmp/h02e.log 2>&1     || { echo "EARLY EVALUATION CRASHED (no kill): r2 replay"; exit 2; }
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
      f"{wilson(b1, n1)} (report); flight {pc['contact_diagnostics']['flight_time_mean_s']} -> {ec['contact_diagnostics']['flight_time_mean_s']} s; "
      f"ball out {pc['contact_diagnostics']['ball_speed_out_mean']} -> {ec['contact_diagnostics']['ball_speed_out_mean']} m/s")
r2 = ld("early-r2")
print(f"early: own-ball legal (R2 protocol, 512 envs) {r2['legal_return_rate']:.4f} {r2['legal_return_ci95']} of {r2['episodes']} (kill if <= 0.104)")
ok = p1 >= p0 - 0.05 and c1 >= c0 - 0.05 and arr >= 0.90 and f1 <= 0.074 and r2["legal_return_rate"] > 0.104
sys.exit(0 if ok else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN $T --agent.seed 74 \
  --agent.max-iterations 800 --agent.resume True --agent.load-run 2026-10-21_00-50-33_s5h-01-keepalive --agent.load-checkpoint model_2599.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) s5h02 4217110
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 1024 --seconds 90 --rally --seed 4217130 \
  --record-returns $PWD/$R-r2-returns.pt --json $R-r2-record.json > /tmp/h01r.log 2>&1; echo "R2 record: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 1024 --seconds 40 --rally --seed 4217131 \
  --replay-file $PWD/$R-r2-returns.pt --json $R-r2.json > /tmp/h01r.log 2>&1; echo "R2 replay: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --envs 2048 --seconds 120 --rally --pairs --seed 4217132 \
  --json $R-r4.json > /tmp/h01p.log 2>&1; echo "R4 pairs: $?"
python - "$R" <<'PY'
import json, sys
R = sys.argv[1]
r2 = json.load(open(R + "-r2.json")); p = json.load(open(R + "-r4.json"))["pairs"]
print(f"R2 (dev seeds): legal {r2['legal_return_rate']:.4f} {r2['legal_return_ci95']} of {r2['episodes']}; falls per shot {r2['falls'] / max(r2['episodes'], 1):.4f}")
print(f"R4 (dev seeds): rallies {p['rallies']}; P(4+) {p['p_len_ge_4']}; mean {p['mean_len']}; own-ball {p['sides_own_ball']}")
PY
