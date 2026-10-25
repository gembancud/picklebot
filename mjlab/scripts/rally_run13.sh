#!/usr/bin/env bash
# Rally run 13 (D-153, panel round 35, 5/5): rally run 12's leg residual at +-0.3 rad, the one change against run 12.
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LegRes30-G1, from the same widened
# rally-10 model_21399 (rally-12-legres-init; leg_r does not change the checkpoint), with its optimizer, training seed
# 91, no critic warm-up, 12,288 envs, 6,400 iterations (wall cap 18 h, a guard only). Endpoint: the last checkpoint.
# Run 13's reads set PICKLEBOT_LEG_R=0.3; the parent's reads do not.
# Early kill at model_23300 (about 30 %), the parent read on the same seeds first: drill v2 0/0 (4219511), move drill
# (4219512), court drill (4219513), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s, 4219514), and the
# direction split (scripts/diag/feeder_speed_envelope.py, 4219515). Kill if (scripts/rally_check.py early-legres30):
# left + back feeder-ball contact not up on the parent; reach_deep + fast feeder-ball contact not up; any feeder family
# loses more than 5 points of contact; partner-ball legal below max(50 %, parent - 3 points); feeder-ball legal below
# parent - 2 points; court legal given contact, court contact or pair contact more than 3 points below the parent; court
# main, drill v2 or the lowest move arrival more than 5 points below the parent; court falls Wilson low > 4 % or point
# > 7.4 %.
# Endpoint: h5f_clean_eval.sh on 4219520-4219535; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4219542; crossing on 4219543 (reported); the direction split on 4219544 (reported). Success
# (pre-registered): feeder-ball legal >= 81.9 % with a court-bootstrap low > 80.1 %, partner-ball legal >= 58.2 %,
# sides within 3 points, court falls <= 4 %.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-13-legres30; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-13
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LegRes30-G1
PRUN=2026-10-25_03-30-00_rally-12-legres-init; PCK=model_21399.pt; EARLY=model_23300.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219511"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219512"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219513"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219514"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-10-pace25 $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r13.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
python scripts/diag/feeder_speed_envelope.py --checkpoint $L/2026-10-24_05-22-29_rally-10-pace25/model_21399.pt --seed 4219515 --json $R-parent-early-dir.json > /tmp/r13d.log 2>&1; echo "parent early dir: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LEG_R=0.3 python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r13e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  PICKLEBOT_LEG_R=0.3 python scripts/diag/feeder_speed_envelope.py --checkpoint $D/$EARLY --seed 4219515 --json $R-early-dir.json > /tmp/r13ed.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill): dir"; exit 2; }
  python scripts/rally_check.py early-legres30 $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=64800 bash scripts/train_run.sh $RUN $T --agent.seed 91 \
  --agent.max-iterations 6400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LEG_R=0.3 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r13 4219520
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LEG_R=0.3 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4219542 --json $R-target.json > /tmp/r13p.log 2>&1; echo "target read: $?"
PICKLEBOT_LEG_R=0.3 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4219543 --json $R-target-crossing.json > /tmp/r13p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LEG_R=0.3 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4219544 --json $R-endpoint-dir.json > /tmp/r13pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py m1 $R r13
python scripts/rally_check.py target $R r13
