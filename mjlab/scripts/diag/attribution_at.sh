#!/usr/bin/env bash
# Training-side leave-one-out screen A-T (D-166 route after the erosion check found no training loss: model_30200's
# training feeder legal +0.86 vs model_29000; D-167). Run 14's task, near-mean actions (std x 0.001), 200 iterations at
# 1,024 envs, learning rate 0, from run 18b model_29000; each arm moves one setting to the pairs read's value
# (tyro overrides, recorded in each arm's params/env.yaml):
#   T0 baseline; T1 no drill-v2 balls (court_feed_prob 1.0); T2 uniform family mix (feed_mix weights all 1.0);
#   T3 refeed 0.5 s; T4 fixed recovery spot; T5 planner off; T6 fixed target A; T7 ball noise off; T8 proprioceptive
#   noise off; TA all of T1-T8. Reported beside them (not in the rule): model_30200 at T0 and TA (the read's erosion in
#   a read-like training config).
# Pre-registered (D-166, architecture): Delta = per-ball legal (shots / (shots + rally-ending misses), all courts, second
# half) arm - T0. Calibration first: TA < 0.71 -> the configuration does not explain the gap to the read (~0.77); no
# configuration run; the panel reconvenes with STOP on the table. Eligible: T1-T6 with Delta >= 3.0 points (T7, T8 are
# sim-to-real commitments: reported, need their own D-entry). B = the largest eligible Delta (within 1 point: the
# smaller code change); the winner must keep Delta >= 2.0 at std x1 (one more arm) before B launches. None eligible ->
# as the calibration fail. Training seeds 114-126 (TRAIN_SEEDS).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand; PCK=model_29000.pt
S29=2026-10-29_00-00-00_std0001-init; S30=2026-10-29_00-00-01_std0001-30200-init
R19=$(ls -d $L/*_rally-19-cont | tail -1)
[ -f $L/$S30/model_30200.pt ] || CUDA_VISIBLE_DEVICES= python scripts/std_scale_init.py $R19/model_30200.pt $L/$S30/model_30200.pt --scale 0.001
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=1e-6
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
B=--env.actions.ball
MIX=""; for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do MIX="$MIX $B.feed-mix.weights.$f 1.0"; done
O1="$B.court-feed-prob 1.0"; O2="$MIX"; O3="$B.refeed-delay-s 0.5"; O4="$B.recovery-mode fixed"; O5="$B.planner-mode off"
O6="$B.target-mode A"; O7="$B.obs-ball-pos-noise 0.0 $B.obs-ball-vel-noise 0.0"; O8="--env.observations.actor.enable-corruption False"
OA="$O1 $O2 $O3 $O4 $O5 $O6 $O7 $O8"
run_arm() { # tag seed run checkpoint overrides...
  local tag=$1 seed=$2 run=$3 ck=$4; shift 4; local out=results/at-$tag.jsonl; rm -f $out
  PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh at-$tag $T \
    --agent.seed $seed --agent.max-iterations 200 --agent.resume True --agent.load-run $run --agent.load-checkpoint $ck $ALG "$@"
  echo "arm $tag: $(cat artifacts/train/at-$tag.exit.json)"
}
run_arm T0 114 $S29 $PCK
run_arm T1 115 $S29 $PCK $O1
run_arm T2 116 $S29 $PCK $O2
run_arm T3 117 $S29 $PCK $O3
run_arm T4 118 $S29 $PCK $O4
run_arm T5 119 $S29 $PCK $O5
run_arm T6 120 $S29 $PCK $O6
run_arm T7 121 $S29 $PCK $O7
run_arm T8 122 $S29 $PCK $O8
run_arm TA 123 $S29 $PCK $OA
run_arm T0-30200 124 $S30 model_30200.pt
run_arm TA-30200 125 $S30 model_30200.pt $OA
python - <<'PY' | tee results/at-summary.txt
import json
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
def stats(tag):
    r = rows(f"results/at-{tag}.jsonl"); a, b = r[len(r) // 2], r[-1]
    h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    er = [y - x for x, y in zip(a["end_reasons"][0], b["end_reasons"][0])]
    shots = sum(i * c for i, c in enumerate(h)); per = shots / max(shots + er[0], 1)
    o = [[b["launch"]["outcome_feeds_legal"][g][j] - a["launch"]["outcome_feeds_legal"][g][j] for j in range(2)] for g in range(3)]
    fed = sum(x[1] for x in o) / max(sum(x[0] for x in o), 1)
    return per, fed, sum(h), shots + er[0]
names = {"T0": "baseline", "T1": "no drill-v2", "T2": "uniform mix", "T3": "refeed 0.5 s", "T4": "fixed recovery",
         "T5": "planner off", "T6": "target A", "T7": "ball noise off", "T8": "proprio noise off", "TA": "all",
         "T0-30200": "model_30200 baseline", "TA-30200": "model_30200 all"}
s = {t: stats(t) for t in names}
p0 = s["T0"][0]
for t, nm in names.items():
    per, fed, n, balls = s[t]
    print(f"{t:9s} {nm:22s} per-ball legal {per:.4f} (Delta {100 * (per - p0):+.2f}; balls {balls}), feeder legal {fed:.4f}")
print(f"model_30200 - model_29000 feeder legal: baseline {100 * (s['T0-30200'][1] - s['T0'][1]):+.2f}, all read settings "
      f"{100 * (s['TA-30200'][1] - s['TA'][1]):+.2f} points (reported)")
if s["TA"][0] < 0.71:
    print(f"VERDICT: CALIBRATION FAIL - all read settings give {s['TA'][0]:.4f} < 0.71; the configuration does not explain the gap -> panel (STOP on the table)")
else:
    el = sorted(((s[t][0] - p0, t) for t in ("T1", "T2", "T3", "T4", "T5", "T6") if s[t][0] - p0 >= 0.03), reverse=True)
    if el:
        print(f"VERDICT: ELIGIBLE {el[0][1]} ({names[el[0][1]]}, Delta {100 * el[0][0]:+.2f}); also eligible {[t for _, t in el[1:]]}; "
              f"confirm Delta >= 2.0 at std x1 before B")
    else:
        print("VERDICT: NONE ELIGIBLE - no single setting moves per-ball legal by 3 points -> panel (STOP on the table)")
PY
python - <<'PY' | tee -a results/at-summary.txt
import glob, re
want = {"T1": [("court_feed_prob", "1.0")], "T3": [("refeed_delay_s", "0.5")], "T4": [("recovery_mode", "fixed")],
        "T5": [("planner_mode", "off")], "T6": [("target_mode", "A")], "T7": [("obs_ball_pos_noise", "0.0"), ("obs_ball_vel_noise", "0.0")],
        "T2": [("backhand", "1.0"), ("reach_backhand", "1.0")]}
for tag, kv in want.items():
    d = sorted(glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_at-{tag}/params/env.yaml"))
    text = open(d[-1]).read() if d else ""
    ok = bool(d) and all(re.search(rf"^\s+{k}: {re.escape(v)}\s*$", text, re.M) for k, v in kv)
    verdict = "ok" if ok else "VOID (override not in params/env.yaml)"
    print(f"override check {tag}: {verdict}")
PY
echo done > artifacts/train/at.done
