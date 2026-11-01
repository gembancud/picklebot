"""D-199 addendum: the d1s4 +360 kill watcher, as d1_stage4.sh's inline watcher with the resume offsets fixed (the env
step counter continues from the resumed iteration x 24: child from 31399, the parent d1s3's run from 30200). Same lines.
Usage: python scripts/diag/d1s4_watch.py BASE > results/d1s4-kill.txt"""

import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from picklebot_mj import d1_rule as dr  # noqa: E402

base = sys.argv[1]
LOG, EXIT, L = "artifacts/train/rally-d1s4.log", "artifacts/train/rally-d1s4.exit.json", "artifacts/train/logs/picklebot_return_stand"
START, PARENT_START = 31399, 30200


def rd(p):
    return [json.loads(line) for line in open(p)] if os.path.exists(p) else []


k = None
while k is None:
    if os.path.exists(EXIT):
        print("training ended before the +360 check")
        sys.exit(0)
    time.sleep(60)
    try:
        k = dr.s2_train_kill(LOG, START, "artifacts/train/rally-22b-readcfg.log", 12288)
    except FileNotFoundError:
        pass
print(k[1], flush=True)
kills = [k[0]]
v, line = dr.s4_dose_kill(rd("results/d1s4-ready.jsonl"), START)
print(line, flush=True)
kills.append(v)
v, line = dr.s4_events_kill(rd("results/d1s4-train-share.jsonl"), rd("results/d1s3-train-share.jsonl"), START, PARENT_START)
print(line, flush=True)
kills.append(v)
if any(x != "CONTINUE" for x in kills):
    os.system("pkill -f 'run-name rally-d1s4 '")
    sys.exit(0)
ck = None
while ck is None:
    c = glob.glob(f"{L}/*_rally-d1s4/model_31760.pt")
    ck = c[0] if c else None
    if ck is None and os.path.exists(EXIT):
        print("no +360 checkpoint")
        sys.exit(0)
    time.sleep(30)
time.sleep(30)
r = subprocess.run(["python", "scripts/diag/footwork_eval.py", "--checkpoint", ck, "--task", "Picklebot-Footwork-Measure60-RallyLamR2-G1",
                    "--envs", "1024", "--seconds", "120", "--move-prob", "1.0", "--seed", "4220309", "--json", "results/d1s4-kill-fw.json"],
                   env=dict(os.environ, PICKLEBOT_RES_BASE=base), capture_output=True, text=True)
if r.returncode != 0:
    print("KILL READ CRASHED (no kill)")
    sys.exit(0)
v, line = dr.s3_speed_kill(json.load(open("results/d1s4-kill-fw.json")), json.load(open("results/d1s4-killref-parent-fw.json")))
print("+360 " + line.replace(" vs Z ", " vs parent ").replace("x Z", "x parent").replace("Z -", "parent -"))
if v != "CONTINUE":
    os.system("pkill -f 'run-name rally-d1s4 '")
