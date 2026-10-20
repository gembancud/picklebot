#!/usr/bin/env bash
# Stage 5G E6 pre-launch check (D-125, panel round 14): E3's endpoint zero-shot on the E6 task (walkable contact),
# seed 4216503, 256 envs, 30 s, as E3's zero-shot on the E5 task (seed 4216020). Pass: live goals needing more than
# 1.5 m/s <= 21 % (the bank's share), legal returns >= 15.24 % (E3 on the E5 task), falls per feed <= 2.5 %.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
CK=artifacts/train/logs/picklebot_latent/2026-10-20_15-12-17_s5g-e3-timed-v3/model_39699.pt
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-Walk-G1 --envs 256 --seconds 30 \
  --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --seed 4216503 \
  --json results/s5g-zs-e3-walk.json > /tmp/zs_walk.log 2>&1; echo "exit $?"
python - <<'PY'
import json
d = json.load(open("results/s5g-zs-e3-walk.json")); g = d["timed_goals"]
bins = g["root_within_25cm_by_required_speed"]; n = sum(v[0] for v in bins.values())
fast = sum(v[0] for k, v in bins.items() if float(k.split("-")[0]) >= 1.5) / max(n, 1)
print(f"legal {d['legal_return_rate']:.4f} {d['legal_return_ci95']} (pass >= 0.1524); falls/feed {d['fall_rate']:.4f} (pass <= 0.025); "
      f"goals > 1.5 m/s {fast:.3f} (pass <= 0.21); contact {d['contact_rate']:.4f}")
for k in ("goals_set", "root_within_25cm_by_required_speed", "legal_returns_and_falls_per_goal_by_required_speed",
          "paddle_err_p90_reachable_m", "paddle_err_over_50cm", "timing_within_50ms", "root_within_25cm"):
    print(k, g.get(k))
c = d["contact_diagnostics"]; print({k: c[k] for k in ("contact_height_mean", "ball_speed_out_mean", "net_clearance_mean_m", "landing_x_mean", "landing_abs_y_mean")})
ok = d["legal_return_rate"] >= 0.1524 and d["fall_rate"] <= 0.025 and fast <= 0.21
print("PRE-LAUNCH", "PASS" if ok else "FAIL")
PY
