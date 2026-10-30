#!/usr/bin/env bash
# Body-speed test (panel round 50, D-177; motion reviewer's option F, least-code form): can the G1 body with the flat
# walking teacher sustain ~2 m/s backward and lateral when asked? The teacher's own task with one change, the internal
# command cap 1.0 -> 2.5 m/s (gain scaled, braking radius 0.83 m), plus what that change needs to be measurable: spots
# 3-5 m away in a box widened past the baseline and sidelines, and 60 s episodes (task Picklebot-Teacher-Move-Fast25-G1,
# tasks/body_speed.py FastMoveDrill; observations, rewards and weights unchanged).
# Fine-tune from the flat walking teacher model_15900: 1,500 iterations, 4,096 envs, 1e-4 (ScheduledPPO, no warm-up,
# KL guard 0.05, critic warm-up 0, std floor 0.05 as arm F), training seed 158; measured over the last 1/8.
# Instrument (PICKLEBOT_BODYSPEED_LOG): per MoveDrill sector, sustained speed = p50 over finished spots of the best 1-s
# mean pelvis ground speed toward the spot; spot peak speed; untimed arrival; censored (episode-limit) and fall counts.
# Pre-registered rule (coded, picklebot_mj/bodyspeed_rule.py):
#   VOID if forward sustained < 1.8 m/s OR censored share > 10 % OR an override is missing from params/env.yaml;
#   BODY-OK if back, left and right >= 1.8 m/s AND untimed arrival >= 90 % in every sector AND falls <= 4.157 / 1,000
#   env-s; BODY-LIMIT if back < 1.3 AND (left < 1.3 OR right < 1.3) m/s; else MIXED.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/bodyspeed54
FRUN=2026-10-06_10-30-12_teacher-move-01; FCK=model_15900.pt
T=Picklebot-Teacher-Move-Fast25-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_STD_MIN=0.05 PICKLEBOT_BODYSPEED_LOG_EVERY=240
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$FRUN/$FCK ] || { echo "missing parent $L/$FRUN/$FCK"; exit 1; }
OUT=$R-K.jsonl
[ -s $OUT ] && { echo "$OUT exists: not re-run"; exit 1; }
PICKLEBOT_BODYSPEED_LOG=$OUT PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=7000 bash scripts/diag/agility_train_run.sh bodyspeed54-K $T \
  --agent.seed 158 --agent.max-iterations 1500 --agent.resume True --agent.load-run $FRUN --agent.load-checkpoint $FCK $ALG
echo "arm K: $(cat artifacts/train/bodyspeed54-K.exit.json)"
[ -s $OUT ] || { echo "arm K wrote no counters"; exit 1; }
python - <<'PY' | tee $R-summary.txt
import glob, json, os, re, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar, bodyspeed_rule as bsr
rows = ar.read_rows("results/bodyspeed54-K.jsonl")
c = ar.window(rows, "body", 7 / 8, 1.0)
log = open("artifacts/train/bodyspeed54-K.log", errors="ignore").read()
blocks = log.split("Learning iteration")
tail = "Learning iteration".join(blocks[-max(1, (len(blocks) - 1) // 8):])  # the last 1/8 of the iterations
with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
    f.write(tail)
falls = falls_per_1000_env_s(f.name, envs=4096)[0]
os.unlink(f.name)
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_bodyspeed54-K/params/env.yaml"))
text = open(d[-1]).read() if d else ""
want = [("move_cmd_max_speed", "2.5"), ("episode_length_s", "60.0"), ("move_prob", "1.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
for k, vals in (("move_dist_range", ("3.0", "5.0")), ("move_spot_box", ("-10.4", "-2.4", "-5.5", "5.5"))):
    m = re.search(rf"^\s*{k}:[^\n]*\n((?:\s*- .*\n)+)", text, re.M)  # dumped as "!!python/tuple" then "- x" lines
    if not m or any(v not in m.group(1) for v in vals):
        miss.append(k)
r = bsr.route(c, falls, miss)
print(f"window: last 1/8 of {len(rows)} rows (steps {rows[0]['step']}-{rows[-1]['step']}); falls over the last 1/8 of iterations")
print("sector         spots  sustained p50/p90  peak p50  arrival  timed_out  fell  censored")
f3 = lambda x, nd=2: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
for s in r["sectors"]:
    print(f"{s['sector']} {s['name']:13s} {s['spots']:6d}   {f3(s['sustained_p50'])}/{f3(s['sustained_p90'])}"
          f"          {f3(s['peak_p50'])}     {f3(s['arrival'], 3)}   {s['timed_out']:6d}   {s['fell']:4d}   {s['censored']:5d}")
print(f"censored share {f3(r['censored_share'], 4)}, falls per 1,000 env-s {f3(falls, 3)}")
print("\nrule:")
for line in r["lines"]:
    print("  " + line)
print(f"VERDICT: {r['verdict']}")
json.dump({**r, "config_missing": miss}, open("results/bodyspeed54-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/bodyspeed54.done
