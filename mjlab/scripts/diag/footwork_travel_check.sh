#!/usr/bin/env bash
# Travel check (D-184, panel round 53: 5 of 5 "check first"). Evaluation only, one shot, frozen before it runs.
# tracking_eval.py --per-stroke (4-s windows, 4 repeats) with the per-env travel instrument (D-184):
#   T1: H0 (s5c-03b model_63300) on footwork-fast.npz, dev seed 4220217
#   T2: latent-07 (latent_10651) on footwork-fast.npz, dev seed 4220217 (paired with T1)
#   T3: H0 on its own training motion tennis-lafan3.npz (control: the LAFAN1 windows, FAST if >= 30 envs else all),
#       dev seed 4220218
# Routing: picklebot_mj/travel_rule.py (route(); thresholds 0.90 / 0.80, SKATE_MAX 0.15, instrument tolerance 0.05).
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
H0=artifacts/train/logs/picklebot_tracking/2026-10-14_18-52-53_s5c-03b-h0mirror/model_63300.pt
LAT=artifacts/train/latent/latent-07/latent_10651.pt
R=results/fw2t
[ -s $R-T1.json ] || python scripts/motion/tracking_eval.py --checkpoint $H0 --task Picklebot-Tracking-FootworkFast-G1 \
  --per-stroke --repeats 4 --seed 4220217 --json $R-T1.json > $R-T1.log 2>&1
[ -s $R-T2.json ] || python scripts/motion/tracking_eval.py --latent --checkpoint $LAT --task Picklebot-Tracking-FootworkFast-G1 \
  --per-stroke --repeats 4 --seed 4220217 --json $R-T2.json > $R-T2.log 2>&1
[ -s $R-T3.json ] || python scripts/motion/tracking_eval.py --checkpoint $H0 --task Picklebot-Tracking-TennisLafan3-Huge-G1 \
  --per-stroke --repeats 4 --seed 4220218 --json $R-T3.json > $R-T3.log 2>&1
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import travel_rule as tr
t1, t2, t3 = (json.load(open(f"results/fw2t-T{i}.json")) for i in (1, 2, 3))
h0, lat = tr.read_stats(t1), tr.read_stats(t2)
laf = tr.read_stats(t3, tr.is_lafan)
if laf.get("envs", 0) < tr.MIN_LAFAN_FAST:
    laf = {**tr.read_stats(t3, tr.is_lafan, fast=False), "note": "all LAFAN windows (too few FAST)"}
laf_all = tr.read_stats(t3, tr.is_lafan, fast=False)
for name, s in (("T1 H0 footwork-fast FAST", h0), ("T2 latent-07 footwork-fast FAST", lat), ("T3 H0 LAFAN1 control", laf),
                ("T3 H0 LAFAN1 all windows (reported)", laf_all)):
    print(name, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}))
v, sub, lines = tr.route(h0, lat, laf)
for line in lines:
    print("  " + line)
print(f"VERDICT: {v}" + (f" / {sub}" if sub else ""))
json.dump({"T1": h0, "T2": lat, "T3_control": laf, "T3_all": laf_all, "verdict": v, "sub": sub, "lines": lines},
          open("results/fw2t-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw2t.done
