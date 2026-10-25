#!/usr/bin/env bash
# Rally run 15 (D-155, panel round 37, 4/5 for lam_r 3; coach voted to continue run 14): rally run 14's task with the
# residual's latent range at 3 prior sigma (lam_r 2 -> 3), the one change against run 14.
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR3-G1, from rally-14 model_27798
# with the latent output rows and std scaled by 2/3 (scripts/lam_r_init.py --factor 0.6666667), with its optimizer,
# training seed 93, no critic warm-up, 12,288 envs, 6,400 iterations (wall cap 18 h, a guard only). Endpoint: the last
# checkpoint. Run 15's reads set PICKLEBOT_LAM_R=3; the parent's reads set PICKLEBOT_LAM_R=2.
# Early kill at model_29700 (about 30 %), the parent re-read on the same seeds first: drill v2 0/0 (4219711), move drill
# (4219712), court drill (4219713), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s, 4219714), and the
# direction split (4219715). Kill if (scripts/rally_check.py early-lamr3 = run 14's early-lamr2 lines): left + back
# feeder-ball contact not up by at least 2 points; reach_deep + fast feeder-ball contact not up; any feeder family loses
# more than 5 points of contact; partner-ball legal below max(50 %, parent - 3 points); feeder-ball legal below parent - 2
# points; court legal given contact, court contact or pair contact more than 3 points below the parent; court main, drill
# v2 or the lowest move arrival more than 5 points below the parent; court falls Wilson low > 4 % or point > 7.4 %.
# Style is reported.
# Endpoint: h5f_clean_eval.sh on 4219720-4219735; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4219742; crossing on 4219743 (reported); the direction split on 4219744 (reported). Success
# (pre-registered): feeder-ball legal >= 83.9 % with a court-bootstrap low > 81.9 %, partner-ball legal >= 68.5 %,
# sides within 3 points, court falls <= 4 %. Training time is a confound (reported). If it fails to engage: lam_r stays
# at 2 and the panel chooses among run 14 continued (the control), the e4 teacher, and a stop.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-15-lamr3; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-15
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR3-G1
PRUN=2026-10-26_06-00-00_rally-15-lamr3-init; PCK=model_27798.pt; EARLY=model_29700.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219711"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219712"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219713"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219714"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh rally-14-lamr2 $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r15.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt --seed 4219715 --json $R-parent-early-dir.json > /tmp/r15d.log 2>&1; echo "parent early dir: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=3 python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r15e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  PICKLEBOT_LAM_R=3 python scripts/diag/feeder_speed_envelope.py --checkpoint $D/$EARLY --seed 4219715 --json $R-early-dir.json > /tmp/r15ed.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill): dir"; exit 2; }
  python scripts/rally_check.py early-lamr3 $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=64800 bash scripts/train_run.sh $RUN $T --agent.seed 93 \
  --agent.max-iterations 6400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=3 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r15 4219720
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=3 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4219742 --json $R-target.json > /tmp/r15p.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=3 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4219743 --json $R-target-crossing.json > /tmp/r15p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=3 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4219744 --json $R-endpoint-dir.json > /tmp/r15pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py m1 $R r15
python scripts/rally_check.py target $R r15
