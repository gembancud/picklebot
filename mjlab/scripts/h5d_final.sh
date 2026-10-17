#!/usr/bin/env bash
# Stage 5D paired final evaluation (D-091): the named candidate and the stage start (run 22) on the same four fresh dev
# seeds S..S+3 for the rally evaluation (90 s, court-anchored, no hint; pooled: P(rally >= 10) over all ended or
# completed rallies) and the court drill (pooled per cell), then the candidate's other gate jobs once (h5c_eval).
# Usage: h5d_final.sh RUN CKFILE TASK TASK5B SEED   -> results/stage5d-final-*.json
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; T=$3; T5B=$4; S=$5; P=~/envs/picklebot-mj/bin/python; R=results/stage5d-final
RA="--envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally"
C="--envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
for i in 0 1 2 3; do
  bash scripts/stage2_eval.sh $RUN $CK --task $T $RA --seed $((S+i)) --json $R-cand-rally-$i.json > /tmp/f5d.log 2>&1; echo "cand rally $i: $?"
  bash scripts/stage2_eval.sh s5c-22-res-rally model_900.pt --task Picklebot-Latent-Court-Res-G1 $RA --seed $((S+i)) --json $R-base-rally-$i.json > /tmp/f5d.log 2>&1; echo "base rally $i: $?"
  bash scripts/stage2_eval.sh $RUN $CK --task $T $C --seed $((S+10+i)) --json $R-cand-court-$i.json > /tmp/f5d.log 2>&1; echo "cand court $i: $?"
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
    reached = failed = 0; legal = []
    for i in range(4):
        d = json.load(open(f"{R}-{who}-rally-{i}.json"))
        reached += d["rally"]["reached"]; failed += d["rally"]["ended_below_n"]; legal.append(d["legal_return_rate"])
    out[who] = {"p_rally10": round(reached / max(reached + failed, 1), 4), "ci95": wilson(reached, reached + failed),
                "reached": reached, "ended_below": failed, "legal_mean": round(sum(legal) / 4, 4)}
json.dump(out, open(f"{R}-rally-pooled.json", "w"), indent=1)
print(json.dumps(out))
PY
bash scripts/h5c_eval.sh $RUN $CK final5d-cand $((S+20)) $T $T5B
