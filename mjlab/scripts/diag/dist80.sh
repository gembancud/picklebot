#!/usr/bin/env bash
# D-216 (panel round 80 / 80b, (vi)): reads only. C = rally-d1s3lr3 model_32598, pairs read (2,048 envs, 120 s, refeed
# 0.5 s, as D-204) on dev 4220366-4220367, at mean actions; plus the same two seeds with --stochastic (training noise on;
# reported only, tests the noise explanation of the practice-vs-read gap). Route on the pooled mean-action reads
# (d1_rule.dist_route): RESTART-BINDS -> (iii-RL) in its own entry; SHOT-BINDS -> STOP to the next phase (d1 base
# unfrozen); otherwise the panel.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/dist80; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
echo "D-216: launch-distance read of C = $P on dev 4220366-4220367 (mean actions; --stochastic reported)" > $R-summary.txt
for s in 4220366 4220367; do
  [ -s $R-C-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --json $R-C-pairs-$s.json >> $R-reads.log 2>&1
  [ -s $R-Cnoise-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --stochastic --json $R-Cnoise-pairs-$s.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
R = "results/dist80"
def pooled(tag):
    fs = [f"{R}-{tag}-pairs-{s}.json" for s in (4220366, 4220367)]
    if not all(os.path.exists(f) for f in fs):
        return None, None
    js = [json.load(open(f)) for f in fs]
    out = [[sum(j["launch_state"]["outcome_by_d"][b][i] for j in js) for i in (0, 1)] for b in range(7)]
    dh = [sum(sum(j["launch_state"]["d_hist"][k][b] for k in range(3)) for j in js) for b in range(7)]
    return out, dh
out, dh = pooled("C")
if out is None:
    print("RESULT EVAL-FAIL"); sys.exit(0)
v, lines = dr.dist_route(out)
print("\n".join(lines))
print(f"(reported) mean actions: off-spot share (d > 1.2) at launch {dh[6] / max(sum(dh), 1):.4f}; feeder legal "
      f"{sum(x[1] for x in out) / max(sum(x[0] for x in out), 1):.4f}")
on, dn = pooled("Cnoise")
if on is not None:
    print(f"(reported) noise on: off-spot share {dn[6] / max(sum(dn), 1):.4f}; feeder legal "
          f"{sum(x[1] for x in on) / max(sum(x[0] for x in on), 1):.4f}; " + dr.dist_route(on)[1][0])
json.dump({"route": v, "out_by_d": out, "d_hist": dh}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {v}")
PY
echo "VERDICT: $(tail -1 $R-summary.txt | cut -d' ' -f2)" | tee -a $R-summary.txt
echo done > artifacts/train/dist80.done
