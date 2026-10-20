#!/usr/bin/env bash
# Stage 5G E6 (D-126, panel round 15) preparation, evaluation only:
# 1. record: E3's endpoint on the E5 ball task (rally protocol, 1,024 envs, 90 s, seed 4216504) saves the post-contact
#    (pos, vel, spin) of every legal return -> artifacts/replay/s5g-e3-returns-4216504.pt (the E6 feeds, mirrored).
# 2. pre-launch: E3 zero-shot on the E6 task (every feed one of those returns), 256 envs, 30 s, seed 4216505.
#    Pass: >= 1,000 feeds, live goals needing more than 1.5 m/s <= 21 %, falls per feed <= 2.5 %. Its legal-return rate
#    is E6's kill line.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
CK=artifacts/train/logs/picklebot_latent/2026-10-20_15-12-17_s5g-e3-timed-v3/model_39699.pt
A="--move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally"
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-PPO-G1 --envs 1024 --seconds 90 $A \
  --seed 4216504 --record-returns $PWD/artifacts/replay/s5g-e3-returns-4216504.pt --json results/s5g-e3-record-4216504.json \
  > /tmp/rec.log 2>&1; echo "record exit $?"
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-Own-G1 --envs 256 --seconds 30 $A \
  --seed 4216505 --json results/s5g-zs-e3-own.json > /tmp/zs_own.log 2>&1; echo "zero-shot exit $?"
python - <<'PY'
import json, torch
r = torch.load("artifacts/replay/s5g-e3-returns-4216504.pt")
print("recorded returns", tuple(r.shape))
d = json.load(open("results/s5g-zs-e3-own.json")); g = d["timed_goals"]
bins = g["root_within_25cm_by_required_speed"]; n = sum(v[0] for v in bins.values())
fast = sum(v[0] for k, v in bins.items() if float(k.split("-")[0]) >= 1.5) / max(n, 1)
print(f"feeds {d['episodes']}; legal {d['legal_return_rate']:.4f} {d['legal_return_ci95']}; falls/feed {d['fall_rate']:.4f} "
      f"(pass <= 0.025); goals > 1.5 m/s {fast:.3f} (pass <= 0.21); contact {d['contact_rate']:.4f}")
for k in ("goals_set", "root_within_25cm_by_required_speed", "legal_returns_and_falls_per_goal_by_required_speed",
          "paddle_err_p90_reachable_m", "paddle_err_over_50cm", "timing_within_50ms", "root_within_25cm"):
    print(k, g.get(k))
c = d["contact_diagnostics"]; print({k: c[k] for k in ("contact_height_mean", "ball_speed_in_mean", "ball_speed_out_mean", "net_clearance_mean_m", "landing_x_mean", "landing_abs_y_mean")})
ok = d["episodes"] >= 1000 and d["fall_rate"] <= 0.025 and fast <= 0.21
print("PRE-LAUNCH", "PASS" if ok else "FAIL")
PY
