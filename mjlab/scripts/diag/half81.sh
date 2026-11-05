#!/usr/bin/env bash
# D-218 (panel round 81, (iv) reads only). C = rally-d1s3lr3 model_32598, pairs read (2,048 envs, refeed 0.5 s, mean
# actions). Experiment design's route: --seconds 120 and --seconds 240 on dev 4220369-4220370; the second half is the
# 240-s read minus the 120-s read (d1_rule.spawn_route: SPAWN-BINDS -> (ii) episode length; MID-BINDS -> post-bounce
# cut; else PANEL). Reported only (motion): the same 120-s read with --audit-fixes on dev 4220371-4220372 (pair-reset
# leak, audit 2026-10-28), compared with dist80b's 4220366-67 without the fixes.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/half81; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
echo "D-218: C = $P; 120 s / 240 s on dev 4220369-4220370; --audit-fixes 120 s on dev 4220371-4220372 (reported)" > $R-summary.txt
for s in 4220369 4220370; do
  [ -s $R-t120-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seconds 120 --seed $s --json $R-t120-$s.json >> $R-reads.log 2>&1
  [ -s $R-t240-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seconds 240 --seed $s --json $R-t240-$s.json >> $R-reads.log 2>&1
done
for s in 4220371 4220372; do
  [ -s $R-audit-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seconds 120 --audit-fixes --seed $s --json $R-audit-$s.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/half81"
def dh(tag, seeds):
    fs = [f"{R}-{tag}-{s}.json" for s in seeds]
    if not all(os.path.exists(f) for f in fs):
        return None
    js = [json.load(open(f)) for f in fs]
    return [sum(sum(j["launch_state"]["d_hist"][k][b] for k in range(3)) for j in js) for b in range(7)], js
a, b = dh("t120", (4220369, 4220370)), dh("t240", (4220369, 4220370))
if a is None or b is None:
    print("RESULT EVAL-FAIL"); sys.exit(0)
v, lines = dr.spawn_route(a[0], b[0])
print("\n".join(lines))
for name, (h, js) in (("120 s", a), ("240 s", b)):
    p5 = dr.pooled_pairs([f"{R}-{'t120' if name == '120 s' else 't240'}-{s}.json" for s in (4220369, 4220370)])
    print(f"(reported) {name}: P(5+) {p5['p5']:.4f}, feeder legal {p5['feeder']:.4f}, rallies {p5['rallies']}")
c = dh("audit", (4220371, 4220372))
if c is not None:
    q = dr.pooled_pairs([f"{R}-audit-{s}.json" for s in (4220371, 4220372)])
    qb = dr.pooled_pairs([f"results/dist80b-C-pairs-{s}.json" for s in (4220366, 4220367)])
    print(f"(reported, motion) --audit-fixes 120 s: off-spot share {c[0][-1] / max(sum(c[0]), 1):.4f}; P(5+) {q['p5']:.4f}, "
          f"feeder legal {q['feeder']:.4f}, rallies {q['rallies']}; without fixes (dist80b): P(5+) {qb['p5']:.4f}, "
          f"feeder legal {qb['feeder']:.4f}, rallies {qb['rallies']}")
json.dump({"route": v, "first": a[0], "full": b[0]}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {v}")
PY
echo "VERDICT: $(tail -1 $R-summary.txt | cut -d' ' -f2)" | tee -a $R-summary.txt
echo done > artifacts/train/half81.done
