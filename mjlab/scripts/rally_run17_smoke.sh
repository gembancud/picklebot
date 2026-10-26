#!/usr/bin/env bash
# D-157 smoke: rally run 17's task resumes 2026-10-26_12-30-00_rally-16-teacher-init/model_27798 (run 14's endpoint with five zero actor input columns)
# with its optimizer and no critic warm-up. Forty PPO iterations at 1,024 envs (training seed 87; never a parent): mean
# fell_over must be <= 1.5 x run 14 smoke's 0.106; the teacher input must be live at gain 30 (teacher_obs_check, 4219902,
# no selection); and the five teacher columns' first-layer norm after the smoke is reported against run 16's smoke.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-17-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Teacher30-G1 \
  --agent.seed 87 --agent.max-iterations 40 --agent.resume True --agent.load-run 2026-10-26_12-30-00_rally-16-teacher-init \
  --agent.load-checkpoint model_27798.pt
cat artifacts/train/rally-17-smoke.exit.json
grep -a -E "Traceback|Error" artifacts/train/rally-17-smoke.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/rally-17-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}'
grep -a -o "Episode_Reward/paddle_contact: [0-9.-]*" artifacts/train/rally-17-smoke.log | awk '{s+=$2;n++} END{print "paddle_contact mean", s/n, "(run 16 smoke 0.0456, run 14 smoke 0.0438)"}'
python - <<'EOF'
import glob, torch
for run in ("rally-16-smoke", "rally-17-smoke"):
    d = sorted(glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}"))[-1]
    ck = sorted(glob.glob(d + "/model_*.pt"), key=lambda x: int(x.split("_")[-1][:-3]))[-1]
    W = torch.load(ck, map_location="cpu", weights_only=False)["actor_state_dict"]["mlp.0.weight"]
    print(run, ck.split("/")[-1], "teacher column norms", [round(float(x), 4) for x in W[:, 124:].norm(dim=0)])
EOF
PICKLEBOT_LAM_R=2 PICKLEBOT_TEACHER=1 PICKLEBOT_TEACHER_GAIN=30 python scripts/diag/teacher_obs_check.py --checkpoint artifacts/train/logs/picklebot_return_stand/2026-10-26_12-30-00_rally-16-teacher-init/model_27798.pt --seed 4219902 2>&1 | grep -a -E "teacher input|Error|Traceback"
