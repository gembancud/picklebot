#!/usr/bin/env bash
# D-194 d1 stage 2 (D-193 rulings; experiment design round 59): 22b's residual re-climbed on the d1 base. One change
# against rally 22b: the frozen base (PICKLEBOT_RES_BASE = s5c-d1-fw1bS's endpoint instead of RES_BASE model_32874).
# Runs only if results/d1r-summary.json reads BASE-PASS. 22b's task and overrides, ScheduledPPO 1e-4 constant (no
# cooldown), KL guard 0.05, std floor 0.1, critic warm-up 0, 12,288 envs; from 22b model_30200, 1,200 iterations (fixed
# endpoint), training seed 186, smoke 187 (asserts base_checkpoint and save_interval 40 in params).
# Zero-shot (reported, dev 4220257): 22b model_30200 on the d1 base, pairs read + Measure60-RallyLamR2 read.
# Kill at +360 (picklebot_mj/d1_rule.py): KILL-UNSTABLE / KILL-NO-HIT from the training log against 22b's own log at the
# same iterations since resume; KILL-NO-ARRIVE from the +360 checkpoint's Measure60-RallyLamR2 read (dev 4220258).
# Endpoint, paired (parent = 22b model_30200 on its own base, env unset; child on the d1 base): pairs (contact hand-off,
# 2,048 envs, 120 s) 4220259, pairs with a 3 s refeed 4220260 (reported), direction split 4220261, Measure60-RallyLamR2
# 4220262; child h5f_clean_eval battery 4220267-4220282 (court falls). Verdict: rally_check.py d1s2-gate (run verdict vs
# 22b) and d1_rule.agility_verdict (vs 22b) -> D1-PASS / ADOPT-AGILITY-NOT-MET / PANEL; r19-gate (vs run 14; expected
# FAIL: 22b already fails it), m1 and target reported.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent|kickstart_h4|stage2_eval|footwork_eval" > /dev/null && { echo "GPU busy: not started"; exit 1; }
python -c "import json, sys; sys.exit(0 if json.load(open('results/d1r-summary.json'))['verdict'] == 'BASE-PASS' else 1)" \
  || { echo "d1 base gate not BASE-PASS: not started"; exit 1; }
RUN=rally-d1s2; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s2; TAG=d1s2
BASE=$(ls $(ls -d $L/*_s5c-d1-fw1bS | tail -1)/model_*.pt | sort -V | tail -1); BASE=$(realpath $BASE)
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt; START=30200
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s2.done; exit 0; }
echo "d1 base $BASE" | tee $R-summary.txt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
FW="--task Picklebot-Footwork-Measure60-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
child() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
parent() { PICKLEBOT_LAM_R=2 "$@"; }
# zero-shot (reported)
[ -s $R-zeroshot-pairs.json ] || child python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --seed 4220257 --json $R-zeroshot-pairs.json > $R-zeroshot.log 2>&1
[ -s $R-zeroshot-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220257 --json $R-zeroshot-fw.json >> $R-zeroshot.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
p = json.load(open("results/d1s2-zeroshot-pairs.json"))["pairs"]
a = dr.agility(json.load(open("results/d1s2-zeroshot-fw.json")))
print(f"zero-shot (reported): P(5+) open {rc.p5_open(p)[0]:.4f}; partner legal {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; "
      f"feeder legal {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; Measure60 worst arrival {a['worst_arrival']:.3f}, falls "
      f"{a['falls']:.2f}, sustained L/B {a['sustained_p50'][2]}/{a['sustained_p50'][4]}")
PY
# smoke
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
    --agent.seed 187 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
python - "$(ls -d $L/*_$RUN-smoke | tail -1)" "$BASE" <<'PY' | tee -a $R-summary.txt || stop SMOKE-FAIL
import re, sys
d, base = sys.argv[1], sys.argv[2]
env, agent = open(f"{d}/params/env.yaml").read(), open(f"{d}/params/agent.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("episode_length_s", "120.0"), ("lam_r", "2.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
saved = re.search(r"^save_interval: 40\s*$", agent, re.M) is not None
ok = not miss and based and saved
print(f"smoke: missing {miss}; base_checkpoint is the d1 base {based}; save_interval 40 {saved} -> {'ok' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - "$BASE" <<'PY' > $R-kill.txt 2>&1
import glob, os, subprocess, sys, time
from picklebot_mj import d1_rule as dr
base = sys.argv[1]
LOG, EXIT, L = "artifacts/train/rally-d1s2.log", "artifacts/train/rally-d1s2.exit.json", "artifacts/train/logs/picklebot_return_stand"
k = None
while k is None:
    if os.path.exists(EXIT):
        print("training ended before the +360 check"); sys.exit(0)
    time.sleep(60)
    try:
        k = dr.s2_train_kill(LOG, 30200, "artifacts/train/rally-22b-readcfg.log", 29000, 12288)
    except FileNotFoundError:
        pass
print(k[1], flush=True)
if k[0] != "CONTINUE":
    os.system("pkill -f 'run-name rally-d1s2 '"); sys.exit(0)
ck = None
while ck is None:
    c = glob.glob(f"{L}/*_rally-d1s2/model_30560.pt")
    ck = c[0] if c else None
    if ck is None and os.path.exists(EXIT):
        print("no +360 checkpoint"); sys.exit(0)
    time.sleep(30)
time.sleep(30)
env = dict(os.environ, PICKLEBOT_RES_BASE=base)
r = subprocess.run(["python", "scripts/diag/footwork_eval.py", "--checkpoint", ck, "--task", "Picklebot-Footwork-Measure60-RallyLamR2-G1",
                    "--envs", "1024", "--seconds", "120", "--move-prob", "1.0", "--seed", "4220258", "--json", "results/d1s2-kill-fw.json"],
                   env=env, capture_output=True, text=True)
if r.returncode != 0:
    print("KILL READ CRASHED (no kill)"); sys.exit(0)
import json
v, line = dr.s2_arrive_kill(json.load(open("results/d1s2-kill-fw.json")))
print(line)
if v != "CONTINUE":
    os.system("pkill -f 'run-name rally-d1s2 '")
PY
  ) &
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 \
    bash scripts/train_run.sh $RUN $T --agent.seed 186 --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN \
    --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "$(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1)"
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
# endpoint reads (parent first, same seeds)
[ -s $R-parent-early-pairs.json ] || parent python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --seed 4220259 --json $R-parent-early-pairs.json > $R-reads.log 2>&1
[ -s $R-parent-early-pairs3.json ] || parent python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --refeed-delay 3.0 --seed 4220260 --json $R-parent-early-pairs3.json >> $R-reads.log 2>&1
[ -s $R-parent-early-dir.json ] || parent python scripts/diag/feeder_speed_envelope.py --checkpoint $L/$PRUN/$PCK --seed 4220261 --json $R-parent-early-dir.json >> $R-reads.log 2>&1
[ -s $R-parent-fw.json ] || python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220262 --json $R-parent-fw.json >> $R-reads.log 2>&1
[ -s $R-target.json ] || child python scripts/stage2_eval.py --checkpoint $CK $PA --seed 4220259 --json $R-target.json >> $R-reads.log 2>&1
[ -s $R-target-pairs3.json ] || child python scripts/stage2_eval.py --checkpoint $CK $PA --refeed-delay 3.0 --seed 4220260 --json $R-target-pairs3.json >> $R-reads.log 2>&1
[ -s $R-endpoint-dir.json ] || child python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220261 --json $R-endpoint-dir.json >> $R-reads.log 2>&1
[ -s $R-child-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $CK $FW --seed 4220262 --json $R-child-fw.json >> $R-reads.log 2>&1
[ -s results/stage5f-$TAG-summary.json ] || PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220267 > $R-h5f.log 2>&1
for f in parent-early-pairs parent-early-dir parent-fw target endpoint-dir child-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
python scripts/rally_check.py d1s2-gate $R $TAG | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
echo "reported (promotion gate against run 14, expected FAIL):" | tee -a $R-summary.txt
python scripts/rally_check.py r19-gate $R $TAG | tee -a $R-summary.txt
python scripts/rally_check.py m1 $R $TAG | tee -a $R-summary.txt
python scripts/rally_check.py target $R $TAG | tee -a $R-summary.txt
python - $RALLY <<'PY' | tee -a $R-summary.txt
import json, sys
from picklebot_mj import d1_rule as dr
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
av, a = dr.agility_verdict(json.load(open("results/d1s2-child-fw.json")), json.load(open("results/d1s2-parent-fw.json")), spec)
for arm in ("parent", "child"):
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a[arm].items()})
v = dr.s2_verdict(sys.argv[1] == "0", av)
print(f"agility vs 22b: {av} (R_LB {a['parent']['R_LB']:.3f} -> {a['child']['R_LB']:.3f}; first-step L/B no slower "
      f"{a['first_step_ok']}); rally run verdict {'PASS' if sys.argv[1] == '0' else 'not met'}")
json.dump({"agility": a, "agility_verdict": av, "verdict": v}, open("results/d1s2-summary.json", "w"), indent=1, default=str)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s2.done
