#!/usr/bin/env bash
# Stage 5E paired final evaluation (D-106): the named candidate and run 22 on the same four fresh dev seeds for drill v2
# (noisy planner spot, sim-to-real on, 90 s rallies; pooled per-shot p, groups with Wilson intervals, P(rally >= 5/10)),
# the candidate's court drill on four more seeds (pooled per cell), then the candidate's Stage 5C battery once.
# Usage: h5e_final.sh RUN CKFILE TASK_V2 TASK_COURT TASK_5B "V2 SEEDS x4" "COURT SEEDS x4" BATTERY_SEED
#   -> results/stage5e-final-*.json
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TV2=$3; TC=$4; T5B=$5; V2S=($6); CS=($7); BS=$8; P=~/envs/picklebot-mj/bin/python; R=results/stage5e-final
A="--envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy"
C="--envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
for i in 0 1 2 3; do
  bash scripts/stage2_eval.sh $RUN $CK --task $TV2 $A --seed ${V2S[$i]} --json $R-cand-v2-$i.json > /tmp/f5e.log 2>&1; echo "cand v2 $i: $?"
  bash scripts/stage2_eval.sh s5c-22-res-rally model_900.pt --task Picklebot-Latent-Court-V2-Res-G1 $A --seed ${V2S[$i]} --json $R-base-v2-$i.json > /tmp/f5e.log 2>&1; echo "base v2 $i: $?"
  bash scripts/stage2_eval.sh $RUN $CK --task $TC $C --seed ${CS[$i]} --json $R-cand-court-$i.json > /tmp/f5e.log 2>&1; echo "cand court $i: $?"
done
$P scripts/h5c_pool.py $R-cand-court-pooled.json $R-cand-court-[0-3].json
$P - "$R" <<'PY'
import json, math, sys
R = sys.argv[1]
def wilson(k, n, z=1.96):
    if n == 0: return [0.0, 0.0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]
out = {}
for who in ("cand", "base"):
    k = n = r10 = f10 = r5 = f5 = 0
    g = {}
    for i in range(4):
        d = json.load(open(f"{R}-{who}-v2-{i}.json"))
        k += d["legal_returns"]; n += d["episodes"]
        r = d["rally"]; r10 += r["reached"]; f10 += r["ended_below_n"]; r5 += r["reached_5"]; f5 += r["ended_below_5"]
        for name, x in d["drill_v2"]["groups"].items():
            kg = round(x["legal_return"] * x["episodes"])
            a = g.setdefault(name, [0, 0]); a[0] += kg; a[1] += x["episodes"]
    out[who] = {"per_shot_p": round(k / max(n, 1), 4), "per_shot_ci95": wilson(k, n), "feeds": n,
                "groups": {name: {"legal_return": round(a[0] / max(a[1], 1), 4), "ci95": wilson(*a), "feeds": a[1]}
                           for name, a in g.items()},
                "p_rally5": round(r5 / max(r5 + f5, 1), 4), "p_rally5_ci95": wilson(r5, r5 + f5),
                "p_rally10": round(r10 / max(r10 + f10, 1), 4), "p_rally10_ci95": wilson(r10, r10 + f10)}
json.dump(out, open(f"{R}-v2-pooled.json", "w"), indent=1)
print(json.dumps(out))
PY
bash scripts/h5c_eval.sh $RUN $CK final5e-cand $BS $TC $T5B
