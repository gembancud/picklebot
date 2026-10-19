#!/usr/bin/env bash
# Self-play readiness R4 (D-116, selfplay-readiness.md): two-robot smoke test on mirrored env pairs (picklebot_mj/pairs.py).
# Usage: h5f_pairs.sh RUN CKFILE TAG I. Two copies of the endpoint, 2048 envs = 1024 courts, court task, no hint, rally
# feeds for the feeder ball that starts each rally (not counted), 120 s, seed 4215200+I -> results/selfplay-r4-TAG.json.
# Bar: P(4+ consecutive legal robot shots) >= 0.25 over >= 1,000 rallies, and sides A and B within 3 points of legal.
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; I=$4; R=results/selfplay-r4-$TAG
bash scripts/stage2_eval.sh $RUN $CK --task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 120 --move-prob 0.0 \
  --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --seed $((4215200 + I)) --json $R.json \
  > /tmp/r4_$TAG.log 2>&1; echo "pairs: $?"
~/envs/picklebot-mj/bin/python - "$R" <<'PY'
import json, sys
p = json.load(open(sys.argv[1] + ".json"))["pairs"]
a, b = p["sides"]["A"], p["sides"]["B"]
gap = abs((a["legal"] or 0) - (b["legal"] or 0))
ok = p["rallies"] >= 1000 and (p["p_len_ge_4"] or 0) >= 0.25 and gap <= 0.03
print(f"R4 {sys.argv[1]}: rallies {p['rallies']}; P(len >= 4) {p['p_len_ge_4']}; P(len >= 10) {p['p_len_ge_10']}; mean {p['mean_len']}; "
      f"side A legal {a['legal']} falls/shot {a['falls_per_shot']}; side B legal {b['legal']} falls/shot {b['falls_per_shot']}; "
      f"gap {gap:.4f}; pass: {ok}")
PY
