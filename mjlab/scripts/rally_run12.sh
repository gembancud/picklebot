#!/usr/bin/env bash
# Rally run 12 (D-152, round 34's pre-registered e1 rule): rally run 10's task with 12 leg-joint residuals (+-0.1 rad,
# as the right wrist) on the frozen latent controller's output, the one change against run 10.
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LegRes-G1, from rally-10-pace25/
# model_21399 widened by scripts/leg_residual_init.py (12 zero output rows), with its optimizer, training seed 90, no
# critic warm-up, 12,288 envs, 6,400 iterations (wall cap 18 h, a guard only). Endpoint: the last checkpoint.
# Run 12's reads set PICKLEBOT_LEG_R=0.1 (evaluation tasks with the leg residual); the parent's reads do not.
# Early kill at model_23300 (about 30 %), the parent read on the same seeds first: drill v2 0/0 (4219411), move drill
# (4219412), court drill (4219413), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s, 4219414). Kill if
# (scripts/rally_check.py early-legres): reach_deep + fast feeder-ball contact not up on the parent; any feeder family
# loses more than 5 points of contact; partner-ball legal below max(50 %, parent - 3 points); feeder-ball legal below
# parent - 2 points; court legal given contact, court contact or pair contact more than 3 points below the parent; court
# main, drill v2 or the lowest move arrival more than 5 points below the parent; court falls Wilson low > 4 % or point
# > 7.4 %.
# Endpoint: h5f_clean_eval.sh on 4219420-4219435 (style reported against the parent's); the M1 and target read (2,048
# envs, 120 s, read once) with the contact hand-off on 4219442; crossing on 4219443 (reported). Success
# (pre-registered): feeder-ball legal >= 81.9 % with a court-bootstrap low > 80.1 %, partner-ball legal >= 58.2 %,
# sides within 3 points, court falls <= 4 %.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-12-legres; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-12
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LegRes-G1
PRUN=2026-10-25_03-30-00_rally-12-legres-init; PCK=model_21399.pt; EARLY=model_23300.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219411"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219412"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219413"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219414"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-10-pace25 $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r12.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LEG_R=0.1 python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r12e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early-legres $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=64800 bash scripts/train_run.sh $RUN $T --agent.seed 90 \
  --agent.max-iterations 6400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LEG_R=0.1 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r12 4219420
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LEG_R=0.1 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4219442 --json $R-target.json > /tmp/r12p.log 2>&1; echo "target read: $?"
PICKLEBOT_LEG_R=0.1 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4219443 --json $R-target-crossing.json > /tmp/r12p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r12
python scripts/rally_check.py target $R r12
