#!/usr/bin/env bash
# Rally run 9 (D-148, panel round 31): rally run 8's pace ceiling (-50 x clamp((|v_out| - 9.5) / 2, 0, 1) at the first
# legal contact) on returns of a partner's ball only (pairs.handed); feeder-ball returns are exempt. The one change
# against run 8. Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-PaceOwn-G1, from
# rally-05-weak/model_15000 with its optimizer, training seed 87, no critic warm-up, 12,288 envs, 3,200 iterations,
# wall cap 6 h (the panel's choice). Endpoint: the last checkpoint before the cap.
# Early kill at model_15900 (about 30 %), the parent read on the same seeds first: drill v2 0/0 (4218911), move drill
# (4218912), court drill (4218913), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s, 4218914). Kill if
# (scripts/rally_check.py early-ceiling-own): D-145's lines unchanged (the mechanism did not engage: pair ball out not
# down 0.4 m/s and the share above 11 m/s not down 8 points; partner-ball legal below max(50 %, parent - 3 points);
# feeder-ball legal below parent - 2 points; court legal given contact, court contact or pair contact more than 3
# points below the parent; court main, drill v2 or the lowest move arrival more than 5 points below the parent; court
# falls Wilson low > 4 % or point > 7.4 %), plus any feeder-ball family losing more than 5 points of contact.
# Endpoint: h5f_clean_eval.sh on 4218920-4218935; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4218942; crossing on 4218943 (reported). Success (pre-registered): partner-ball legal >= 58.2 % with a
# bootstrap low > 55.2 %, and feeder-ball legal >= 81.9 % (run 5's M1 read: no loss).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-09-paceown; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-09
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-PaceOwn-G1
PRUN=2026-10-22_23-28-36_rally-05-weak; PCK=model_15000.pt; EARLY=model_15900.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218911"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218912"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218913"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4218914"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-05-weak $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r09.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r09e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early-ceiling-own $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=21600 bash scripts/train_run.sh $RUN $T --agent.seed 87 \
  --agent.max-iterations 3200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r09 4218920
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218942 --json $R-target.json > /tmp/r09p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218943 --json $R-target-crossing.json > /tmp/r09p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r09
python scripts/rally_check.py target $R r09
