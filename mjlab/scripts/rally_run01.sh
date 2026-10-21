#!/usr/bin/env bash
# Rally target run 1 (D-135, panel round 21): continued pair self-play with the contact hand-off (the one change).
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Contact-G1, parent s5h-04-pairs/model_3398, training seed 79,
# 12,288 envs (6,144 courts), 900 iterations. Endpoint: the last checkpoint (iteration 4298 or the last before the cap).
# Early kill at model_3700 (about 33 %; a crashed evaluation never kills, D-112), the parent read on the same seeds first:
#   drill v2 0/0 (4218100), move drill (4218101), court drill (4218102), pairs R4 protocol with the contact hand-off
#   (1,024 envs, 60 s, 4218103). Kill if: own-ball legal in pairs not above the parent's Wilson upper bound; court falls
#   per episode Wilson lower > 4 % or point > 7.4 %; feeder-ball legal or court main > 5 points below the parent; drill v2
#   or the lowest move arrival > 5 points below the parent.
# Endpoint: h5f_clean_eval.sh on 4218110-4218125; the target read (2,048 envs, 120 s) contact 4218132, crossing 4218133.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-01-contact; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-01
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Contact-G1
PRUN=2026-10-21_09-25-54_s5h-04-pairs; PCK=model_3398.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218100"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218101"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218102"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 1024 --seconds 60 --seed 4218103"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh s5h-04-pairs $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r01.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_3700.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/model_3700.pt ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r01e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN $T --agent.seed 79 \
  --agent.max-iterations 900 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r01 4218110
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218132 --json $R-target.json > /tmp/r01p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218133 --json $R-target-crossing.json > /tmp/r01p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py target $R r01
