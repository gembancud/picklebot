#!/usr/bin/env bash
# Footwork phase step 2, route D: H0 fine-tune h0-fw-02 (D-186, panel round 55: O1 weight 0.5 -> 2.0, 4 of 5). Frozen
# before launch. As h0_fw01.sh (D-185) with: task ...-Root1W2- (the one change: motion_global_root_pos weight 2.0, std 1.0);
# training seed 174 (smoke 175); a held-out footwork read (clips recorded with training seed 176, accepted by
# amass_g1_import unchanged, never trained on; clip list sha256 frozen before training); kill reads on 4220230 (fw) /
# 4220231 (tl) with h0fw_rule.kill(d_lafan_min=0.82, lafan_succ_drop=0.05); endpoint reads 4220222 (fw), 4220223 /
# 4220224 (tl), 4220232 (fwHO, child only) with h0fw_rule.endpoint(ho=...). Original h0_fw01.sh header follows.
# --- h0_fw01.sh (D-185, panel round 54), as adapted here:
#   Task Picklebot-Tracking-TennisLafan3FF-Root1-Huge-G1: tennis-lafan3 + footwork-fast (shares 0.5 / 0.125 / 0.125 /
#   0.25), ONE objective change O1 (motion_global_root_pos std 0.3 -> 1.0). Parent s5c-03b model_63300, stock PPO fixed
#   1e-5 (as the parent), 4,096 envs, training seed 172 [h0-fw-02: 174]; 3,000 iterations as two segments with a paired kill read at +900:
#     seg 1: h0-fw-02 (+900, to model_64200); kill reads; seg 2: h0-fw-02b (+2,100, to model_66300); endpoint reads.
#   Reads (tracking_eval.py --per-stroke, 4 repeats, mean actions, travel instrument), child and parent paired per seed:
#     kill: footwork-fast 4220230, tennis-lafan3 4220231; endpoint: footwork-fast 4220222, tennis-lafan3 4220223 + 4220224.
#   Rule: picklebot_mj/h0fw_rule.py (kill(): KILL / CONTINUE / INSTRUMENT; endpoint(): H0F-PASS / -RETENTION / -FAIL /
#   -PARTIAL). Output results/h0fw02-{kill,endpoint}.txt / .json. Usage: h0_fw01.sh [smoke]
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
L=artifacts/train/logs/picklebot_tracking
PRUN=2026-10-14_18-52-53_s5c-03b-h0mirror; PCK=model_63300.pt; PARENT=$L/$PRUN/$PCK
T=Picklebot-Tracking-TennisLafan3FF-Root1W2-Huge-G1
ALG="--agent.algorithm.schedule fixed --agent.algorithm.learning-rate 1e-5"
R=results/h0fw02
[ -f $PARENT ] || { echo "missing parent"; exit 1; }
# held-out footwork clips (training seed 176; never trained on), frozen before training
HO=artifacts/motion/footwork-fast-ho
if [ ! -s $HO/footwork-fast.npz ] && [ "${1:-}" != smoke ]; then
  SPEC=artifacts/train/logs/picklebot_return_stand/2026-10-31_01-16-15_fw1b-S/model_16600.pt
  python scripts/motion/record_policy_clips.py --checkpoint $SPEC --out $HO/csv --task Picklebot-Footwork-Specialist-Settle-G1 \
    --envs 64 --seconds 30 --min-seconds 6 --seed 176 --prefix fwfast 2>&1 | tail -1 | tee $R-ho-record.txt
  python -I - $HO <<'PY'
import sys, pathlib, numpy as np
o = pathlib.Path(sys.argv[1]); raw = o / "raw" / "g1"; raw.mkdir(parents=True, exist_ok=True)
for f in sorted((o / "csv").glob("*.csv")):
    np.save(raw / f"{f.stem}_50_jpos.npy", np.loadtxt(f, delimiter=","))
PY
  python -I scripts/motion/amass_g1_import.py --src $HO/raw --out $HO/accepted | tail -1 | tee -a $R-ho-record.txt
  python scripts/motion/csv_to_npz_local.py $HO/accepted $HO/src0.npz --input-fps 30 --output-fps 50 2>&1 | tail -1
  python -I - $HO <<'PY'
import sys, numpy as np
d = dict(np.load(f"{sys.argv[1]}/src0.npz")); d["clip_source"] = np.ones(len(d["clip_starts"]), dtype=int)
np.savez(f"{sys.argv[1]}/footwork-fast.npz", **d); print(len(d["clip_starts"]), "held-out clips")
PY
  sha256sum $HO/accepted/accepted.json $HO/footwork-fast.npz | tee $R-ho-sha256.txt
fi
if [ "${1:-}" = smoke ]; then
  PICKLEBOT_ENVS=256 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh h0-fw2-smoke $T --agent.seed 175 \
    --agent.max-iterations 5 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
  cat artifacts/train/h0-fw2-smoke.exit.json; d=$(ls -d $L/*_h0-fw2-smoke | tail -1)
  grep -n "motion_global_root_pos:" -A8 $d/params/env.yaml | grep "std"; grep -n "source_shares" -A5 $d/params/env.yaml | head -6
  exit 0
fi
read_pair() {  # tag child_ck task seed
  local tag=$1 ck=$2 task=$3 seed=$4
  for who in child parent; do
    local c=$ck; [ $who = parent ] && c=$PARENT
    [ -s $R-$tag-$who.json ] || python scripts/motion/tracking_eval.py --checkpoint $c --task $task --per-stroke --repeats 4 \
      --seed $seed --json $R-$tag-$who.json > $R-$tag-$who.log 2>&1 || { echo "read $tag $who failed"; return 1; }
  done
}
last_ck() { ls $(ls -d $L/*_$1 | tail -1)/model_*.pt | sort -V | tail -1; }
# segment 1
if [ ! -f artifacts/train/h0-fw-02.exit.json ]; then
  PICKLEBOT_WALL_CAP=3000 bash scripts/train_run.sh h0-fw-02 $T --agent.seed 174 --agent.max-iterations 900 \
    --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
fi
echo "seg 1: $(cat artifacts/train/h0-fw-02.exit.json)"
CK1=$(last_ck h0-fw-02); echo "kill checkpoint $CK1"
read_pair killfw $CK1 Picklebot-Tracking-FootworkFast-G1 4220230 || exit 1
read_pair killtl $CK1 Picklebot-Tracking-TennisLafan3-Huge-G1 4220231 || exit 1
python - <<'PY' | tee results/h0fw02-kill.txt
import json
from picklebot_mj import h0fw_rule as r
L = lambda t: json.load(open(f"results/h0fw02-{t}.json"))  # noqa: E731
v, lines = r.kill(L("killfw-child"), L("killfw-parent"), L("killtl-child"), L("killtl-parent"), d_lafan_min=0.82,
                  lafan_succ_drop=0.05)
for line in lines:
    print("  " + line)
print("KILL CHECK:", v)
json.dump({"verdict": v, "lines": lines}, open("results/h0fw02-kill.json", "w"), indent=1)
PY
grep -q "KILL CHECK: CONTINUE" results/h0fw02-kill.txt || { echo "stopped at the kill check"; echo done > artifacts/train/h0fw02.done; exit 0; }
# segment 2
RUN1=$(basename "$(ls -d $L/*_h0-fw-02 | tail -1)")
if [ ! -f artifacts/train/h0-fw-02b.exit.json ]; then
  PICKLEBOT_WALL_CAP=6500 bash scripts/train_run.sh h0-fw-02b $T --agent.seed 174 --agent.max-iterations 2100 \
    --agent.resume True --agent.load-run $RUN1 --agent.load-checkpoint $(basename $CK1) $ALG
fi
echo "seg 2: $(cat artifacts/train/h0-fw-02b.exit.json)"
CK2=$(last_ck h0-fw-02b); echo "endpoint checkpoint $CK2"
read_pair endfw $CK2 Picklebot-Tracking-FootworkFast-G1 4220222 || exit 1
read_pair endtl1 $CK2 Picklebot-Tracking-TennisLafan3-Huge-G1 4220223 || exit 1
read_pair endtl2 $CK2 Picklebot-Tracking-TennisLafan3-Huge-G1 4220224 || exit 1
[ -s $R-endho-child.json ] || python scripts/motion/tracking_eval.py --checkpoint $CK2 --task Picklebot-Tracking-FootworkFastHO-G1 \
  --per-stroke --repeats 4 --seed 4220232 --json $R-endho-child.json > $R-endho-child.log 2>&1 || { echo "read endho failed"; exit 1; }
python - <<'PY' | tee results/h0fw02-endpoint.txt
import json
from picklebot_mj import h0fw_rule as r
L = lambda t: json.load(open(f"results/h0fw02-{t}.json"))  # noqa: E731
v, lines = r.endpoint(L("endfw-child"), L("endfw-parent"), [L("endtl1-child"), L("endtl2-child")],
                      [L("endtl1-parent"), L("endtl2-parent")], ho=L("endho-child"))
for line in lines:
    print("  " + line)
print("ENDPOINT:", v)
json.dump({"verdict": v, "lines": lines}, open("results/h0fw02-endpoint.json", "w"), indent=1)
PY
echo done > artifacts/train/h0fw02.done
