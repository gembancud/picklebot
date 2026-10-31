#!/usr/bin/env bash
# D-189 first GPU action (panel round 58, (d) 4 of 5): route C's floor test. How much of the footwork specialist's joint
# action can latent-07's decoder reproduce? scripts/latent_reach_floor.py unchanged (the D-057 / D-082 instrument),
# launched through runpy after registering the footwork tasks: fw1b-S model_16600 on its own task
# (Picklebot-Footwork-Specialist-G1), move episodes only, lams 3 and 5, 256 envs, 8 s, dev seed 4220245.
# Frozen routing on the LEG group at lam 3 (RES_BASE's lam; D-082's walking teacher: 93 % explained):
#   explained_legs = 1 - mse_legs / var_legs >= 0.85 -> d1: rebuild the base by the s5c-18 recipe with fw1b-S as the
#   footwork teacher, keeping latent-07 (no new code); < 0.85 -> d2: a residual-aware kickstart with leg_r 0.3.
#   lam 5 (about the composite's full range, 3 + 2) is reported.
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
pgrep -f "run-name |distill_latent" > /dev/null && { echo "a trainer is running: not started"; exit 1; }
CK=artifacts/train/logs/picklebot_return_stand/2026-10-31_01-16-15_fw1b-S/model_16600.pt
python - <<PY 2>&1 | grep -v "^\[INFO\]\|^|\|^+" | tail -8 | tee results/fw-floor.log
import runpy, sys
import mjlab.tasks  # noqa: F401
import picklebot_mj.tasks.footwork_specialist  # noqa: F401
sys.argv = ["latent_reach_floor.py", "--checkpoint", "$CK", "--task", "Picklebot-Footwork-Specialist-G1", "--move-prob", "1.0",
            "--lams", "3,5", "--envs", "256", "--seconds", "8", "--seed", "4220245", "--json", "results/fw-floor.json"]
runpy.run_path("scripts/latent_reach_floor.py", run_name="__main__")
PY
python -I - <<'PY' | tee results/fw-floor-summary.txt
import json
d = json.load(open("results/fw-floor.json"))
var = d["action_var"]
legs_key = next(k for k in var if "leg" in k)
for lam, fit in d["fits"].items():
    e = 1 - fit[legs_key] / var[legs_key]
    print(f"lambda {lam}: legs explained {e:.3f} (mse {fit[legs_key]:.4f} / var {var[legs_key]:.4f})")
e3 = 1 - d["fits"]["lambda_3"][legs_key] / var[legs_key]
print("ROUTE:", "d1 (s5c-18 recipe with fw1b-S teacher)" if e3 >= 0.85 else "d2 (residual-aware kickstart, leg_r 0.3)")
PY
