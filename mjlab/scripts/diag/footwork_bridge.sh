#!/usr/bin/env bash
# D-185 bridge (panel round 54, 3 of 5 "first"): does the current rally composite inherit the prior's travel cap?
# Rally run 22b model_30200 (lam_r 2 residual around RES_BASE) on Picklebot-Footwork-Measure60-RallyLamR2-G1 (run 14's
# task, move-only FootworkDrill, spots 3-5 m, 60-s episodes), mean actions (stage2_eval via footwork_eval.py), 1,024 envs,
# 120 s, dev seed 4220225. Frozen line: R = mean over sectors left (2) and back (4) of the composite's sustained p50 divided
# by the specialist's on read C (fw1d-C.json, D-183): R <= 0.65 CAP-INHERITED (route D's chain proceeds); R >= 0.85 NO-CAP
# (re-ask the panel before paying for the H1 / RES_BASE rebuild); else MIXED (reported; the chain proceeds).
# footwork_eval's BODY verdict is printed for information only (its config check flags the rally task's rewards).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
CK=$(ls -d artifacts/train/logs/picklebot_return_stand/*_rally-22b-readcfg | tail -1)/model_30200.pt
R=results/fw2b
[ -s $R.json ] || python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-G1 --checkpoint $CK \
  --envs 1024 --seconds 120 --seed 4220225 --move-prob 1.0 --json $R.json > $R.log 2>&1
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import bodyspeed_rule as bsr
comp = bsr.sectors(json.load(open("results/fw2b.json"))["move_drill"]["footwork"])
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
for a, b in zip(comp, spec):
    print(f"{a['name']:13s} composite sustained {a['sustained_p50']} (arrival {a['arrival']}) vs specialist {b['sustained_p50']:.3f}")
r = [comp[i]["sustained_p50"] / spec[i]["sustained_p50"] for i in (2, 4)]
R = sum(r) / 2
v = "CAP-INHERITED" if R <= 0.65 else "NO-CAP" if R >= 0.85 else "MIXED"
print(f"R = mean(left {r[0]:.3f}, back {r[1]:.3f}) = {R:.3f} -> {v}")
json.dump({"R": R, "left_back": r, "verdict": v}, open("results/fw2b-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw2b.done
