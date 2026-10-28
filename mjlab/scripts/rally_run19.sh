#!/usr/bin/env bash
# Rally run 19 (D-160, panel round 41: A by RL, experiment design and architecture; motion E then B, coach G). Run 18b
# continued: its parent is run 18b model_29000, a checkpoint of a killed run. Run 18b stays killed (no endpoint is read
# or claimed for it); its kill reason (cross_forehand contact -5.3) is carried forward as an accepted, named regression.
# No change to the task or the optimizer: run 14's task, ScheduledPPO at 1e-4 with model_29000's Adam state, no
# warm-up (an exact continuation of 18b's constant phase), cooldown over the last 20 % (updates 3,200-4,000), KL guard
# 0.05, std floor 0.1. The variable is training time. Training seed 96 (TRAIN_SEEDS again), smoke seed 97, 12,288 envs,
# 4,000 iterations (wall cap 14 h, a guard only). Endpoint: the last checkpoint (model_33000).
# Reads (PICKLEBOT_LAM_R=2; the interface guard checks it against 18b's params/env.yaml): the parent model_29000 first,
# then model_30200 (30 %), same seeds: drill v2 4220002, move 4220003, court 4220004, pairs (contact hand-off, 2,048
# envs, 120 s) 4220005, direction split 4220006. P(5+) is read with open rallies counted (D-160).
# Kill (rally_check.py early-r19; experiment design's lines from measured read noise): P(5+) up < 1.0 point; partner-ball
# legal below parent - 1.5; feeder-ball legal below parent - 1.0 or run 14 - 2; any feeder family's contact more than 5
# below run 14 (cross_forehand: more than 3 below model_29000); left + back feeder contact more than 5 below run 14;
# run 18b's court legal given contact / court contact / pair contact (-3), court main / drill v2 / move arrival (-5) and
# falls (Wilson low > 4 % or point > 7.4 %) lines. Exit 2 from the check (a crash) is not a kill.
# Endpoint (read once): h5f_clean_eval.sh on 4220010-4220025; the target / M1 read with the contact hand-off 4220026;
# crossing 4220027 (reported); the direction split 4220028. Success (rally_check.py r19-gate): P(5+) open >= parent + 2
# points with a Wilson low above the parent's point; partner >= parent - 1.5; feeder >= run 14 - 2; sides within 3;
# falls <= 4 %; the cumulative guards.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-19-cont; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-19
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt; EARLY=model_30200.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_LR_COOLDOWN=0.2 PICKLEBOT_LR_FINAL=1e-5
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }

# smoke
PICKLEBOT_LR_TOTAL=40 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
  --agent.seed 97 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
cat artifacts/train/$RUN-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/$RUN-smoke.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/$RUN-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "smoke fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}' | tee /tmp/r19-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $L/*_$RUN-smoke/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/r19-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
[ "$(grep -c " ok$" /tmp/r19-smoke.txt)" = 2 ] || { echo "smoke failed: run not started"; exit 1; }

EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4220002"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4220003"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220004"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220005"
read_ck() { # checkpoint, output prefix, log tag; returns 2 on a crash
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${spec#*:} --json $2-${spec%%:*}.json > /tmp/r19-$3.log 2>&1 \
      || { echo "READ CRASHED: $2 ${spec%%:*}"; tail -3 /tmp/r19-$3.log; return 2; }
  done
  PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220006 --json $2-dir.json > /tmp/r19-$3.log 2>&1 \
    || { echo "READ CRASHED: $2 dir"; tail -3 /tmp/r19-$3.log; return 2; }
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
PICKLEBOT_LR_TOTAL=4000 PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=50400 bash scripts/train_run.sh $RUN $T \
  --agent.seed 96 --agent.max-iterations 4000 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; echo killed > artifacts/train/$RUN.done; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r19 4220010
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4220026 --json $R-target.json > /tmp/r19p.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4220027 --json $R-target-crossing.json > /tmp/r19p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220028 --json $R-endpoint-dir.json > /tmp/r19pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py r19-gate $R r19
python scripts/rally_check.py m1 $R r19
python scripts/rally_check.py target $R r19
echo done > artifacts/train/$RUN.done
