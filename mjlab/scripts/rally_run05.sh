#!/usr/bin/env bash
# Rally run 5 (D-141, panel round 27, 5/5): rally run 4's task with a court-feed family mix weighted toward the weak
# feeder families (COURT_MIX_WEAK: backhand, reach_backhand, cross_backhand, fast 2.0; drop, low, reach_deep 1.5;
# short, high, reach_forehand 0.75; the rest 1.0). Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-
# Weak-G1, from rally-04-moves/model_12100 with its optimizer, training seed 83, no critic warm-up, 12,288 envs, 3,200
# iterations, wall cap 6 h. Endpoint: the last checkpoint before the cap.
# Early kill at model_13000 (about 30 %), the parent read on the same seeds first: drill v2 0/0 (4218501), move drill
# (4218502), court drill (4218503), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s for the per-family
# guard, 4218504). Kill if (scripts/rally_check.py early-weak): partner-ball legal below max(50 %, parent - 3 points);
# feeder-ball legal (even mix) below parent - 2 points; short, high or reach_forehand (down-weighted) more than 5 points
# below the parent; court main, drill v2 or the lowest move arrival more than 5 points below the parent; court falls
# Wilson low > 4 % or point > 7.4 %. No early stop for futility.
# Endpoint: h5f_clean_eval.sh on 4218510-4218525; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4218532; crossing on 4218533 (reported). Panel trigger: a feeder-ball gain under +3 points.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-05-weak; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-05
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-G1
PRUN=2026-10-22_15-20-48_rally-04-moves; PCK=model_12100.pt; EARLY=model_13000.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218501"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218502"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218503"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4218504"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-04-moves $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r05.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r05e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early-weak $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=21600 bash scripts/train_run.sh $RUN $T --agent.seed 83 \
  --agent.max-iterations 3200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r05 4218510
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218532 --json $R-target.json > /tmp/r05p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218533 --json $R-target-crossing.json > /tmp/r05p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r05
python scripts/rally_check.py target $R r05
