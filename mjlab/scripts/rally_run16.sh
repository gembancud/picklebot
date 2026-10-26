#!/usr/bin/env bash
# Rally run 16 (D-156, panel round 38, 3/5 for the e4 teacher; RL and architecture voted to continue run 14): rally run
# 14's task (lam_r 2) plus the privileged true-state contact point and time of every live feed as a trailing actor input
# (return_stand.teacher_contact_obs), the one change against run 14.
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Teacher-G1, from rally-14
# model_27798 with five zero actor input columns (scripts/rally_run16_init.sh), with its optimizer, training seed 94, no
# critic warm-up, 12,288 envs, 6,400 iterations (wall cap 18 h, a guard only). Endpoint: the last checkpoint.
# Run 16's reads set PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1; the parent's re-reads set PICKLEBOT_LAM_R=2.
# Early kill at model_29700 (about 30 %), the parent re-read on the same seeds first: drill v2 0/0 (4219811), move drill
# (4219812), court drill (4219813), pairs R4 protocol with the contact hand-off (2,048 envs, 120 s, 4219814), and the
# direction split (4219815). Kill if (scripts/rally_check.py early-teacher = run 14's early-lamr2 lines): left + back
# feeder-ball contact not up by at least 2 points; reach_deep + fast feeder-ball contact not up; any feeder family loses
# more than 5 points of contact; partner-ball legal below max(50 %, parent - 3 points); feeder-ball legal below parent - 2
# points; court legal given contact, court contact or pair contact more than 3 points below the parent; court main, drill
# v2 or the lowest move arrival more than 5 points below the parent; court falls Wilson low > 4 % or point > 7.4 %.
# Endpoint: h5f_clean_eval.sh on 4219820-4219835; the M1 read (2,048 envs, 120 s, read once) with the contact hand-off
# on 4219842; crossing on 4219843 (reported); the direction split on 4219844 (reported). Teacher gate (pre-registered;
# rally_check.py teacher-gate): feeder-ball legal >= 85 % with a court-bootstrap low >= 84 %, partner-ball legal >= 68.5
# %, sides within 3 points, court falls <= 4 %. Pass: the panel builds the DAgger student (M1 is claimed only from the
# student, on fresh seeds). Fail: no distillation; the panel convenes (motion and coach vote STOP below 85 %, experiment
# design below 83.9 %).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-16-teacher; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-16
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Teacher-G1
PRUN=2026-10-26_12-30-00_rally-16-teacher-init; PCK=model_27798.pt; EARLY=model_29700.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219811"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219812"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219813"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219814"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh rally-14-lamr2 $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r16.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt --seed 4219815 --json $R-parent-early-dir.json > /tmp/r16d.log 2>&1; echo "parent early dir: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r16e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 python scripts/diag/feeder_speed_envelope.py --checkpoint $D/$EARLY --seed 4219815 --json $R-early-dir.json > /tmp/r16ed.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill): dir"; exit 2; }
  python scripts/rally_check.py early-teacher $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=64800 bash scripts/train_run.sh $RUN $T --agent.seed 94 \
  --agent.max-iterations 6400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r16 4219820
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4219842 --json $R-target.json > /tmp/r16p.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4219843 --json $R-target-crossing.json > /tmp/r16p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4219844 --json $R-endpoint-dir.json > /tmp/r16pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py teacher-gate $R r16
python scripts/rally_check.py m1 $R r16
python scripts/rally_check.py target $R r16
