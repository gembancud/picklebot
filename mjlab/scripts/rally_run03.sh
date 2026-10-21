#!/usr/bin/env bash
# Rally run 3 (D-139, panel round 25; a 2-2-1 vote broken by "least new code"): rally run 2 continued unchanged. The
# training curve was still rising at the cap. Same task (Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-
# Coop-G1), from rally-02-coop/model_6400 with its optimizer, training seed 81, no critic warm-up
# (PICKLEBOT_CRITIC_WARMUP=0: the critic is already trained), 12,288 envs, 3,200 iterations, wall cap 6 h. Endpoint:
# the last checkpoint before the cap.
# Early kill at model_7300 (about 30 %; a crashed evaluation never kills, D-112), the parent read on the same seeds first:
#   drill v2 0/0 (4218301), move drill (4218302), court drill (4218303), pairs R4 protocol with the contact hand-off
#   (1,024 envs, 60 s, 4218304). Kill if (scripts/rally_check.py early-continuation):
#   - partner-ball legal below the parent's bootstrap low minus 2 points;
#   - feeder-ball legal more than 3 points below the parent;
#   - court main, drill v2 or the lowest move arrival more than 5 points below the parent;
#   - court falls Wilson low > 4 % or point > 7.4 %.
# Reported before launch: model_6400 in pairs with a 2 s refeed delay (4218305; experiment design: how much of the
# feeder-ball gap is the robot's state when the feeder ball fires).
# Endpoint: h5f_clean_eval.sh on 4218310-4218325; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4218332; crossing on 4218333 (reported). Panel trigger: a feeder-ball gain under +3 points.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-03-coop-cont; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-03
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1
PRUN=2026-10-21_20-50-34_rally-02-coop; PCK=model_6400.pt; EARLY=model_7300.pt
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4218301"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4218302"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4218303"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 1024 --seconds 60 --seed 4218304"
for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
  bash scripts/stage2_eval.sh rally-02-coop $PCK ${spec#*:} --json $R-parent-early-${spec%%:*}.json > /tmp/r03.log 2>&1; echo "parent early ${spec%%:*}: $?"
done
P2="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 1024 --seconds 60 --refeed-delay 2.0 --seed 4218305"
bash scripts/stage2_eval.sh rally-02-coop $PCK $P2 --json $R-parent-refeed2s.json > /tmp/r03.log 2>&1; echo "parent refeed 2 s: $?"
python - <<'PY'
import json, sys
sys.path.insert(0, "scripts"); import rally_check as r
for k in ("parent-early-pairs", "parent-refeed2s"):
    p = json.load(open(f"results/rally-03-{k}.json"))["pairs"]
    print(k, "partner-ball", r.boot_low(p["court_counts"], 1, 0), "feeder-ball", r.boot_low(p["court_counts"], 3, 2), "P(5+)", p["p_len_ge_5"])
PY
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    python scripts/stage2_eval.py --checkpoint $D/$EARLY ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r03e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python scripts/rally_check.py early-continuation $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=21600 bash scripts/train_run.sh $RUN $T --agent.seed 81 \
  --agent.max-iterations 3200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r03 4218310
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4218332 --json $R-target.json > /tmp/r03p.log 2>&1; echo "target read: $?"
bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4218333 --json $R-target-crossing.json > /tmp/r03p.log 2>&1; echo "crossing read: $?"
python scripts/rally_check.py m1 $R r03
python scripts/rally_check.py target $R r03
