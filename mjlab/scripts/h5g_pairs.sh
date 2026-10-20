#!/usr/bin/env bash
# Self-play readiness R4 (D-116, selfplay-readiness.md): two-robot smoke test on mirrored env pairs (picklebot_mj/pairs.py).
# Usage: h5g_pairs.sh RUN CKFILE TAG I [TASK] (D-118: h5f_pairs.sh with the task as an argument; D-116 tightening: side
# symmetry on own-ball shots only, the feeder ball excluded, reported alongside). Two copies of the endpoint, 2048 envs = 1024 courts, court task, no hint, rally
# feeds for the feeder ball that starts each rally (not counted), 120 s, seed 4215200+I -> results/selfplay-r4-TAG.json.
# Bar: P(4+ consecutive legal robot shots) >= 0.25 over >= 1,000 rallies, and sides A and B within 3 points of legal.
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; I=$4; T=${5:-Picklebot-Latent-Court-Res-G1}; R=results/selfplay-r4-$TAG
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 120 --move-prob 0.0 \
  --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --seed $((4215200 + I)) --json $R.json \
  > /tmp/r4_$TAG.log 2>&1; echo "pairs: $?"
~/envs/picklebot-mj/bin/python - "$R" <<'PY'
import json, sys
p = json.load(open(sys.argv[1] + ".json"))["pairs"]
a, b = p["sides"]["A"], p["sides"]["B"]
oa, ob = p["sides_own_ball"]["A"], p["sides_own_ball"]["B"]
gap = abs((oa["legal"] or 0) - (ob["legal"] or 0))  # D-116 tightening: own-ball shots only, the feeder ball excluded
gap_all = abs((a["legal"] or 0) - (b["legal"] or 0))
ok = p["rallies"] >= 1000 and (p["p_len_ge_4"] or 0) >= 0.25 and gap <= 0.03
print(f"R4 {sys.argv[1]}: rallies {p['rallies']}; P(len >= 4) {p['p_len_ge_4']}; P(len >= 10) {p['p_len_ge_10']}; mean {p['mean_len']}; "
      f"side A legal {a['legal']} falls/shot {a['falls_per_shot']}; side B legal {b['legal']} falls/shot {b['falls_per_shot']}; "
      f"own-ball legal A {oa['legal']} ({oa['feeds']}) / B {ob['legal']} ({ob['feeds']}); gap (own-ball) {gap:.4f}, all shots {gap_all:.4f}; pass: {ok}")
PY
