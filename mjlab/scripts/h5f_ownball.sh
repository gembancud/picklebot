#!/usr/bin/env bash
# Self-play readiness R2 (D-116, selfplay-readiness.md): own-ball returns. Usage: h5f_ownball.sh RUN CKFILE TAG I
#   1. record: the rally evaluation protocol (court task, no hint, rally feeds, 1024 envs, 90 s) on seed 4215000+I saves
#      the post-contact (pos, vel, spin) of every legal return -> results/selfplay-r2-TAG-returns.pt
#   2. replay: the court task with every feed one of those returns mirrored to the far side (rally phase), 1024 envs,
#      40 s, seed 4215100+I -> results/selfplay-r2-TAG.json; bar: legal >= 0.70 and Wilson low >= 0.65 (>= 1,000 balls)
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; I=$4; R=results/selfplay-r2-$TAG; T=Picklebot-Latent-Court-Res-G1
A="--task $T --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint"
bash scripts/stage2_eval.sh $RUN $CK $A --envs 1024 --seconds 90 --rally --seed $((4215000 + I)) \
  --record-returns $PWD/$R-returns.pt --json $R-record.json > /tmp/r2_$TAG.log 2>&1; echo "record: $?"
bash scripts/stage2_eval.sh $RUN $CK $A --envs 1024 --seconds 40 --rally --seed $((4215100 + I)) \
  --replay-file $PWD/$R-returns.pt --json $R.json > /tmp/r2_$TAG.log 2>&1; echo "replay: $?"
~/envs/picklebot-mj/bin/python - "$R" <<'PY'
import json, sys
d = json.load(open(sys.argv[1] + ".json"))
n, k = d["episodes"], d["legal_returns"]
lo = d["legal_return_ci95"][0]
print(f"R2 {sys.argv[1]}: legal {k}/{n} = {k / max(n, 1):.4f} (Wilson low {lo}); recorded states {d['replay']['states']}; "
      f"feeds ended by a fall {d['falls']} of {n} ({d['falls'] / max(n, 1):.4f} per shot); "
      f"pass: {k / max(n, 1) >= 0.70 and lo >= 0.65 and n >= 1000}")
PY
