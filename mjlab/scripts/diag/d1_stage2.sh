#!/usr/bin/env bash
# D-194 d1 stage 2 (D-193 rulings; panel round 61 amendments): 22b's residual re-climbed on the d1 base. One change
# against rally 22b: the frozen base (PICKLEBOT_RES_BASE = s5c-d1-fw1bS model_32854 instead of RES_BASE model_32874).
# Runs only if results/d1r-summary.json reads BASE-PASS. 22b's task and overrides, ScheduledPPO at 1e-4 constant (22b's
# model_30200 itself trained at constant 1e-4: its cooldown began at 32200), KL guard 0.05, std floor 0.1, critic warm-up
# 0 (as 22b), 12,288 envs; from 22b model_30200, 1,200 iterations (fixed endpoint model_31399), training seed 186, smoke
# 187 (22b's smoke checks plus base_checkpoint and save_interval 40).
# Pre-training reads: zero-shot on dev 4220257, both arms (22b on its own base and on the d1 base): pairs + Measure60-
# RallyLamR2, reported (with s2_arrive_kill printed); 22b on its own base on Measure60-RallyLamR2 at dev 4220258, the
# KILL-NO-ARRIVE falls reference.
# Kill at +360 (picklebot_mj/d1_rule.py): KILL-UNSTABLE / KILL-NO-HIT from the training log against 22b's 30100-30199;
# KILL-NO-ARRIVE from model_30560's Measure60-RallyLamR2 read (dev 4220258), D-188 validity against 22b's read.
# Endpoint, paired (parent = 22b model_30200 on its own base, env unset; child on the d1 base): pairs (contact hand-off,
# 2,048 envs, 120 s) 4220259, pairs with a 3 s refeed 4220260 (reported), direction split 4220261, Measure60-RallyLamR2
# 4220262; child h5f_clean_eval battery 4220267-4220282 (court falls); 22b model_30600 (+400 on its own base) pairs 4220259
# and direction split 4220261, reported (the training-time confound). Verdict: rally_check.py d1s2-gate (run verdict vs
# 22b) and d1_rule.agility_verdict (vs 22b) -> D1-PASS / ADOPT-AGILITY-NOT-MET (adopt the child; base-caused only if the
# child also beats the model_30600 read) / PANEL; r19-gate, m1 and target against run 14 reported (expected FAIL).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent|kickstart_h4|stage2_eval|footwork_eval" > /dev/null && { echo "GPU busy: not started"; exit 1; }
python -c "import json, sys; sys.exit(0 if json.load(open('results/d1r-summary.json'))['verdict'] == 'BASE-PASS' else 1)" \
  || { echo "d1 base gate not BASE-PASS: not started"; exit 1; }
RUN=rally-d1s2; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s2; TAG=d1s2
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
[ -f $BASE ] || { echo "missing d1 base $BASE"; exit 1; }
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt; C600=$L/$PRUN/model_30600.pt
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
# pre-training reads
[ -s $R-zeroshot-parent-pairs.json ] || parent python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --seed 4220257 --json $R-zeroshot-parent-pairs.json > $R-pre.log 2>&1
[ -s $R-zeroshot-pairs.json ] || child python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --seed 4220257 --json $R-zeroshot-pairs.json >> $R-pre.log 2>&1
[ -s $R-zeroshot-parent-fw.json ] || python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220257 --json $R-zeroshot-parent-fw.json >> $R-pre.log 2>&1
[ -s $R-zeroshot-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220257 --json $R-zeroshot-fw.json >> $R-pre.log 2>&1
[ -s $R-killref-parent-fw.json ] || python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220258 --json $R-killref-parent-fw.json >> $R-pre.log 2>&1
for f in zeroshot-parent-pairs zeroshot-pairs zeroshot-parent-fw zeroshot-fw killref-parent-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
ld = lambda f: json.load(open(f"results/d1s2-{f}.json"))  # noqa: E731
for arm, pf, ff in (("22b own base", "zeroshot-parent-pairs", "zeroshot-parent-fw"), ("22b on d1 base", "zeroshot-pairs", "zeroshot-fw")):
    p, a = ld(pf)["pairs"], dr.agility(ld(ff))
    print(f"zero-shot {arm} (reported): P(5+) open {rc.p5_open(p)[0]:.4f}; partner legal {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; "
          f"feeder legal {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; Measure60 worst arrival {a['worst_arrival']:.3f}, falls "
          f"{a['falls']:.2f}, sustained L/B {a['sustained_p50'][2]}/{a['sustained_p50'][4]}")
print("zero-shot arrival line (reported): " + dr.s2_arrive_kill(ld("zeroshot-fw"), ld("zeroshot-parent-fw"))[1])
PY
# smoke (22b's checks + base_checkpoint + save_interval)
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T \
    --agent.seed 187 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s2-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s2-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s2-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s2-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s2-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env, agent = open(f"{d}/params/env.yaml").read(), open(f"{d}/params/agent.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
noise = re.search(r"^\s+enable_corruption: true\s*$", env, re.M) is not None
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
saved = re.search(r"^save_interval: 40\s*$", agent, re.M) is not None
ok = not miss and noise and based and saved
print(f"smoke config check: missing {miss}; actor noise on {noise}; base_checkpoint is the d1 base {based}; "
      f"save_interval 40 {saved} -> {'ok' if ok else 'STOP'}")
PY
cat /tmp/d1s2-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s2-smoke.txt)" = 5 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - "$BASE" <<'PY' > $R-kill.txt 2>&1
import glob, json, os, subprocess, sys, time
from picklebot_mj import d1_rule as dr
base = sys.argv[1]
LOG, EXIT, L = "artifacts/train/rally-d1s2.log", "artifacts/train/rally-d1s2.exit.json", "artifacts/train/logs/picklebot_return_stand"
k = None
while k is None:
    if os.path.exists(EXIT):
        print("training ended before the +360 check"); sys.exit(0)
    time.sleep(60)
    try:
        k = dr.s2_train_kill(LOG, 30200, "artifacts/train/rally-22b-readcfg.log", 12288)
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
r = subprocess.run(["python", "scripts/diag/footwork_eval.py", "--checkpoint", ck, "--task", "Picklebot-Footwork-Measure60-RallyLamR2-G1",
                    "--envs", "1024", "--seconds", "120", "--move-prob", "1.0", "--seed", "4220258", "--json", "results/d1s2-kill-fw.json"],
                   env=dict(os.environ, PICKLEBOT_RES_BASE=base), capture_output=True, text=True)
if r.returncode != 0:
    print("KILL READ CRASHED (no kill)"); sys.exit(0)
v, line = dr.s2_arrive_kill(json.load(open("results/d1s2-kill-fw.json")), json.load(open("results/d1s2-killref-parent-fw.json")))
print("+360 " + line)
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
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_31399.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
# endpoint reads (parent first, same seeds)
[ -s $R-parent-early-pairs.json ] || parent python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --seed 4220259 --json $R-parent-early-pairs.json > $R-reads.log 2>&1
[ -s $R-parent-early-pairs3.json ] || parent python scripts/stage2_eval.py --checkpoint $L/$PRUN/$PCK $PA --refeed-delay 3.0 --seed 4220260 --json $R-parent-early-pairs3.json >> $R-reads.log 2>&1
[ -s $R-parent-early-dir.json ] || parent python scripts/diag/feeder_speed_envelope.py --checkpoint $L/$PRUN/$PCK --seed 4220261 --json $R-parent-early-dir.json >> $R-reads.log 2>&1
[ -s $R-parent-fw.json ] || python scripts/diag/footwork_eval.py --checkpoint $L/$PRUN/$PCK $FW --seed 4220262 --json $R-parent-fw.json >> $R-reads.log 2>&1
[ -s $R-c600-pairs.json ] || parent python scripts/stage2_eval.py --checkpoint $C600 $PA --seed 4220259 --json $R-c600-pairs.json >> $R-reads.log 2>&1
[ -s $R-c600-dir.json ] || parent python scripts/diag/feeder_speed_envelope.py --checkpoint $C600 --seed 4220261 --json $R-c600-dir.json >> $R-reads.log 2>&1
[ -s $R-target.json ] || child python scripts/stage2_eval.py --checkpoint $CK $PA --seed 4220259 --json $R-target.json >> $R-reads.log 2>&1
[ -s $R-target-pairs3.json ] || child python scripts/stage2_eval.py --checkpoint $CK $PA --refeed-delay 3.0 --seed 4220260 --json $R-target-pairs3.json >> $R-reads.log 2>&1
[ -s $R-endpoint-dir.json ] || child python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220261 --json $R-endpoint-dir.json >> $R-reads.log 2>&1
[ -s $R-child-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $CK $FW --seed 4220262 --json $R-child-fw.json >> $R-reads.log 2>&1
[ -s results/stage5f-$TAG-summary.json ] || PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220267 > $R-h5f.log 2>&1
for f in parent-early-pairs parent-early-dir parent-fw target endpoint-dir child-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
python scripts/rally_check.py d1s2-gate $R $TAG | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
[ "$RALLY" = 0 ] || [ "$RALLY" = 1 ] || stop "GATE-CRASH-$RALLY"
echo "reported (promotion gate against run 14, expected FAIL):" | tee -a $R-summary.txt
python scripts/rally_check.py r19-gate $R $TAG | tee -a $R-summary.txt
python scripts/rally_check.py m1 $R $TAG | tee -a $R-summary.txt
python scripts/rally_check.py target $R $TAG | tee -a $R-summary.txt
python - $RALLY <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
ld = lambda f: json.load(open(f"results/d1s2-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
av, a = dr.agility_verdict(ld("child-fw"), ld("parent-fw"), spec)
for arm in ("parent", "child"):
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a[arm].items()})
lb = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
for name, pf, df in (("22b model_30200", "parent-early-pairs", "parent-early-dir"), ("22b model_30600 (reported)", "c600-pairs", "c600-dir"),
                     ("child", "target", "endpoint-dir")):
    p = ld(pf)["pairs"]
    print(f"{name}: P(5+) open {rc.p5_open(p)[0]:.4f} {rc.p5_open(p)[1]}; partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; "
          f"feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; left + back feeder contact {lb(ld(df)['directions']):.4f}")
v = dr.s2_verdict(sys.argv[1] == "0", av)
print(f"agility vs 22b: {av} (R_LB {a['parent']['R_LB']:.3f} -> {a['child']['R_LB']:.3f}; first-step L/B no slower "
      f"{a['first_step_ok']}); rally run verdict {'PASS' if sys.argv[1] == '0' else 'not met'}")
json.dump({"agility": a, "agility_verdict": av, "verdict": v}, open("results/d1s2-summary.json", "w"), indent=1, default=str)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s2.done
