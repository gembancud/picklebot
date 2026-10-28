#!/usr/bin/env bash
# Refeed-delay diagnostic (panel round 43, 3/5 C; D-162). Run 19's feeder-ball loss (feeder legal 80.87 -> 77.26 % at
# model_29000 -> model_30200) appeared only in the pairs read, where each feeder ball comes 0.5 s after a rally ends;
# feeder-only reads held. This reads both checkpoints in run 19's pairs read with the feeder ball delayed 3.0 s
# (--refeed-delay 3.0), seed 4220053 for both. Pre-registered rule (experiment design) on L3 = feeder legal(29000) -
# feeder legal(30200) at 3 s: L3 <= 1.0 -> the start state (next run B: move/swing episodes off the pair courts);
# L3 >= 2.5 -> the stroke / reward (next run A: a feeder-ball return bonus); between -> B. Diagnostic only, never a
# target read.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220053 --refeed-delay 3.0"
for spec in "29000:$L/2026-10-28_12-03-16_rally-18b-sched/model_29000.pt" "30200:$(ls -d $L/*_rally-19-cont | tail -1)/model_30200.pt"; do
  PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint ${spec#*:} $PA --json results/refeed3-${spec%%:*}-pairs.json > /tmp/refeed3.log 2>&1 \
    || { echo "READ CRASHED: ${spec%%:*}"; tail -5 /tmp/refeed3.log; }
  echo "read ${spec%%:*} done"
done
python - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
from rally_check import boot_low, p5_open, wilson
out = {}
for t in ("29000", "30200"):
    j = json.load(open(f"results/refeed3-{t}-pairs.json")); p = j["pairs"]
    fed, lo = boot_low(p["court_counts"], 3, 2); own, _ = boot_low(p["court_counts"], 1, 0)
    fam = j["per_family"]; n = sum(v["episodes"] for v in fam.values())
    con = sum(v["contact"] * v["episodes"] for v in fam.values()) / max(n, 1)
    fal = sum(v["fall"] * v["episodes"] for v in fam.values()) / max(n, 1)
    s = p["started"]
    out[t] = fed
    print(f"{t}: feeder legal {fed:.4f} (low {lo:.4f}), feeder contact {con:.4f}, feeder falls/ball {fal:.4f}, partner {own:.4f}, "
          f"P(5+) open {p5_open(p)[0]:.4f}, feeder share {s['feeder'] / (s['feeder'] + s['handoffs']):.3f}, feeder n {n}")
L3 = 100 * (out["29000"] - out["30200"])
print(f"L3 = {L3:.2f} points (0.5 s read: 3.61) -> " + ("start state: B" if L3 <= 1.0 else "stroke / reward: A" if L3 >= 2.5 else "mixed: B"))
PY
echo done > artifacts/train/refeed3.done
