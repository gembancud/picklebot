#!/usr/bin/env bash
# Stance-cap diagnostic (D-174). The second agility screen (D-173) was VOID: on drill spots the rally policy moves at
# about 1.05-1.25 m/s (p50 peak) in every direction, below the 1.2-2.0 m/s band, while a lagged point mass meets 100 %.
# Stepping faster than 1 m/s has never been rewarded: stance_progress (pelvis speed toward the hitting stance before
# the hit) is clamped at max_speed 1.0 m/s, and the move drill tracks <= 1 m/s. Feeder balls going left / back are
# returned 45 / 38 % in training (BALL arm), forward / right 88 / 85 %.
# One change: stance_progress max_speed 1.0 -> 2.0 (task Picklebot-Agility-DirTally-Stance2-LamR2-G1, otherwise
# identical to the BALL arm's run-14 task). Two arms from run 18b model_29000, 1e-4, 400 iterations, 4,096 envs,
# measured over the last quarter with the feeder-ball direction tally:
#   K0 (seed 148) Picklebot-Agility-DirTally-LamR2-G1; K2 (seed 149) the Stance2 task.
# Pre-registered rule (coded): PASS if K2 left + back feeder legal - K0 >= +3.0 points, K2 forward + right legal >=
# K0 - 2.0 points and K2 falls <= 4.157 per 1,000 env-seconds -> the next rally run carries stance max_speed 2.0.
# Otherwise FAIL: the cap is not the lever; next the motion-controller route.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/stance49
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_AGILITY_LOG_EVERY=240
export PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_STD_MIN=0.1
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$PRUN/$PCK ] || { echo "missing parent"; exit 1; }
arm() { # tag task seed
  local tag=$1 task=$2 seed=$3 out=$R-$1.jsonl
  [ -s $out ] && { echo "$out exists: not re-run"; return 1; }
  PICKLEBOT_AGILITY_LOG=$out PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=3600 bash scripts/diag/agility_train_run.sh stance49-$tag $task \
    --agent.seed $seed --agent.max-iterations 400 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
  echo "arm $tag: $(cat artifacts/train/stance49-$tag.exit.json)"
  [ -s $out ] || { echo "arm $tag wrote no counters"; return 1; }
}
arm K0 Picklebot-Agility-DirTally-LamR2-G1 148 || exit 1
arm K2 Picklebot-Agility-DirTally-Stance2-LamR2-G1 149 || exit 1
python - <<'PY' | tee $R-summary.txt
import glob, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar
s = {}
for t in ("K0", "K2"):
    b = ar.ball_side(ar.window(ar.read_rows(f"results/stance49-{t}.jsonl"), "dir", 0.75, 1.0))
    f = falls_per_1000_env_s(f"artifacts/train/stance49-{t}.log", envs=4096)[0]
    s[t] = (b, f)
    print(f"{t}: left + back legal {b['lb_legal']:.4f}, forward + right legal {b['fr_legal']:.4f}, falls / 1,000 env-s {f:.3f}")
    for dn, v in b["directions"].items():
        print(f"   {dn:8s} feeds {v['feeds']:6d} legal {v['legal']:.3f} contact {v['contact']:.3f} onset p50 {v['onset_p50_s']} peak mean {v['peak_mean']:.2f} m/s")
(b0, f0), (b2, f2) = s["K0"], s["K2"]
d_lb, d_fr = 100 * (b2["lb_legal"] - b0["lb_legal"]), 100 * (b2["fr_legal"] - b0["fr_legal"])
ok = d_lb >= 3.0 and d_fr >= -2.0 and f2 <= 4.157
print(f"rule: K2 - K0 left + back legal {d_lb:+.2f} (needs >= +3.0); forward + right {d_fr:+.2f} (needs >= -2.0); K2 falls {f2:.3f} (needs <= 4.157)")
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_stance49-K2/params/env.yaml"))
txt = open(d[-1]).read() if d else ""
cap = re.search(r"stance_progress:\n\s+func:.*\n\s+params:\n\s+max_speed: 2\.0", txt) is not None
print(f"config check K2 stance_progress max_speed 2.0: {'ok' if cap else 'VOID'}")
print("VERDICT: VOID" if not cap else ("VERDICT: PASS" if ok else "VERDICT: FAIL"))
PY
echo done > artifacts/train/stance49.done
