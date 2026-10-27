#!/usr/bin/env bash
# Learning-rate sweep after the KL check (2026-10-28; the user: "lets do that then"). Rally run 14's task and reward
# unchanged; only the optimizer side changes, as one package against run 14:
#   - parent 2026-10-28_00-00-00_lrsweep-init/model_27798: run 14's endpoint with Adam's state emptied and output 30's
#     collapsed std (0.0022) raised to the floor 0.1 (scripts/fresh_init.py; the other 34 are 0.15-0.20, untouched);
#   - ScheduledPPO (picklebot_mj/rl/sched_ppo.py): std floor 0.1, linear warm-up over 50 updates to a constant peak,
#     KL guard 0.05 (the rest of an update takes no step once a mini-batch passes it); no adaptive rule.
# Smoke: 40 iterations at 1,024 envs at the highest peak (3e-4, seed 4219953): mean fell_over <= 1.5 x run 14 smoke's
# 0.106, else stop. Arms: peak 3e-5 / 1e-4 / 3e-4, 400 iterations each at 12,288 envs (seeds 4219954-4219956).
# Read: each arm's last checkpoint and the parent (run 14 model_27798) on the same seeds: drill v2 (4219960), move drill
# (4219961), court drill (4219962), pairs R4 with the contact hand-off (2,048 envs, 120 s, 4219963), the direction
# split (4219964); then rally_check.py early-lamr2 per arm (run 14's early lines, unchanged).
# Pre-registered choice: the arm with the largest left + back feeder-ball contact gain among the arms that hold the
# guard lines (partner-ball legal >= max(50 %, parent - 3), feeder-ball legal >= parent - 2, court falls Wilson low
# <= 4 % and point <= 7.4 %). It goes to a full run only if its gain is >= 2 points; otherwise the optimizer route is
# not confirmed at 400 iterations and the result goes to the user. Diagnostic seeds only; nothing here is an endpoint.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand; R=results/lrsweep
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
INIT=2026-10-28_00-00-00_lrsweep-init; PCK=model_27798.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_WARMUP=50 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
mkdir -p $L/$INIT
[ -f $L/$INIT/$PCK ] || python scripts/fresh_init.py $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt $L/$INIT/$PCK --std-min 0.1

# smoke
PICKLEBOT_LR_PEAK=3e-4 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh lrsweep-smoke $T \
  --agent.seed 4219953 --agent.max-iterations 40 --agent.resume True --agent.load-run $INIT --agent.load-checkpoint $PCK $ALG
cat artifacts/train/lrsweep-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/lrsweep-smoke.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/lrsweep-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "smoke fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}' | tee /tmp/lrs-smoke.txt
grep -q " ok$" /tmp/lrs-smoke.txt || { echo "smoke failed: sweep not run"; echo smoke-fail > artifacts/train/lrsweep.done; exit 1; }

EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219960"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219961"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219962"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219963"
read_ck() { # checkpoint, output prefix
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${spec#*:} --json $2-${spec%%:*}.json > /tmp/lrs-read.log 2>&1 || echo "READ CRASHED: $2 ${spec%%:*}"
  done
  PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4219964 --json $2-dir.json > /tmp/lrs-read.log 2>&1 || echo "READ CRASHED: $2 dir"
}
read_ck $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt $R-parent-early; echo "parent read done"

for arm in 3e-5 1e-4 3e-4; do
  RUN=lrsweep-$arm; SEED=$((4219954 + $(echo "3e-5 1e-4 3e-4" | tr ' ' '\n' | grep -n "^$arm$" | cut -d: -f1) - 1))
  PICKLEBOT_LR_PEAK=$arm PICKLEBOT_SCHED_LOG=$R-$arm-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=5400 bash scripts/train_run.sh $RUN $T \
    --agent.seed $SEED --agent.max-iterations 400 --agent.resume True --agent.load-run $INIT --agent.load-checkpoint $PCK $ALG
  echo "arm $arm (seed $SEED): $(cat artifacts/train/$RUN.exit.json)"
  D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "arm $arm read: $CK"
  read_ck $CK $R-$arm-early
  for f in v2 move court pairs dir; do cp $R-parent-early-$f.json $R-$arm-parent-early-$f.json; done
  python scripts/rally_check.py early-lamr2 $R-$arm > $R-$arm-check.txt 2>&1; echo "arm $arm early-lamr2 exit $?"; cat $R-$arm-check.txt
done
echo done > artifacts/train/lrsweep.done
