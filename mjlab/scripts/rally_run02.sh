#!/usr/bin/env bash
# Rally run 2 (D-137, panel round 24): cooperative credit, the one change: placement weight 0 and partner_return 150
# (the hitter is paid when its partner legally returns its ball). The court share is corrected to 40 % of feeds
# started (0.80; a correction of run 1's hidden change, results/rally-02-share.json).
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1, parent s5h-04-pairs/model_3398, training seed 80,
# 12,288 envs (6,144 courts), 3,200 iterations, wall cap 6 h (the user's approval, D-137). Endpoint: model_6598 or the
# last checkpoint before the cap.
# Early kill at model_4400 (31 %; a crashed evaluation never kills, D-112), the parent read on the same seeds first:
#   drill v2 0/0 (4218201), move drill (4218202), court drill (4218203), pairs R4 protocol with the contact hand-off
#   (1,024 envs, 60 s, 4218204). Kill if: partner-ball legal in pairs not above the parent's Wilson upper bound; court
#   falls per episode Wilson lower > 4 % or point > 7.4 %; feeder-ball legal, court main, drill v2 or the lowest move
#   arrival > 5 points below the parent.
# Endpoint: h5f_clean_eval.sh on 4218210-4218225; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4218232; the crossing read on 4218233 (reported). Panel trigger (not a stop): a partner-ball gain under +8
# points at the endpoint.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-02-coop; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-02
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1
PRUN=2026-10-21_09-25-54_s5h-04-pairs; PCK=model_3398.pt; EARLY=model_4400.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218201"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218202"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218203"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 1024 --seconds 60 --seed 4218204"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh s5h-04-pairs $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r02.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r02e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=21600 bash scripts/train_run.sh $RUN $T --agent.seed 80 \
  --agent.max-iterations 3200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r02 4218210
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218232 --json $R-target.json > /tmp/r02p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218233 --json $R-target-crossing.json > /tmp/r02p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r02
python scripts/rally_check.py target $R r02
