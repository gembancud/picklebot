#!/usr/bin/env bash
# D-156 smoke: rally run 16's task resumes 2026-10-26_12-30-00_rally-16-teacher-init/model_27798 (run 14's endpoint, five zero actor input columns) with
# its optimizer and no critic warm-up. Forty PPO iterations at 1,024 envs (training seed 86; the checkpoints are never a
# parent): mean fell_over must be <= 1.5 x run 14 smoke's 0.106. Then (no selection): the widened parent with
# PICKLEBOT_TEACHER=1 and run 14's endpoint without it, 64-env pairs reads on 4219803 (they must agree: zero columns), and
# the teacher input check (scripts/diag/teacher_obs_check.py, 4219804).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-16-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Teacher-G1 \
  --agent.seed 86 --agent.max-iterations 40 --agent.resume True --agent.load-run 2026-10-26_12-30-00_rally-16-teacher-init \
  --agent.load-checkpoint model_27798.pt
cat artifacts/train/rally-16-smoke.exit.json
grep -a -E "Learning iteration|Episode_Reward/paddle_contact|Traceback|Error" artifacts/train/rally-16-smoke.log | tail -6
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/rally-16-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}'
grep -a -o "Episode_Reward/paddle_contact: [0-9.-]*" artifacts/train/rally-16-smoke.log | awk '{s+=$2;n++} END{print "paddle_contact mean", s/n, "(run 15 smoke 0.0445, run 14 smoke 0.0438)"}'
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 64 --seconds 10 --seed 4219803"
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 bash scripts/stage2_eval.sh rally-16-teacher-init model_27798.pt $A --json /tmp/r16smoke-init.json > /tmp/r16s.log 2>&1; echo "init read: $?"; grep -a -E "Error|Traceback" /tmp/r16s.log | head -3
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh rally-14-lamr2 model_27798.pt $A --json /tmp/r16smoke-parent.json > /tmp/r16s2.log 2>&1; echo "parent read: $?"
python - <<'EOF'
import json
a, b = (json.load(open(f"/tmp/r16smoke-{x}.json")) for x in ("init", "parent"))
for k in ("contact_rate", "legal_return_rate", "fall_rate"):
    print(k, a.get(k), b.get(k), "same" if a.get(k) == b.get(k) else "DIFFERENT")
EOF
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 python scripts/diag/teacher_obs_check.py --checkpoint artifacts/train/logs/picklebot_return_stand/2026-10-26_12-30-00_rally-16-teacher-init/model_27798.pt --seed 4219804 2>&1 | grep -a -E "teacher input|Error|Traceback"
