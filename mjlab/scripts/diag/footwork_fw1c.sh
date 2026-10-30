#!/usr/bin/env bash
# Footwork phase step 1, third attempt (D-181, panel round 51: A 4 of 5): pay the arrival bonus at the HELD arrival of a
# spot first entered before its deadline (Picklebot-Footwork-Specialist-Settle-G1; the one change), continued from fw1b
# arm S (2026-10-31_01-16-15_fw1b-S/model_16600, its optimizer) with fw1b's algorithm (rsl_rl PPO, adaptive, desired KL
# 0.01, initial rate 1e-5), 1,500 iterations, 4,096 envs, training seed 168.
# Instrument (fixed before launch, D-181): sustained speed over full 1-s windows only; reads on
# Picklebot-Footwork-Measure60-G1 (60-s episodes, spots 3-5 m), learning rate 0, 300 iterations, stochastic actions:
#   B0 (seed 170): model_16600 re-read on the fixed instrument (baseline, reported);
#   A  (seed 169): arm A's last checkpoint.
# Kill lines, enforced by picklebot_mj/footwork_watch.py while A trains: VOID-unstable (falls > 8.314 / 1,000 env-s over
# the last 100 iterations after iteration 100), KILL-no-settle (untimed arrival < 50 % over a 100-iteration window
# starting at >= 200), KILL-speed-traded (min(L, B, R) sustained p50 < 1.3 m/s, same window). Endpoint: bodyspeed_rule
# unchanged on A's read. Output results/fw1c-summary.{txt,json}.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/fw1c
PRUN=2026-10-31_01-16-15_fw1b-S; PCK=model_16600.pt
TA=Picklebot-Footwork-Specialist-Settle-G1; TM=Picklebot-Footwork-Measure60-G1
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_AGILITY_LOG_EVERY=240 PICKLEBOT_ENVS=4096
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }

measure() {  # tag seed run checkpoint
  local tag=$1 seed=$2 run=$3 ck=$4
  [ -s $R-$tag.jsonl ] && { echo "$R-$tag.jsonl exists: not re-run"; return 1; }
  echo "{\"read\": \"$tag\", \"run\": \"$run\", \"checkpoint\": \"$ck\"}" > $R-$tag.parent.json
  PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=50 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_STD_MIN=0 \
    PICKLEBOT_AGILITY_LOG=$R-$tag.jsonl PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh fw1c-$tag $TM \
    --agent.seed $seed --agent.max-iterations 300 --agent.resume True --agent.load-run $run --agent.load-checkpoint $ck \
    --agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO
  echo "read $tag: $(cat artifacts/train/fw1c-$tag.exit.json)"
}

measure B0 170 $PRUN $PCK
if [ ! -s $R-A.jsonl ]; then
  python -m picklebot_mj.footwork_watch fw1c-A $R-A.jsonl artifacts/train/fw1c-A.log $R-A-kill.json &
  PICKLEBOT_AGILITY_LOG=$R-A.jsonl PICKLEBOT_WALL_CAP=9000 bash scripts/diag/agility_train_run.sh fw1c-A $TA \
    --agent.seed 168 --agent.max-iterations 1500 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK \
    --agent.algorithm.learning-rate 1e-5
  echo "arm A: $(cat artifacts/train/fw1c-A.exit.json)"; wait
  [ -s $R-A-kill.json ] && echo "arm A killed: $(cat $R-A-kill.json | tr -d '\n' | cut -c1-300)"
fi
ARUN=$(basename "$(ls -d $L/*_fw1c-A 2>/dev/null | tail -1)")
ACK=$(ls $L/$ARUN/model_*.pt 2>/dev/null | sed 's/.*model_//; s/\.pt//' | sort -n | tail -1)
[ -n "$ACK" ] && measure A 169 $ARUN model_$ACK.pt
python - <<'PY' | tee $R-summary.txt
import glob, json, os, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar, bodyspeed_rule as bsr
out = {"kill": json.load(open("results/fw1c-A-kill.json")) if os.path.exists("results/fw1c-A-kill.json") else None}
for tag in ("B0", "A"):
    try:
        rows = ar.read_rows(f"results/fw1c-{tag}.jsonl")
    except FileNotFoundError:
        print(f"{tag}: no read"); continue
    c = ar.window(rows, "move", 0.0, 1.0)
    log = f"artifacts/train/fw1c-{tag}.log"
    falls = falls_per_1000_env_s(log, envs=4096)[0]
    std = re.findall(r"Mean action std: ([0-9.]+)", open(log, errors="ignore").read())
    d = sorted(glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_fw1c-{tag}/params/env.yaml"))
    text = open(d[-1]).read() if d else ""
    miss = [k for k, v in (("footwork_drill", "true"), ("footwork_pay", "settled"), ("deadline_arrival_mode", "first_entry"),
                           ("move_prob", "1.0"), ("episode_length_s", "60.0")) if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
    m = re.search(r"^\s*footwork_dist:[^\n]*\n((?:\s*- .*\n)+)", text, re.M)
    if not m or "3.0" not in m.group(1) or "5.0" not in m.group(1):
        miss.append("footwork_dist")
    for k, f in (("move_track_lin_vel", "fw_track_lin_vel"), ("pose", "fw_posture")):
        if not re.search(rf"^  {k}:\n\s*func: [^\n]*{f}", text, re.M):
            miss.append(f"{k}.func")
    r = bsr.route(c, falls, miss)
    parent = json.load(open(f"results/fw1c-{tag}.parent.json"))
    print(f"== read {tag} ({parent['run']}/{parent['checkpoint']}), {len(rows)} rows, action std {std[-1] if std else 'n/a'}")
    print("sector         spots  sustained p50/p90  peak p50  untimed  deadline  settled  settle s  overshoot m  short  fell  cens")
    f3 = lambda x, nd=2: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
    for s in r["sectors"]:
        i = s["sector"]
        fin = s["arrived"] + s["timed_out"] + s["fell"]
        st = c["settled"][i]
        print(f"{i} {s['name']:13s} {s['spots']:6d}   {f3(s['sustained_p50'])}/{f3(s['sustained_p90'])}          "
              f"{f3(s['peak_p50'])}    {f3(s['arrival'], 3)}    {c['deadline'][i] / max(1, fin):.3f}    {st / max(1, fin):.3f}"
              f"    {c['settle_time_sum'][i] / max(1, st):.2f}      {c['overshoot_sum'][i] / max(1, st):.2f}     "
              f"{c['short'][i]:5d} {s['fell']:5d} {s['censored']:5d}")
    print(f"censored share {f3(r['censored_share'], 4)}, falls per 1,000 env-s {f3(falls, 3)}")
    for line in r["lines"]:
        print("  " + line)
    print(f"VERDICT {tag}: {r['verdict']}" + (" (baseline, reported)" if tag == "B0" else "") + "\n")
    out[tag] = {**r, "config_missing": miss, "falls_per_1000_env_s": falls, "parent": parent,
                "action_std": float(std[-1]) if std else None}
if out["kill"]:
    print(f"arm A was killed: {out['kill']['kill']} ({out['kill']['checks']})")
json.dump(out, open("results/fw1c-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw1c.done
