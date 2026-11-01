#!/usr/bin/env bash
# D-196 d1s3 (panel round 62: motion, RL, architecture): stage 2 (D-194) with one change, the move-episode speed reward
# (Picklebot-Rally22b-FastMove-G1: in move episodes the command cap is 2.5 m/s and the kernel std 0.5 x max(1, |v_cmd|);
# everything else is 22b's task). From 22b model_30200 on the d1 base (PICKLEBOT_RES_BASE = s5c-d1-fw1bS model_32854),
# 1,200 iterations (fixed endpoint model_31399), ScheduledPPO 1e-4 constant, KL 0.05, std floor 0.1, critic warm-up 0,
# 12,288 envs, training seed 189, smoke 190.
# Pre-training reads on fresh seeds (both arms: P = 22b on its own base, Z = 22b on the d1 base, untrained; reported, and
# the endpoint's paired references): pairs 4220283, direction split 4220284, Measure60-RallyLamR2 4220285, h5f battery
# 4220286-4220301; Z on Measure60 at 4220302 (the +360 kill reference).
# Kill at +360: KILL-UNSTABLE / KILL-NO-HIT from the training log against 22b's 30100-30199 (D-194, unchanged);
# model_30560 on Measure60 at 4220302 against Z's read: KILL-SLOWED if sustained p50 left or back < Z's - 0.15 m/s;
# KILL-NO-ARRIVE if D-188 validity fails against Z (falls <= 2 x, worst untimed arrival >= 0.80, fallen + censored <= 0.15).
# Endpoint (child on the same seeds): rally_check.py d1s2-gate against P (unchanged lines; court falls <= 0.04 absolute,
# P's own h5f falls reported); agility: AGILE-KEPT if R_LB >= Z's - 0.03 and first-step p50 left and back <= Z's + 0.05,
# else SPEED-LOST. Reported: the stage-2 child (model_31399 of rally-d1s2) and 22b model_30600 on pairs / direction.
# Verdict: D1S3-PASS (rally pass + AGILE-KEPT) / SPEED-KEPT (AGILE-KEPT, rally not met: expected; next is the
# first-handed-ball lever) / SPEED-LOST (panel; motion's next is d1 + --recover).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent|kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
RUN=rally-d1s3; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s3; TAG=d1s3
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
[ -f $BASE ] || { echo "missing d1 base $BASE"; exit 1; }
T=Picklebot-Rally22b-FastMove-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt; P=$L/$PRUN/$PCK; C600=$L/$PRUN/model_30600.pt
S2=$(ls -d $L/*_rally-d1s2 | tail -1)/model_31399.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s3.done; exit 0; }
[ -s $R-summary.txt ] || echo "d1 base $BASE" > $R-summary.txt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
FW="--task Picklebot-Footwork-Measure60-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
own() { PICKLEBOT_LAM_R=2 "$@"; }
# arm reads: $1 = own|onbase, $2 = checkpoint, $3 = prefix (pairs / dir / fw on the endpoint seeds)
reads() {
  [ -s $3-pairs.json ] || $1 python scripts/stage2_eval.py --checkpoint $2 $PA --seed 4220283 --json $3-pairs.json >> $R-reads.log 2>&1
  [ -s $3-dir.json ] || $1 python scripts/diag/feeder_speed_envelope.py --checkpoint $2 --seed 4220284 --json $3-dir.json >> $R-reads.log 2>&1
  if [ "$1" = onbase ]; then [ -s $3-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $2 $FW --seed 4220285 --json $3-fw.json >> $R-reads.log 2>&1
  else [ -s $3-fw.json ] || python scripts/diag/footwork_eval.py --checkpoint $2 $FW --seed 4220285 --json $3-fw.json >> $R-reads.log 2>&1; fi
}
# pre-training: P (22b, own base) and Z (22b on the d1 base)
reads own $P $R-parent; reads onbase $P $R-zs
[ -s $R-zs-killref-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $P $FW --seed 4220302 --json $R-zs-killref-fw.json >> $R-reads.log 2>&1
[ -s results/stage5f-$TAG-p22b-summary.json ] || own bash scripts/h5f_clean_eval.sh rally-22b-readcfg $PCK $TAG-p22b 4220286 > $R-h5f-p22b.log 2>&1
[ -s results/stage5f-$TAG-zs-summary.json ] || onbase bash scripts/h5f_clean_eval.sh rally-22b-readcfg $PCK $TAG-zs 4220286 > $R-h5f-zs.log 2>&1
for f in parent-pairs parent-dir parent-fw zs-pairs zs-dir zs-fw zs-killref-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
for t in p22b zs; do [ -s results/stage5f-$TAG-$t-summary.json ] || stop EVAL-FAIL-h5f-$t; done
# rally_check.py d1s2-gate reads PREFIX-parent-early-{pairs,dir}.json: the paired parent reads under its names
cp -n $R-parent-pairs.json $R-parent-early-pairs.json; cp -n $R-parent-dir.json $R-parent-early-dir.json
grep -q "^pre-training" $R-summary.txt || python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
ld = lambda f: json.load(open(f"results/d1s3-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
lb = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
for arm, name in (("parent", "22b own base"), ("zs", "22b on d1 base (untrained)")):
    p = ld(f"{arm}-pairs")["pairs"]
    a = dr.agility(ld(f"{arm}-fw"))
    r = sum(a["sustained_p50"][i] / spec[i]["sustained_p50"] for i in (2, 4)) / 2
    f = json.load(open(f"results/stage5f-d1s3-{'p22b' if arm == 'parent' else 'zs'}-summary.json"))["falls_court"]
    print(f"pre-training {name}: P(5+) open {rc.p5_open(p)[0]:.4f} {rc.p5_open(p)[1]}; partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; "
          f"feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; left + back feeder contact {lb(ld(f'{arm}-dir')['directions']):.4f}; "
          f"h5f court falls {f}; Measure60 R_LB {r:.3f}, sustained L/B {a['sustained_p50'][2]}/{a['sustained_p50'][4]}, falls {a['falls']:.2f}")
PY
# smoke
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/diag/agility_train_run.sh $RUN-smoke $T \
    --agent.seed 190 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s3-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s3-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s3-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s3-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead,
      "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s3-smoke.txt
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
fast = "rally_fast_track_lin_vel" in env
ok = not miss and noise and based and saved and fast
print(f"smoke config check: missing {miss}; actor noise on {noise}; base_checkpoint is the d1 base {based}; "
      f"save_interval 40 {saved}; fast move reward {fast} -> {'ok' if ok else 'STOP'}")
PY
cat /tmp/d1s3-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s3-smoke.txt)" = 5 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - "$BASE" <<'PY' > $R-kill.txt 2>&1
import glob, json, os, subprocess, sys, time
from picklebot_mj import d1_rule as dr
base = sys.argv[1]
LOG, EXIT, L = "artifacts/train/rally-d1s3.log", "artifacts/train/rally-d1s3.exit.json", "artifacts/train/logs/picklebot_return_stand"
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
    os.system("pkill -f 'run-name rally-d1s3 '"); sys.exit(0)
ck = None
while ck is None:
    c = glob.glob(f"{L}/*_rally-d1s3/model_30560.pt")
    ck = c[0] if c else None
    if ck is None and os.path.exists(EXIT):
        print("no +360 checkpoint"); sys.exit(0)
    time.sleep(30)
time.sleep(30)
r = subprocess.run(["python", "scripts/diag/footwork_eval.py", "--checkpoint", ck, "--task", "Picklebot-Footwork-Measure60-RallyLamR2-G1",
                    "--envs", "1024", "--seconds", "120", "--move-prob", "1.0", "--seed", "4220302", "--json", "results/d1s3-kill-fw.json"],
                   env=dict(os.environ, PICKLEBOT_RES_BASE=base), capture_output=True, text=True)
if r.returncode != 0:
    print("KILL READ CRASHED (no kill)"); sys.exit(0)
v, line = dr.s3_speed_kill(json.load(open("results/d1s3-kill-fw.json")), json.load(open("results/d1s3-zs-killref-fw.json")))
print("+360 " + line)
if v != "CONTINUE":
    os.system("pkill -f 'run-name rally-d1s3 '")
PY
  ) &
  PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 \
    bash scripts/diag/agility_train_run.sh $RUN $T --agent.seed 189 --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN \
    --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "$(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1)"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_31399.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
# endpoint: child, plus the reported stage-2 child and 22b model_30600
reads onbase $CK $R-child; reads onbase $S2 $R-s2; reads own $C600 $R-c600
[ -s results/stage5f-$TAG-summary.json ] || onbase bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220286 > $R-h5f.log 2>&1
for f in child-pairs child-dir child-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
cp -n $R-child-pairs.json $R-target.json; cp -n $R-child-dir.json $R-endpoint-dir.json
python scripts/rally_check.py d1s2-gate $R $TAG | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
[ "$RALLY" = 0 ] || [ "$RALLY" = 1 ] || stop "GATE-CRASH-$RALLY"
echo "reported (promotion gate against run 14, expected FAIL):" | tee -a $R-summary.txt
python scripts/rally_check.py r19-gate $R $TAG | tee -a $R-summary.txt
python scripts/rally_check.py target $R $TAG | tee -a $R-summary.txt
python - $RALLY <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
ld = lambda f: json.load(open(f"results/d1s3-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
kv, ka = dr.s3_agility_kept(ld("child-fw"), ld("zs-fw"), spec)
print(f"agility vs the untrained composite (Z): {kv}; " + "; ".join(ka))
av, a = dr.agility_verdict(ld("child-fw"), ld("parent-fw"), spec)
print(f"agility vs 22b (reported): {av} (R_LB {a['parent']['R_LB']:.3f} -> {a['child']['R_LB']:.3f})")
lb = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
for name, pre in (("22b model_30200", "parent"), ("22b on d1 base, untrained", "zs"), ("stage-2 child (reported)", "s2"),
                  ("22b model_30600 (reported)", "c600"), ("d1s3 child", "child")):
    if not os.path.exists(f"results/d1s3-{pre}-pairs.json"):
        continue
    p = ld(f"{pre}-pairs")["pairs"]
    print(f"{name}: P(5+) open {rc.p5_open(p)[0]:.4f} {rc.p5_open(p)[1]}; partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; "
          f"feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; left + back feeder contact {lb(ld(f'{pre}-dir')['directions']):.4f}")
for t in ("p22b", "zs", ""):
    f = f"results/stage5f-d1s3{'-' + t if t else ''}-summary.json"
    print(f"h5f court falls {t or 'child'}: {json.load(open(f))['falls_court']}")
rally = sys.argv[1] == "0"
v = "D1S3-PASS" if rally and kv == "AGILE-KEPT" else "SPEED-KEPT" if kv == "AGILE-KEPT" else "SPEED-LOST"
json.dump({"agility_kept": kv, "agility_vs_22b": av, "rally_pass": rally, "verdict": v}, open("results/d1s3-summary.json", "w"), indent=1)
print(f"rally run verdict {'PASS' if rally else 'not met'}; VERDICT: {v}")
PY
echo done > artifacts/train/d1s3.done
