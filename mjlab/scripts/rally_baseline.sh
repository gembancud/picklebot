#!/usr/bin/env bash
# D-135 baseline for the rally target (mjlab/results/rally-target.md): Stage 5H run 4's endpoint (s5h-04-pairs/model_3398)
# in two-robot pairs on the R4 protocol (Picklebot-Latent-Court-Res-G1, every family, no hint, rally, 2,048 envs = 1,024
# courts, 120 s), with the old hand-off (net crossing, seed 4218000) and the corrected one (partner's contact, seed 4218001).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 2048 --seconds 120"
for spec in "crossing:4218000" "contact:4218001"; do
  h=${spec%%:*}; s=${spec#*:}
  bash scripts/stage2_eval.sh s5h-04-pairs model_3398.pt $A --pair-handoff $h --seed $s --json results/rally-baseline-$h.json > /tmp/rb_$h.log 2>&1
  echo "$h exit $?"
done
python - <<'PY'
import json, math
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]
for h in ("crossing", "contact"):
    d = json.load(open(f"results/rally-baseline-{h}.json")); p = d["pairs"]
    n = p["rallies"]; k5 = round(p["p_len_ge_5"] * n) if p["p_len_ge_5"] is not None else 0
    so = p["sides_own_ball"]; kk = sum(round(v["legal"] * v["feeds"]) for v in so.values() if v["feeds"]); nn = sum(v["feeds"] for v in so.values())
    print(f"{h}: rallies {n}; P(5+) {p['p_len_ge_5']} {wilson(k5, n)}; P(4+) {p['p_len_ge_4']}; mean {p['mean_len']}; "
          f"own-ball legal {kk / max(nn, 1):.4f} {wilson(kk, nn)} (A {so['A']['legal']}, B {so['B']['legal']}); feeder-side legal {p['sides']}; "
          f"falls/episode {d['robot_fall_rate_per_episode']}")
PY
