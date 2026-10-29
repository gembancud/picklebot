#!/usr/bin/env bash
# Rally run 23 (D-171): run 22b's design plus one change: every training rally ends after its 3rd shot (pair_rally_cap 3,
# D-161's mechanism, set by override and recorded in params/env.yaml). Run 22b was killed at model_30200 with partner-ball
# legal 0.989 but feeder-ball legal 0.656 [read:protocol]. In training the feeder share fell 0.290 -> 0.150 and training
# feeder legal fell 0.796 -> 0.731 [train-log]. Pre-launch (scripts/diag/prelaunch23.sh, PASS): from model_30200, 300
# iterations, cap 3 against no cap: feeder legal 0.811 vs 0.724 (+8.7), share 0.440 vs 0.165, ball 0 / 1 failure
# 0.232 / 0.232 vs 0.330 / 0.324, falls 2.16 vs 2.10 per 1,000 env-seconds [train-diag].
# Parent run 22b model_30200 (with its optimizer state), 1e-4, no warm-up, 4,000 iterations, cooldown over the last
# 20 %. Smoke seed 137, training seed 138.
# Smoke: falls <= 4.157 per 1,000 env-seconds (D-170), gradients, and every override (now including pair_rally_cap 3)
# plus the kept-on noise in params/env.yaml.
# Reads (PICKLEBOT_LAM_R=2): the parent model_30200 re-read first, then model_31400 (30 %), same seeds: drill v2 4220105,
# move 4220106, court 4220107, pairs (contact hand-off, 2,048 envs, 120 s) 4220108, direction split 4220109, pairs with a
# 3 s refeed 4220110. Kill: rally_check.py early-r21 unchanged (early-r19's lines with D-160's cumulative guards against
# run 14: feeder legal >= parent - 1 and >= run 14 - 2, every family within run 14 - 5, left + back within run 14 - 5;
# P(5+) open >= parent + 1.0; partner >= parent - 1.5; falls; plus feeder legal at the 3 s refeed >= parent - 1.0).
# Exit 2 is not a kill. Endpoint (read once): h5f_clean_eval.sh on 4220111-4220126, target / M1 read 4220127, crossing
# 4220128 (reported), direction split 4220129; r19-gate, m1, target.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-23-cap3; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-23
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt; EARLY=model_31400.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A $B.pair-rally-cap 3"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_LR_COOLDOWN=0.2 PICKLEBOT_LR_FINAL=1e-5
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }
tail -1 results/prelaunch23-summary.txt | grep -q ": ok$" || { echo "pre-launch check not passed (results/prelaunch23-summary.txt): run not started"; exit 1; }

# smoke
PICKLEBOT_LR_TOTAL=40 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
  --agent.seed 137 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV
cat artifacts/train/$RUN-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/$RUN-smoke.log | head -3
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee /tmp/r23-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $L/*_$RUN-smoke/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/r23-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$(ls -d $L/*_$RUN-smoke | tail -1)/params/env.yaml" <<'PY' | tee -a /tmp/r23-smoke.txt
import re, sys
text = open(sys.argv[1]).read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("pair_rally_cap", "3"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
noise = re.search(r"^\s+enable_corruption: true\s*$", text, re.M) is not None
print("smoke config check: missing", miss, "actor noise on", noise, "ok" if not miss and noise else "STOP")
PY
[ "$(grep -c " ok$" /tmp/r23-smoke.txt)" = 3 ] || { echo "smoke failed: run not started"; exit 1; }

EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4220105"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4220106"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220107"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220108"
read_ck() { # checkpoint, output prefix, log tag; returns 2 on a crash
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${spec#*:} --json $2-${spec%%:*}.json > /tmp/r23-$3.log 2>&1 \
      || { echo "READ CRASHED: $2 ${spec%%:*}"; tail -3 /tmp/r23-$3.log; return 2; }
  done
  PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${PA/--seed 4220108/--seed 4220110} --refeed-delay 3.0 --json $2-pairs3.json > /tmp/r23-$3.log 2>&1 \
    || { echo "READ CRASHED: $2 pairs3"; tail -3 /tmp/r23-$3.log; return 2; }
  PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220109 --json $2-dir.json > /tmp/r23-$3.log 2>&1 \
    || { echo "READ CRASHED: $2 dir"; tail -3 /tmp/r23-$3.log; return 2; }
}
read_ck $L/$PRUN/$PCK $R-parent-early p || exit 1; echo "parent read done"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  read_ck $D/$EARLY $R-early e || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/rally_check.py early-r21 $R; rc=$?
  case $rc in
    0) echo "early check: pass";;
    1) echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN";;
    *) echo "early check: CHECK CRASHED (exit $rc), no kill";;
  esac
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_LR_TOTAL=4000 PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=50400 bash scripts/train_run.sh $RUN $T \
  --agent.seed 138 --agent.max-iterations 4000 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; echo killed > artifacts/train/$RUN.done; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r23 4220111
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4220127 --json $R-target.json > /tmp/r23p.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4220128 --json $R-target-crossing.json > /tmp/r23p.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220129 --json $R-endpoint-dir.json > /tmp/r23pd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py r19-gate $R r23
python scripts/rally_check.py m1 $R r23
python scripts/rally_check.py target $R r23
echo done > artifacts/train/$RUN.done
