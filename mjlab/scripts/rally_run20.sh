#!/usr/bin/env bash
# Rally run 20 (D-161, panel round 42: 5/5 for holding the feeder ball's share of play; a rally cap 4/5 (motion: a
# fraction of feeder-only courts); N = 5 by the tie rule, experiment design's value). Run 19's design with one change:
# the training task caps a pair rally at 5 shots (pair_rally_cap 5: the 5th shot is not handed over, it lands and is
# judged, then a feeder ball starts the next rally), so the feeder ball's share of play stays >= 1/5 (run 19's fell
# 21.5 -> 13.3 % and its feeder-ball legal fell 3.6 points). Parent run 18b model_29000, as run 19: same rate (1e-4, no
# warm-up), Adam state, length (4,000 iterations, cooldown over the last 20 %) and early-check iteration, so run 19's
# model_30200 read is the matched no-cap arm. Training seed 98, smoke seed 99. Reads unchanged (the read task has no cap).
# Smoke: falls (fell_over mean <= 0.159), every std output with a gradient, and the manipulation check: the training
# feeder share of balls started (PICKLEBOT_PAIR_LOG) in the smoke's second half within 0.20-0.35, else the run does not
# start (an implementation error, not a kill). The training share is logged for the whole run (results/rally-20-train-share.jsonl).
# Reads (PICKLEBOT_LAM_R=2): the parent model_29000 re-read first, then model_30200, same seeds: drill v2 4220029, move
# 4220030, court 4220031, pairs (contact hand-off, 2,048 envs, 120 s) 4220032, direction split 4220033.
# Kill (rally_check.py early-r19, unchanged): P(5+) open up < 1.0 point; partner legal below parent - 1.5; feeder legal
# below parent - 1.0 or run 14 - 2; any feeder family's contact more than 5 below run 14 (cross_forehand: 3 below
# model_29000); left + back more than 5 below run 14; run 18b's court / drill / move / falls lines. Exit 2 is not a kill.
# Reported beside it: run 19's model_30200 read (the no-cap arm), feeder-ball falls per feeder ball (motion; parent
# 1.44 %), the shot-position end rates, the feeder share in the read, feeder n and its binomial SE.
# Endpoint (read once): h5f_clean_eval.sh on 4220034-4220049; the target / M1 read with the contact hand-off 4220050;
# crossing 4220051 (reported); the direction split 4220052. Success: rally_check.py r19-gate unchanged; m1, target.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-20-cap5; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-20
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Cap5-G1
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt; EARLY=model_30200.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_LR_COOLDOWN=0.2 PICKLEBOT_LR_FINAL=1e-5
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }

# smoke
PICKLEBOT_LR_TOTAL=40 PICKLEBOT_PAIR_LOG=$R-smoke-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=48 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
  --agent.seed 99 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
cat artifacts/train/$RUN-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/$RUN-smoke.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/$RUN-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "smoke fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}' | tee /tmp/r20-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $L/*_$RUN-smoke/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/r20-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - $R-smoke-share.jsonl <<'PY' | tee -a /tmp/r20-smoke.txt
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
a, b = rows[len(rows) // 2], rows[-1]  # the second half of the smoke: past the start, where every court opens with a feeder ball
f, h = b["feeder"] - a["feeder"], b["handoffs"] - a["handoffs"]
s = f / max(f + h, 1)
print(f"smoke feeder share of balls started {s:.3f} ({f} feeder, {h} hand-offs; manipulation check 0.20-0.35)", "ok" if 0.20 <= s <= 0.35 else "STOP")
PY
[ "$(grep -c " ok$" /tmp/r20-smoke.txt)" = 3 ] || { echo "smoke failed: run not started"; exit 1; }

EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4220029"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4220030"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220031"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220032"
read_ck() { # checkpoint, output prefix, log tag; returns 2 on a crash
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${spec#*:} --json $2-${spec%%:*}.json > /tmp/r20-$3.log 2>&1 \
      || { echo "READ CRASHED: $2 ${spec%%:*}"; tail -3 /tmp/r20-$3.log; return 2; }
  done
  PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220033 --json $2-dir.json > /tmp/r20-$3.log 2>&1 \
    || { echo "READ CRASHED: $2 dir"; tail -3 /tmp/r20-$3.log; return 2; }
}
read_ck $L/$PRUN/$PCK $R-parent-early p || exit 1; echo "parent read done"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  read_ck $D/$EARLY $R-early e || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/rally_check.py early-r19 $R; rc=$?
  case $rc in
    0) echo "early check: pass";;
    1) echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN";;
    *) echo "early check: CHECK CRASHED (exit $rc), no kill";;
  esac
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_LR_TOTAL=4000 PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=50400 bash scripts/train_run.sh $RUN $T \
  --agent.seed 98 --agent.max-iterations 4000 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; echo killed > artifacts/train/$RUN.done; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r20 4220034
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4220050 --json $R-target.json > /tmp/r20p.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4220051 --json $R-target-crossing.json > /tmp/r20p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220052 --json $R-endpoint-dir.json > /tmp/r20pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py r19-gate $R r20
python scripts/rally_check.py m1 $R r20
python scripts/rally_check.py target $R r20
echo done > artifacts/train/$RUN.done
