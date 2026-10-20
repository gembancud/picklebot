#!/usr/bin/env bash
# D-127 (panel round 16): the contact decomposition, evaluation only. E3's endpoint on the E5 task (court feeds),
# 256 envs, 30 s, development seed 4216507: every first contact's incoming ball, paddle state, commanded paddle state
# and planned outgoing ball -> results/s5g-contacts-e3.pt, analysed by picklebot_mj/contact_check.py.
# Pre-registered rule: the larger of the mean landing-x gaps (planner: commanded - target; controller: realized -
# commanded) picks the fix: planner -> a planner impact-model fix, read zero-shot (c); controller -> E6 with the face
# factor tightened (b). A landing reward only if both are under 0.3 m.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
CK=artifacts/train/logs/picklebot_latent/2026-10-20_15-12-17_s5g-e3-timed-v3/model_39699.pt
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-PPO-G1 --envs 256 --seconds 30 \
  --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --seed 4216507 \
  --record-contacts $PWD/results/s5g-contacts-e3.pt --json results/s5g-contacts-e3.json > /tmp/cc.log 2>&1; echo "exit $?"
python - <<'PY'
import json, torch
from picklebot_mj.contact_check import decompose
out = decompose(torch.load("results/s5g-contacts-e3.pt"))
json.dump(out, open("results/s5g-contacts-e3-decomposition.json", "w"), indent=1)
print(json.dumps(out, indent=1))
d = json.load(open("results/s5g-contacts-e3.json")); print("legal", d["legal_return_rate"], "contact", d["contact_rate"])
PY
