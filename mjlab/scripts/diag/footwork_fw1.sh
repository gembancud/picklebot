#!/usr/bin/env bash
# Footwork phase step 1 (D-179): the footwork specialist, a flat joint-space teacher built for speed
# (tasks/footwork_specialist.py). Two arms from the flat walking teacher teacher-move-01 model_15900, 1,500 iterations,
# 4,096 envs, ScheduledPPO 3e-4 (warm-up 50, KL guard 0.05, std floor 0.05):
#   S  (seed 159): Picklebot-Footwork-Specialist-G1 (drill, speed-scaled tracking kernel, posture regime fixed);
#   SA (seed 160): the same plus the AMP style reward (LAFAN1 + mirror + AMASS footwork, weight 0.5).
# Each arm's final checkpoint is then read at learning rate 0 on Picklebot-Footwork-Measure-G1 (spots 3-5 m), 100
# iterations, 4,096 envs, stochastic actions as in training (seeds 161 / 162), the whole read as the window.
# Coded rule (picklebot_mj/footwork_rule.py): bodyspeed_rule.route per arm unchanged (VOID if forward < 1.8 m/s,
# censored > 10 % or an override missing; BODY-OK if left, back, right >= 1.8 m/s, untimed arrival >= 90 % in every
# sector and falls <= 4.157 / 1,000 env-s; BODY-LIMIT if back < 1.3 and (left or right) < 1.3; else MIXED), then
# select(): rank, then min(L, B, R) speed, ties within 0.1 m/s to SA. Output results/fw1-summary.{txt,json}.
# Usage: footwork_fw1.sh [smoke]
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/fw1
FRUN=2026-10-06_10-30-12_teacher-move-01; FCK=model_15900.pt
TS=Picklebot-Footwork-Specialist-G1; TSA=Picklebot-Footwork-Specialist-Style-G1; TM=Picklebot-Footwork-Measure-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_LR_WARMUP=50 PICKLEBOT_LR_TOTAL=0 \
  PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_AGILITY_LOG_EVERY=240
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$FRUN/$FCK ] || { echo "missing parent $L/$FRUN/$FCK"; exit 1; }
SMOKE="${1:-}"
if [ "$SMOKE" = smoke ]; then
  for t in $TS $TSA $TM; do
    PICKLEBOT_LR_PEAK=3e-4 PICKLEBOT_STD_MIN=0.05 PICKLEBOT_AGILITY_LOG=$R-smoke-$t.jsonl PICKLEBOT_AGILITY_LOG_EVERY=24 \
      PICKLEBOT_ENVS=256 PICKLEBOT_WALL_CAP=900 bash scripts/diag/agility_train_run.sh fw1-smoke-$t $t \
      --agent.seed 1 --agent.max-iterations 3 --agent.resume True --agent.load-run $FRUN --agent.load-checkpoint $FCK $ALG
    echo "$t: $(cat artifacts/train/fw1-smoke-$t.exit.json)"; tail -c 400 $R-smoke-$t.jsonl; echo
  done
  exit 0
fi

train() {  # tag task seed
  local tag=$1 task=$2 seed=$3
  [ -s $R-$tag.jsonl ] && { echo "$R-$tag.jsonl exists: not re-run"; return 1; }
  PICKLEBOT_LR_PEAK=3e-4 PICKLEBOT_STD_MIN=0.05 PICKLEBOT_AGILITY_LOG=$R-$tag.jsonl PICKLEBOT_SCHED_LOG=$R-$tag-sched.jsonl \
    PICKLEBOT_STYLE_SAVE=artifacts/train/fw1-$tag-disc.pt PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=9000 \
    bash scripts/diag/agility_train_run.sh fw1-$tag $task \
    --agent.seed $seed --agent.max-iterations 1500 --agent.resume True --agent.load-run $FRUN --agent.load-checkpoint $FCK $ALG
  echo "arm $tag: $(cat artifacts/train/fw1-$tag.exit.json)"
}
measure() {  # tag seed: the arm's last checkpoint at learning rate 0
  local tag=$1 seed=$2 run ck
  run=$(ls -d $L/*_fw1-$tag 2>/dev/null | tail -1); run=$(basename "$run")
  ck=$(ls $L/$run/model_*.pt | sed 's/.*model_//; s/\.pt//' | sort -n | tail -1)
  [ -n "$ck" ] || { echo "no checkpoint for $tag"; return 1; }
  echo "{\"arm\": \"$tag\", \"run\": \"$run\", \"checkpoint\": \"model_$ck.pt\"}" > $R-$tag-measure.parent.json
  PICKLEBOT_LR_PEAK=0 PICKLEBOT_STD_MIN=0 PICKLEBOT_AGILITY_LOG=$R-$tag-measure.jsonl PICKLEBOT_ENVS=4096 \
    PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh fw1-$tag-measure $TM \
    --agent.seed $seed --agent.max-iterations 100 --agent.resume True --agent.load-run $run --agent.load-checkpoint model_$ck.pt $ALG
  echo "measure $tag: $(cat artifacts/train/fw1-$tag-measure.exit.json)"
}
train S $TS 159 && measure S 161
train SA $TSA 160 && measure SA 162
python - <<'PY' | tee $R-summary.txt
import glob, json, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar, footwork_rule as fr
routes, out = {}, {}
for tag in ("S", "SA"):
    try:
        rows = ar.read_rows(f"results/fw1-{tag}-measure.jsonl")
    except FileNotFoundError:
        print(f"{tag}: no measure read"); continue
    c = ar.window(rows, "move", 0.0, 1.0)
    falls = falls_per_1000_env_s(f"artifacts/train/fw1-{tag}-measure.log", envs=4096)[0]
    d = sorted(glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_fw1-{tag}-measure/params/env.yaml"))
    text = open(d[-1]).read() if d else ""
    miss = [k for k, v in (("footwork_drill", "true"), ("deadline_arrival_mode", "first_entry"), ("move_prob", "1.0"),
                           ("episode_length_s", "20.0")) if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
    m = re.search(r"^\s*footwork_dist:[^\n]*\n((?:\s*- .*\n)+)", text, re.M)
    if not m or "3.0" not in m.group(1) or "5.0" not in m.group(1):
        miss.append("footwork_dist")
    for k, f in (("move_track_lin_vel", "fw_track_lin_vel"), ("pose", "fw_posture")):
        if not re.search(rf"^  {k}:\n\s*func: [^\n]*{f}", text, re.M):
            miss.append(f"{k}.func")
    r = fr.route(c, falls, miss)
    routes[tag] = r
    out[tag] = {**r, "config_missing": miss, "falls_per_1000_env_s": falls,
                "parent": json.load(open(f"results/fw1-{tag}-measure.parent.json"))}
    print(f"== arm {tag} ({out[tag]['parent']['run']}/{out[tag]['parent']['checkpoint']}), measure read, {len(rows)} rows")
    print("sector         spots  sustained p50/p90  peak p50  arrival  timed_out  fell  censored")
    f3 = lambda x, nd=2: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
    for s in r["sectors"]:
        print(f"{s['sector']} {s['name']:13s} {s['spots']:6d}   {f3(s['sustained_p50'])}/{f3(s['sustained_p90'])}"
              f"          {f3(s['peak_p50'])}     {f3(s['arrival'], 3)}   {s['timed_out']:6d}   {s['fell']:4d}   {s['censored']:5d}")
    print(f"censored share {f3(r['censored_share'], 4)}, falls per 1,000 env-s {f3(falls, 3)}")
    for line in r["lines"]:
        print("  " + line)
    print(f"VERDICT {tag}: {r['verdict']}\n")
pick, lines = fr.select(routes)
for line in lines:
    print(line)
json.dump({"arms": out, "carried_forward": pick, "select": lines}, open("results/fw1-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw1.done
