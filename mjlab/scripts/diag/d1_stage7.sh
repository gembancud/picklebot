#!/usr/bin/env bash
# D-203 d1s7 (panel round 67, 5 of 5 for (i): (d) alone): the parent d1s3 child (rally-d1s3 model_31399, on the d1 base)
# with one change, the restart state as a trailing actor and critic input (return_stand.restart_obs, 5 columns: parked,
# partner parked, court dead, next receiver, refeed countdown; PICKLEBOT_RESTART_OBS=1), trained 1,200 iterations on
# d1s3's own task (Picklebot-Rally22b-FastMove-G1). No reward change. The parent is widened by expand_checkpoint.py (zero
# columns, (0, 1) normalizer prior, zero Adam moments). ScheduledPPO 1e-4 constant, KL 0.05, std floor 0.1, warm-up 0,
# 12,288 envs; training seed 197, smoke 198. Child reads all run with PICKLEBOT_RESTART_OBS=1.
# Paired references reused (D-199 reads, D-201's parent dose read on 4220326), reported as such.
# INVALID (before training, CPU): the widened checkpoint's first layer, normalizer and Adam state equal the parent's on
#   the old columns, and the new columns are zero / (0, 1) / zero, so actions and values equal the parent's exactly.
# Smoke: D-202's checks (falls 4.157 unchanged, half-split reported), config has the restart term in actor and critic, and
#   the new first-layer columns got a gradient (Adam second moment > 0) in both networks.
# Kill at +360: D-194 lines; KILL-FARM; KILL-SLOWED / KILL-NO-ARRIVE on model_31760 against the parent. New-column norms
#   at +360 reported.
# Endpoint: D-202's lines (DOSE, GUARDS, F-UP + F-BIN, F-BAND, REFEED3, P5-KEPT, K3-KEPT, AGILE-KEPT, rally, ABS-F) plus
#   NO-USE: the child's dose read with the inputs frozen at live-court values (PICKLEBOT_RESTART_OBS_FREEZE=1), paired on
#   4220326, must take back >= half of the DOSE gain on a DOSE dimension that passed. Reported: the parent dose retest on
#   4220330 (test-retest), opening-exchange failure rates by shot position (parent vs child).
# Verdicts: KILL -> INVALID -> NO-DOSE -> NO-USE -> GUARD-BREACH -> MIX -> MORE-TIME -> OBS-PASS -> OBS-F -> OBS-FAIL.
# Stop rule (round 67): NO-DOSE or NO-USE ends the feeder premise; the panel then moves to other work.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
RUN=rally-d1s7; CTRL=rally-d1s7ctl; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s7; TAG=d1s7
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK
IRUN=2026-11-02_12-00-00_rally-d1s7-init; I=$L/$IRUN/$PCK
T=Picklebot-Rally22b-FastMove-G1; TF=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s7.done; exit 0; }
[ -s $R-summary.txt ] || echo "parent $P widened to $I (restart obs, 5 zero columns) on the d1 base $BASE; task $T" > $R-summary.txt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
FW="--task Picklebot-Footwork-Measure60-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
child() { PICKLEBOT_RESTART_OBS=1 "$@"; }
reads() {  # checkpoint, prefix: as D-199 (child only: the restart input on)
  [ -s $2-pairs.json ] || child onbase python scripts/stage2_eval.py --checkpoint $1 $PA --seed 4220306 --json $2-pairs.json >> $R-reads.log 2>&1
  [ -s $2-dir.json ] || child onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220307 --json $2-dir.json >> $R-reads.log 2>&1
  [ -s $2-fw.json ] || child env PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $1 $FW --seed 4220308 --json $2-fw.json >> $R-reads.log 2>&1
  [ -s $2-refeed3.json ] || child onbase python scripts/stage2_eval.py --checkpoint $1 $PA --refeed-delay 3.0 --seed 4220327 --json $2-refeed3.json >> $R-reads.log 2>&1
}
dose() {  # name, run dir, checkpoint, seed, extra env: LR-0 feeder tally + launch-bin pair log (the d1 base)
  [ -s $R-dose-$1.jsonl ] && [ -s $R-dose-$1-pairs.jsonl ] && return 0
  rm -f $R-dose-$1.jsonl $R-dose-$1-pairs.jsonl
  env $5 PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 \
    PICKLEBOT_PAIR_LOG=$R-dose-$1-pairs.jsonl PICKLEBOT_PAIR_LOG_EVERY=240 \
    PICKLEBOT_RES_BASE=$BASE PICKLEBOT_BALLIDX_LOG=$R-dose-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2700 PICKLEBOT_TRAIN_ENTRY=scripts/diag/agility_train.py \
    bash scripts/diag/agility_train_run.sh d1s7-dose-$1 $TF --agent.seed $4 --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $2 --agent.load-checkpoint $3 $ALG $OV >> $R-reads.log 2>&1
}
# paired parent references reused from D-199 (reads) and D-201 (the dose read on 4220326): same seeds, checkpoint, base
for f in parent-pairs parent-dir parent-fw parent-refeed3 killref-parent-fw p22b-pairs; do [ -s $R-$f.json ] || cp results/d1s4-$f.json $R-$f.json; done
for f in dose-parent dose-parent-pairs; do [ -s $R-$f.jsonl ] || cp results/d1s5-$f.jsonl $R-$f.jsonl; done
[ -s results/stage5f-$TAG-p-summary.json ] || cp results/stage5f-d1s4-p-summary.json results/stage5f-$TAG-p-summary.json
for f in parent-pairs parent-dir parent-fw parent-refeed3 killref-parent-fw p22b-pairs; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
for f in dose-parent dose-parent-pairs; do [ -s $R-$f.jsonl ] || stop EVAL-FAIL-$f; done
cp -n $R-parent-pairs.json $R-parent-early-pairs.json; cp -n $R-parent-dir.json $R-parent-early-dir.json
# widen the parent (5 trailing zero columns in actor and critic) and the INVALID check
if [ ! -f $I ]; then
  mkdir -p $L/$IRUN
  DIMS=$(CUDA_VISIBLE_DEVICES= python -c "import torch; c=torch.load('$P', map_location='cpu', weights_only=False); print(c['actor_state_dict']['mlp.0.weight'].shape[1] + 5, c['critic_state_dict']['mlp.0.weight'].shape[1] + 5)")
  set -- $DIMS
  CUDA_VISIBLE_DEVICES= python scripts/expand_checkpoint.py $P $I --actor-dim $1 --critic-dim $2 | tee -a $R-summary.txt
fi
CUDA_VISIBLE_DEVICES= python - "$P" "$I" <<'PY' | tee -a $R-summary.txt
import sys, torch
p, c = (torch.load(f, map_location="cpu", weights_only=False) for f in sys.argv[1:])
ok = c.get("iter") == p.get("iter")
for net in ("actor_state_dict", "critic_state_dict"):
    a, b = p[net], c[net]
    n = a["mlp.0.weight"].shape[1]
    ok &= b["mlp.0.weight"].shape[1] == n + 5 and torch.equal(b["mlp.0.weight"][:, :n], a["mlp.0.weight"])
    ok &= bool((b["mlp.0.weight"][:, n:] == 0).all())
    for k, fill in (("obs_normalizer._mean", 0.0), ("obs_normalizer._var", 1.0), ("obs_normalizer._std", 1.0)):
        ok &= torch.equal(b[k][:, :n], a[k]) and bool((b[k][:, n:] == fill).all())
    ok &= all(torch.equal(a[k], b[k]) for k in a if k not in ("mlp.0.weight", "obs_normalizer._mean", "obs_normalizer._var", "obs_normalizer._std"))
print(f"INVALID check: widened checkpoint equals the parent on the old columns, new columns zero / (0, 1) -> {'ok' if ok else 'INVALID'}")
PY
grep -q "INVALID check: .* -> ok$" $R-summary.txt || stop INVALID
# smoke (D-202's checks; restart term present; new columns get a gradient)
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  child env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=900 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 198 --agent.max-iterations 40 --agent.resume True \
    --agent.load-run $IRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s7-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s7-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s7-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s7-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
shapes = {net: sd[net]["mlp.0.weight"].shape for net in ("actor_state_dict", "critic_state_dict")}
live = []
for net, shp in shapes.items():
    st = [v for v in sd["optimizer_state_dict"]["state"].values() if tuple(v["exp_avg_sq"].shape) == tuple(shp)]
    g = float(st[0]["exp_avg_sq"][:, -5:].sum()) if len(st) == 1 else float("nan")
    w = float(sd[net]["mlp.0.weight"][:, -5:].norm())
    live.append(g > 0)
    print(f"smoke {net.split('_')[0]} new columns: Adam second moment sum {g:.3e}, weight norm {w:.4f}")
print("smoke new columns get a gradient in actor and critic", "ok" if all(live) else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s7-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
restart = "return_stand.restart_obs" in env and len(re.findall(r"^\s+restart:\s*$", env, re.M)) == 2  # actor + critic (YAML aliases the 2nd func)
terms = "rally_fast_track_lin_vel" in env and restart and "parked_ready" not in env and "ready_at_event" not in env
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move term, restart obs in actor + critic, no ready terms {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' | tee -a /tmp/d1s7-smoke.txt
import os, re, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
t = open(sys.argv[1], errors="ignore").read()
cut = [m.start() for m in re.finditer(r"Learning iteration", t)]
if len(cut) >= 4:
    mid = cut[len(cut) // 2]
    out = []
    for part in (t[:mid], t[mid:]):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write(part)
        out.append(falls_per_1000_env_s(f.name)[0])
        os.unlink(f.name)
    print(f"smoke falls half-split (reported): first half {out[0]:.3f}, second half {out[1]:.3f}")
PY
cat /tmp/d1s7-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s7-smoke.txt)" = 6 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python scripts/diag/d1s7_watch.py "$BASE" > $R-kill.txt 2>&1 ) &
  child env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 197 --agent.max-iterations 1200 --agent.resume True --agent.load-run $IRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
D=$(ls -d $L/*_$RUN | tail -1)
[ -f $D/model_31760.pt ] && CUDA_VISIBLE_DEVICES= python -c "
import torch; sd = torch.load('$D/model_31760.pt', map_location='cpu', weights_only=False)
print('+360 new-column weight norms (reported): actor', round(float(sd['actor_state_dict']['mlp.0.weight'][:, -5:].norm()), 4),
      'critic', round(float(sd['critic_state_dict']['mlp.0.weight'][:, -5:].norm()), 4))" | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_32598.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
reads $CK $R-child
[ -s results/stage5f-$TAG-summary.json ] || child onbase bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220310 > $R-h5f.log 2>&1
dose child $(basename $D) $(basename $CK) 4220326 PICKLEBOT_RESTART_OBS=1
dose child-frozen $(basename $D) $(basename $CK) 4220326 "PICKLEBOT_RESTART_OBS=1 PICKLEBOT_RESTART_OBS_FREEZE=1"
dose parent-retest $PRUN $PCK 4220330 PICKLEBOT_RESTART_OBS=0
for f in child-pairs child-dir child-fw child-refeed3; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
for f in dose-child dose-child-frozen; do [ -s $R-$f.jsonl ] || stop EVAL-FAIL-$f; done
cp -n $R-child-pairs.json $R-target.json; cp -n $R-child-dir.json $R-endpoint-dir.json
python scripts/rally_check.py d1s2-gate $R $TAG "d1s3 child (parent)" | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
[ "$RALLY" = 0 ] || [ "$RALLY" = 1 ] || stop "GATE-CRASH-$RALLY"
FUP=$(python -c "import json; from picklebot_mj import d1_rule as dr; print(int(dr.f_up(json.load(open('$R-child-pairs.json'))['pairs'], json.load(open('$R-parent-pairs.json'))['pairs'])[0] and dr.f_bin('$R-dose-child-pairs.jsonl', '$R-dose-parent-pairs.jsonl')[0]))")
if [ "$FUP" = 1 ]; then
  if [ ! -f artifacts/train/$CTRL.exit.json ]; then
    env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $CTRL $T --agent.seed 197 \
      --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  fi
  CD=$(ls -d $L/*_$CTRL | tail -1); CC=$(ls $CD/model_*.pt | sort -V | tail -1)
  [ -s $R-control-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $CC $PA --seed 4220306 --json $R-control-pairs.json >> $R-reads.log 2>&1
  dose control $(basename $CD) $(basename $CC) 4220326 PICKLEBOT_RESTART_OBS=0
fi
python - $RALLY <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import agility_rule as ar, ballidx_rule as br, d1_rule as dr, feeder_rule as fr
ld = lambda f: json.load(open(f"results/d1s7-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
rally = sys.argv[1] == "0"
def dose_read(name):
    c = ar.window(ar.read_rows(f"results/d1s7-dose-{name}.jsonl"), "ballidx", 0.5, 1.0)
    return fr.feeder_stats(c), [x for x in br.summarize(c, 0)["k"] if x["k"] == "3+"][0]["legal"]
sc, k3c = dose_read("child")
sp, k3p = dose_read("parent")
sa, _ = dose_read("child-frozen")
dose, line = dr.s6_dose(sc["vars"], sp["vars"]); print(line)
used, line = dr.s7_use(sc["vars"], sp["vars"], sa["vars"]); print(line)
if os.path.exists("results/d1s7-dose-parent-retest.jsonl"):
    sr, _ = dose_read("parent-retest")
    print(f"parent dose retest on 4220330 (reported): pelvis speed p50 {sr['vars']['pelvis_speed']['p50']} vs {sp['vars']['pelvis_speed']['p50']}, "
          f"recovery distance p50 {sr['vars']['recover_dist']['p50']} vs {sp['vars']['recover_dist']['p50']}")
guards = rc.r19_guards(ld("child-pairs")["per_family"], ld("child-dir")["directions"], ref="results/d1s7-parent-early",
                       cross_ref="results/d1s7-parent-early-pairs.json", name="parent", cross_name="parent")
print(f"GUARDS vs parent: {guards}")
fup, line = dr.f_up(ld("child-pairs")["pairs"], ld("parent-pairs")["pairs"]); print("F-UP vs parent (pairs): " + line)
fbin, line = dr.f_bin("results/d1s7-dose-child-pairs.jsonl", "results/d1s7-dose-parent-pairs.jsonl"); print("F-BIN vs parent (0-1 launch bin): " + line)
fc = rc.boot_low(ld("child-pairs")["pairs"]["court_counts"], 3, 2)[0]
abs_f = fc >= 0.80
print(f"ABS-F: feeder legal {fc:.4f} >= 0.80 -> {abs_f}")
fband = sc["band_contact"] is not None and sp["band_contact"] is not None and sc["band_contact"] >= sp["band_contact"] + 0.03
print(f"F-BAND: k=0 matched-band contact {sc['band_contact']} vs parent {sp['band_contact']} (need >= +0.03) -> {fband}")
k3 = k3c is not None and k3p is not None and k3c >= k3p - 0.01
print(f"K3-KEPT: k>=3 legal {k3c} vs parent {k3p} -> {k3}")
ak, lines = dr.s3_agility_kept(ld("child-fw"), ld("parent-fw"), spec)
print(f"AGILE-KEPT vs parent: {ak}; " + "; ".join(l.replace(" Z ", " parent ") for l in lines))
p5c, p5p = rc.p5_open(ld("child-pairs")["pairs"])[0], rc.p5_open(ld("parent-pairs")["pairs"])[0]
p5k = p5c >= p5p - 0.01
r3c, r3p = (rc.boot_low(ld(f)["pairs"]["court_counts"], 3, 2)[0] for f in ("child-refeed3", "parent-refeed3"))
r3k = r3c >= r3p - 0.01
print(f"P5-KEPT: {p5c:.4f} vs {p5p:.4f} -> {p5k}; REFEED3: feeder legal at 3 s {r3c:.4f} vs {r3p:.4f} -> {r3k}")
for name, f in (("parent", "parent-pairs"), ("child", "child-pairs")):
    print(f"opening-exchange failure rate by shot position 0-4 (reported), {name}: " + ", ".join(f"{x:.3f}" for x in dr.open_hazards(ld(f)["pairs"])))
fup_ctl = None
if os.path.exists("results/d1s7-control-pairs.json"):
    fup_ctl, line = dr.f_up(ld("child-pairs")["pairs"], ld("control-pairs")["pairs"]); print("F-UP vs control: " + line)
for name, f in (("parent", "parent-pairs"), ("child", "child-pairs"), ("22b (reported)", "p22b-pairs"), ("control (reported)", "control-pairs")):
    if os.path.exists(f"results/d1s7-{f}.json"):
        p = ld(f)["pairs"]
        print(f"{name}: P(5+) open {rc.p5_open(p)[0]:.4f}; feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}")
for name, f in (("parent", "results/stage5f-d1s7-p-summary.json"), ("child", "results/stage5f-d1s7-summary.json")):
    print(f"h5f court falls {name}: {json.load(open(f))['falls_court']}")
v = dr.s7_verdict(dose, used, guards, fup and fbin, fband, fup_ctl, abs_f, rally, ak == "AGILE-KEPT", k3, p5k, r3k)
json.dump({"verdict": v, "dose": dose, "used": used, "guards": guards, "f_up": fup, "f_bin": fbin, "f_band": fband,
           "f_up_control": fup_ctl, "abs_f": abs_f, "rally": rally, "agile": ak, "k3": k3, "p5_kept": p5k, "refeed3": r3k},
          open("results/d1s7-summary.json", "w"), indent=1)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s7.done
