#!/usr/bin/env bash
# Rally run 4 (D-140, panel round 26; 5/5 for "the fix only"): rally run 3's task with ball-free drill episodes respected
# in pair mode (pair_respect_moves: a robot in a move-to-spot or swing episode gets no ball, a return to it ends the rally
# once it lands, the feeder ball goes to the free side). Before, 38 % of all balls went to robots in move episodes
# (results/rally-03-movebug.json). The court share stays 0.80 (3/4: no second knob).
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-G1, from rally-03-coop-cont/model_9200 with its
# optimizer, training seed 82, no critic warm-up, 12,288 envs, 3,200 iterations, wall cap 6 h. Endpoint: the last
# checkpoint before the cap.
# Early kill at model_10100 (about 30 %), D-139's lines, the parent read on the same seeds first: drill v2 0/0
# (4218401), move drill (4218402), court drill (4218403), pairs R4 protocol with the contact hand-off (1,024 envs, 60 s,
# 4218404). Kill if (scripts/rally_check.py early-continuation): partner-ball legal below the parent's bootstrap low
# minus 2 points; feeder-ball legal more than 3 points below the parent; court main, drill v2 or the lowest move arrival
# more than 5 points below the parent; court falls Wilson low > 4 % or point > 7.4 %. No early stop for futility.
# Endpoint: h5f_clean_eval.sh on 4218410-4218425; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4218432; crossing on 4218433 (reported). Panel trigger: a feeder-ball gain under +3 points.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-04-moves; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-04
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-G1
PRUN=2026-10-22_07-16-05_rally-03-coop-cont; PCK=model_9200.pt; EARLY=model_10100.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218401"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218402"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218403"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 1024 --seconds 60 --seed 4218404"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-03-coop-cont $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r04.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r04e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early-continuation $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=21600 bash scripts/train_run.sh $RUN $T --agent.seed 82 \
  --agent.max-iterations 3200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r04 4218410
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218432 --json $R-target.json > /tmp/r04p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218433 --json $R-target-crossing.json > /tmp/r04p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r04
python scripts/rally_check.py target $R r04
