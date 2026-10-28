#!/usr/bin/env bash
# Rally run 18b (2026-10-28): rally run 18 (scripts/rally_run18.sh) relaunched with the std floor fixed. Run 18 was
# stopped during its parent read, before training began: the audit (docs/research/audit-2026-10-28-training-loop.md C1)
# found that ScheduledPPO's floor used rsl_rl's forward clamp, which passes zero gradient at the floor, so an output that
# reached it froze for good (output 30 sat at 0.1 with no gradient in the sweep and run 18's smoke). The floor now clamps
# the parameter after each optimizer step. Everything else is run 18's pre-registered design, below, with a new run name,
# smoke seed 4219991 and training seed 4219992; the read seeds 4219967-4219990 are unchanged (no child read used them).
# The smoke also stops if any std output has no gradient or sits below the floor.
# Run 18's design: rally run 18 (2026-10-28; the user approved option 1 after the learning-rate sweep, "yeah sure"): rally run 14's task
# and reward unchanged; the one change is the optimizer package the sweep tested, at its 1e-4 arm:
#   - parent 2026-10-28_00-00-00_lrsweep-init/model_27798 (run 14's endpoint, Adam's state emptied, output 30's collapsed
#     std raised 0.0022 -> 0.1; scripts/fresh_init.py);
#   - ScheduledPPO (picklebot_mj/rl/sched_ppo.py): std floor 0.1, linear warm-up over 50 updates to 1e-4, constant, then a
#     1 - sqrt cooldown to 1e-5 over the last 20 % (updates 3,200-4,000); KL guard 0.05; no adaptive rule.
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1, training seed 4219966, no
# critic warm-up, 12,288 envs, 4,000 iterations (wall cap 14 h, a guard only). Endpoint: the last checkpoint.
# Smoke: 40 iterations at 1,024 envs (seed 4219965): mean fell_over <= 0.159 (1.5 x run 14 smoke), else stop.
# Early kill at model_29000 (about 30 %), the parent (run 14 model_27798) read on the same seeds first: drill v2 0/0
# (4219967), move drill (4219968), court drill (4219969), pairs R4 with the contact hand-off (2,048 envs, 120 s,
# 4219970), the direction split (4219971). Kill if (scripts/rally_check.py early-sched): P(5+) not up by at least 2
# points; any feeder family loses more than 5 points of contact; left + back feeder-ball contact more than 5 points below
# the parent; partner-ball legal below max(50 %, parent - 3 points); feeder-ball legal below parent - 2 points; court
# legal given contact, court contact or pair contact more than 3 points below the parent; court main, drill v2 or the
# lowest move arrival more than 5 points below the parent; court falls Wilson low > 4 % or point > 7.4 %.
# Endpoint: h5f_clean_eval.sh on 4219972-4219987; the M1 and target read (2,048 envs, 120 s, read once) with the contact
# hand-off on 4219988; crossing 4219989 (reported); the direction split 4219990 (reported). Success (pre-registered,
# rally_check.py sched-gate): P(5+) Wilson low above run 14's endpoint P(5+) (18.73 %), partner-ball legal >= run 14 - 3,
# feeder-ball legal >= run 14 - 2, sides within 3 points, court falls <= 4 %.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=rally-18b-sched; L=artifacts/train/logs/picklebot_return_stand; R=results/rally-18b
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
PRUN=2026-10-28_00-00-00_lrsweep-init; PCK=model_27798.pt; EARLY=model_29000.pt
P14=$L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=50 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_LR_COOLDOWN=0.2 PICKLEBOT_LR_FINAL=1e-5
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }

# smoke
PICKLEBOT_LR_TOTAL=40 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
  --agent.seed 4219991 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
cat artifacts/train/$RUN-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/$RUN-smoke.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/$RUN-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "smoke fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}' | tee /tmp/r18b-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $L/*_$RUN-smoke/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/r18b-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
# every 35-wide Adam state (the std and the last actor bias) must have a gradient in every output
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
[ "$(grep -c " ok$" /tmp/r18b-smoke.txt)" = 2 ] || { echo "smoke failed: run not started"; exit 1; }

EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4219967"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4219968"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4219969"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219970"
read_ck() { # checkpoint, output prefix, log tag; exit 2 on a crash
  for spec in "v2:$EV" "move:$MV" "court:$CV" "pairs:$PA"; do
    PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $1 ${spec#*:} --json $2-${spec%%:*}.json > /tmp/r18b-$3.log 2>&1 \
      || { echo "READ CRASHED: $2 ${spec%%:*}"; return 2; }
  done
  PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4219971 --json $2-dir.json > /tmp/r18b-$3.log 2>&1 \
    || { echo "READ CRASHED: $2 dir"; return 2; }
}
read_ck $P14 $R-parent-early p || exit 1; echo "parent read done"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/$EARLY" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  read_ck $D/$EARLY $R-early e || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/rally_check.py early-sched $R && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_LR_TOTAL=4000 PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=50400 bash scripts/train_run.sh $RUN $T \
  --agent.seed 4219992 --agent.max-iterations 4000 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; echo killed > artifacts/train/$RUN.done; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) r18b 4219972
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff contact --seed 4219988 --json $R-target.json > /tmp/r18bp.log 2>&1; echo "target read: $?"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh $RUN $(basename $CK) $A --pair-handoff crossing --seed 4219989 --json $R-target-crossing.json > /tmp/r18bp.log 2>&1; echo "crossing read: $?"
PICKLEBOT_LAM_R=2 python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4219990 --json $R-endpoint-dir.json > /tmp/r18bpd.log 2>&1; echo "endpoint dir: $?"
python scripts/rally_check.py sched-gate $R r18b
python scripts/rally_check.py m1 $R r18b
python scripts/rally_check.py target $R r18b
echo done > artifacts/train/$RUN.done
