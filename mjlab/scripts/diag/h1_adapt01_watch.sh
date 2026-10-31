#!/usr/bin/env bash
# D-188 addendum: replacement kill watcher for P1. The watcher inside h1_adapt01.sh mis-read an absent log
# (`grep -c ... || echo 0` printed "0\n0"), skipped its wait and wrote a false CONTINUE before training began. This one
# applies the same frozen line (falls per 1,000 env-s over iterations 101-120 > 0.5 x those over 1-20 -> KILL-NO-ADAPT)
# and overwrites results/h1adapt01-kill.txt. Started before iteration 120.
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
LOG=artifacts/train/h1adapt-01.log; R=results/h1adapt01
n() { local c; c=$(grep -c 'Learning iteration' $LOG 2>/dev/null); echo "${c:-0}"; }
while [ "$(n)" -lt 122 ]; do [ -f artifacts/train/h1adapt-01.exit.json ] && exit 0; sleep 30; done
PICKLEBOT_ENVS=12288 python - <<'PY' > $R-kill.txt 2>&1
import os, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
blocks = open("artifacts/train/h1adapt-01.log", errors="ignore").read().split("Learning iteration")
def rate(a, b):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(blocks[a:b]))
    try:
        return falls_per_1000_env_s(f.name, envs=int(os.environ["PICKLEBOT_ENVS"]))[0]
    finally:
        os.unlink(f.name)
r0, r1 = rate(1, 21), rate(101, 121)
v = "KILL-NO-ADAPT" if r1 > 0.5 * r0 else "CONTINUE"
print(f"falls per 1,000 env-s: iterations 1-20 {r0:.2f}, 101-120 {r1:.2f} -> {v} (replacement watcher, D-188 addendum)")
PY
cat $R-kill.txt
grep -q "KILL-NO-ADAPT" $R-kill.txt && pkill -f "run-name h1adapt-01 "
exit 0
