#!/usr/bin/env bash
# Court-feed stance-target diagnostic (D-176). With the planner on, court feeds get no planner spot (D-116), so
# stance_progress has paid pelvis speed toward a STALE stance_xy (the last planned spot or (0, 0)) on every court feed,
# i.e. on the pair courts' feeder balls, through all training (panel round 49, experiment design; verified in code).
# One change: court_feed_stance True (each court feed's stance_xy is its own stance spot; privileged reward target only,
# observations unchanged; task Picklebot-Agility-DirTally-CourtStance-LamR2-G1, otherwise the BALL arm's run-14 task).
# Arms from run 18b model_29000, 1e-4, 400 iterations, 4,096 envs, last quarter, feeder-ball direction tally:
#   K0a (seed 150) and K0b (seed 151): the BALL task (A/A control: drift between identical arms);
#   KF (seed 152): the CourtStance task.
# Pre-registered rule (coded): PASS if KF left + back legal - mean(K0) >= +3.0 points AND >= 2 x |K0a - K0b| (left +
# back), KF forward + right legal >= mean(K0) - 2.0 points, KF falls <= 4.157 per 1,000 env-seconds, and the config
# check finds court_feed_stance: true in KF's params/env.yaml. PASS -> the next rally run carries court_feed_stance.
# FAIL -> the stale target was not what held left / back back; E continues with ball-1 work.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/courtstance50
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_AGILITY_LOG_EVERY=240
export PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_STD_MIN=0.1
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$PRUN/$PCK ] || { echo "missing parent"; exit 1; }
arm() { # tag task seed
  local tag=$1 task=$2 seed=$3 out=$R-$1.jsonl
  [ -s $out ] && { echo "$out exists: not re-run"; return 1; }
  PICKLEBOT_AGILITY_LOG=$out PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=3600 bash scripts/diag/agility_train_run.sh courtstance50-$tag $task \
    --agent.seed $seed --agent.max-iterations 400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
  echo "arm $tag: $(cat artifacts/train/courtstance50-$tag.exit.json)"
  [ -s $out ] || { echo "arm $tag wrote no counters"; return 1; }
}
arm K0a Picklebot-Agility-DirTally-LamR2-G1 150 || exit 1
arm K0b Picklebot-Agility-DirTally-LamR2-G1 151 || exit 1
arm KF Picklebot-Agility-DirTally-CourtStance-LamR2-G1 152 || exit 1
python - <<'PY' | tee $R-summary.txt
import glob, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar
s = {}
for t in ("K0a", "K0b", "KF"):
    b = ar.ball_side(ar.window(ar.read_rows(f"results/courtstance50-{t}.jsonl"), "dir", 0.75, 1.0))
    f = falls_per_1000_env_s(f"artifacts/train/courtstance50-{t}.log", envs=4096)[0]
    s[t] = (b, f)
    print(f"{t}: left + back legal {b['lb_legal']:.4f}, forward + right legal {b['fr_legal']:.4f}, falls / 1,000 env-s {f:.3f}")
    for dn, v in b["directions"].items():
        print(f"   {dn:8s} feeds {v['feeds']:6d} legal {v['legal']:.3f} contact {v['contact']:.3f} onset p50 {v['onset_p50_s']} peak mean {v['peak_mean']:.2f} m/s")
lb0 = (s["K0a"][0]["lb_legal"] + s["K0b"][0]["lb_legal"]) / 2
fr0 = (s["K0a"][0]["fr_legal"] + s["K0b"][0]["fr_legal"]) / 2
aa = 100 * abs(s["K0a"][0]["lb_legal"] - s["K0b"][0]["lb_legal"])
d_lb, d_fr, ff = 100 * (s["KF"][0]["lb_legal"] - lb0), 100 * (s["KF"][0]["fr_legal"] - fr0), s["KF"][1]
ok = d_lb >= 3.0 and d_lb >= 2 * aa and d_fr >= -2.0 and ff <= 4.157
print(f"rule: KF - mean(K0) left + back {d_lb:+.2f} (needs >= +3.0 and >= 2 x A/A {aa:.2f} = {2 * aa:.2f}); "
      f"forward + right {d_fr:+.2f} (needs >= -2.0); KF falls {ff:.3f} (needs <= 4.157)")
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_courtstance50-KF/params/env.yaml"))
cap = bool(d) and re.search(r"^\s+court_feed_stance: true\s*$", open(d[-1]).read(), re.M) is not None
print(f"config check KF court_feed_stance true: {'ok' if cap else 'VOID'}")
print("VERDICT: VOID" if not cap else ("VERDICT: PASS" if ok else "VERDICT: FAIL"))
PY
echo done > artifacts/train/courtstance50.done
