#!/usr/bin/env bash
# The user (2026-11-09): the pro videos were meant to promote agility, not to move P(5+) at once; was movement measured?
# It was not (D-249's gate reads rally outcomes and feeder contact by direction). Reads only, no training, no promotion:
# the D-185 bridge drill (Picklebot-Footwork-Measure60-RallyLamR2-G1: move-only, spots 3-5 m in the Fast25 box, 60-s
# episodes, deterministic policy) for three lam_r 2 residuals on the d1 base, paired on dev 4220447:
#   Q     = rally-d1s3cap8hr2 model_36793 (the parent),
#   PRO   = rally-d1s3pro1 model_37392 (D-249: Q + the pro-move drill, 600 iterations),
#   DOSE  = rally-d1s3q8w2c model_37392 (D-248: Q + feed dose, 600 iterations; the same training length without the drill).
# Reported per direction: first-step time (to 1.5 m), sustained 1-s speed toward the spot, peak speed, untimed arrival,
# settled share; falls per 1,000 env-s. No verdict line.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |scripts/stage2_eval.py|scripts/diag/feeder_speed_envelope.py|scripts/diag/footwork_eval.py" > /dev/null && { echo "GPU busy: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand; R=results/agility249
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
declare -A CK=([Q]=$L/2026-11-07_19-25-03_rally-d1s3cap8hr2/model_36793.pt [PRO]=$(ls -d $L/*_rally-d1s3pro1 | tail -1)/model_37392.pt
               [DOSE]=$(ls -d $L/*_rally-d1s3q8w2c | tail -1)/model_37392.pt)
for a in Q PRO DOSE; do [ -f ${CK[$a]} ] || { echo "missing ${CK[$a]}"; exit 1; }; done
for a in PRO Q DOSE; do
  [ -s $R-$a.json ] && continue
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-G1 \
    --checkpoint ${CK[$a]} --envs 1024 --seconds 120 --seed 4220447 --move-prob 1.0 --json $R-$a.json > $R-$a.log 2>&1
done
python - <<'PY' | tee $R-summary.txt
import json, os
from picklebot_mj import bodyspeed_rule as bsr
ARMS = ("Q", "PRO", "DOSE")
def med(h, b):  # median of a histogram (bin width b), seconds
    n = sum(h); c = 0
    for i, x in enumerate(h):
        c += x
        if n and c >= n / 2:
            return (i + 0.5) * b
    return float("nan")
out = {}
for a in ARMS:
    p = f"results/agility249-{a}.json"
    if not os.path.exists(p):
        print(f"{a}: no read ({p})"); continue
    d = json.load(open(p)); c = d["move_drill"]["footwork"]; s = bsr.sectors(c)
    fs = c.get("first_step_hist"); fb = c.get("first_step_bin_s", 0.05)
    fin = [x["arrived"] + x["timed_out"] + x["fell"] for x in s]
    out[a] = {"falls": 1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]),
              "first": [med(fs[i], fb) if fs else float("nan") for i in range(8)],
              "first_n": [sum(fs[i]) if fs else 0 for i in range(8)],
              "sus": [x["sustained_p50"] for x in s], "sus90": [x["sustained_p90"] for x in s], "peak": [x["peak_p50"] for x in s],
              "arr": [x["arrival"] for x in s], "settled": [c["settled"][i] / max(1, f) for i, f in enumerate(fin)],
              "spots": [x["spots"] for x in s], "names": [x["name"] for x in s]}
names = next(iter(out.values()))["names"] if out else []
print("Measure60 bridge drill (spots 3-5 m), dev 4220447, deterministic; per direction: first step to 1.5 m (s, median) / "
      "sustained speed p50 (m/s) / untimed arrival")
for i, nm in enumerate(names):
    print(f"  {nm:13s} " + "  ".join(f"{a} {out[a]['first'][i]:.2f}s {out[a]['sus'][i]:.2f} {out[a]['arr'][i]:.3f}" for a in out))
for a in out:
    o = out[a]
    lb = [2, 3, 4]
    print(f"{a}: falls {o['falls']:.2f} per 1,000 env-s; left/back-left/back first step {sum(o['first'][i] for i in lb) / 3:.2f} s, "
          f"sustained {sum(o['sus'][i] for i in lb) / 3:.2f} m/s, peak {sum(o['peak'][i] for i in lb) / 3:.2f} m/s; "
          f"all-direction first step {sum(o['first']) / 8:.2f} s, sustained {sum(o['sus']) / 8:.2f} m/s (p90 {sum(o['sus90']) / 8:.2f}), "
          f"arrival {sum(o['arr']) / 8:.3f}, settled {sum(o['settled']) / 8:.3f}; first-step spots {sum(o['first_n'])}")
json.dump(out, open("results/agility249-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/agility249.done
