#!/usr/bin/env bash
# D-234 (panel round 95, (ii) 4 of 5): the R3 premise read. No training.
# Reads R (rally-d1s3dr model_33797, unpromoted), C (rally-d1s3lr3 model_32598, the parent) and the d1 base
# (s5c-d1-fw1bS model_32854 as a zero-residual checkpoint, scripts/residual_init.py, so the read is the base's exact
# behaviour on R3's own instrument) on the h5f court read (Picklebot-Latent-Court-Res-G1, 2,048 envs, 24 s, random recovery,
# every family), dev 4220394 and 4220395, pooled. Each read's fall_log (D-234) books every robot fall by phase (feed in
# play / between feeds), time since the episode start, distance from the recovery spot and family.
# Route (d1_rule.r3_route, R against the base): INVALID (booked falls != robot_falls) / BASE-FAILS (base R3 > 0.04) /
# SPAWN, RECOVERY, FEED (>= 50 % of R's excess per episode in that class) / MIXED. C's route is reported.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/fl95; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
ZR=artifacts/zr/d1-base-zero-residual.pt
CKR=$L/2026-11-06_05-15-42_rally-d1s3dr/model_33797.pt; CKC=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $CKR $CKC; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
[ -f $ZR ] || python scripts/residual_init.py $BASE $ZR
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
echo "D-234: the R3 premise read; base = $ZR (zero residual on $BASE), R = $CKR, C = $CKC; dev 4220394-4220395" > $R-summary.txt
for s in 4220394 4220395; do
  for w in base R C; do
    case $w in base) ck=$ZR;; R) ck=$CKR;; C) ck=$CKC;; esac
    [ -s $R-$w-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $CT --seed $s --json $R-$w-$s.json >> $R-reads.log 2>&1
  done
done
python - >> $R-summary.txt 2>&1 <<'EOF'
import json
from picklebot_mj import d1_rule as dr
def pool(w):
    rs = [json.load(open(f"results/fl95-{w}-{s}.json")) for s in (4220394, 4220395)]
    out = {"robot_episodes": sum(r["robot_episodes"] for r in rs), "robot_falls": sum(r["robot_falls"] for r in rs)}
    out["robot_fall_rate_per_episode"] = out["robot_falls"] / max(out["robot_episodes"], 1)
    fl = dict(rs[0]["fall_log"])
    for k in ("by_t", "by_d", "by_family"):
        fl[k] = [[sum(r["fall_log"][k][p][i] for r in rs) for i in range(len(rs[0]["fall_log"][k][p]))] for p in (0, 1)]
    out["fall_log"] = fl
    for r, s in zip(rs, (4220394, 4220395)):
        print(f"{w} dev {s}: R3 {r['robot_fall_rate_per_episode']:.4f} ({r['robot_falls']} / {r['robot_episodes']})")
    return out
p = {w: pool(w) for w in ("base", "R", "C")}
for w in p:
    fl = p[w]["fall_log"]
    print(f"\n{w}: pooled R3 {p[w]['robot_fall_rate_per_episode']:.4f}; falls in feed / between feeds by 0.5-s bin:")
    print("  feed ", fl["by_t"][0]); print("  betw ", fl["by_t"][1])
    print(f"  by distance from the spot (edges {fl['d_edges']} m): feed {fl['by_d'][0]} betw {fl['by_d'][1]}")
    print("  by family (feed / betw): " + ", ".join(f"{n} {a}/{b}" for n, a, b in zip(fl["families"], *fl["by_family"]) if a + b))
route, txt = dr.r3_route(p["base"], p["R"])
print("\nR against the base:\n" + txt)
rc, txc = dr.r3_route(p["base"], p["C"])
print("\n(reported) C against the base:\n" + txc)
print(f"\nVERDICT: {route}")
EOF
cat $R-summary.txt
echo done > artifacts/train/fl95.done
