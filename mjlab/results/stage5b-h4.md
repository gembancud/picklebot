# Stage 5B H4: the Drill 3 executor over the latent controller (D-050, D-056)

**Task** `Picklebot-Latent-Drill3-G1` (`picklebot_mj/tasks/__init__.py`):
- **Base:** S-D3b's Drill 3 task (gentle reach curriculum; 60 % real balls over all 14 families with an adaptive mix, 15 % move-to-spot, 25 % ghost swings). This is the task of the S-D3-style-c baseline, without its style reward.
- **Action:** H3's latent action space, a = [a_lat 32, a_wrist 3] through the frozen latent-07/latent_10651 (λ 1.0, wrist residual ±0.3 rad).
- **Rewards:**
  - removed: `pose`, `ready_stance`;
  - added: `latent_l2` −0.01;
  - `action_rate_l2` set to H3's −0.01. The inherited −0.1 on the raw latent action gave −5.5 per episode in the smoke run and swamped the task terms.
- **Network:** the student's 1024-512-256 actor and critic, plain PPO (mjlab G1 defaults).
- **Speed:** about 5.2 s per iteration at 4096 envs, about 1,350 iterations per 2 h run.

**Evaluation** (`scripts/h4_eval.sh`, `scripts/h4_summary.py`): the Stage 5 gate protocol on each fixed endpoint, on fresh dev seeds:
- 2048 envs × 16 s;
- every family, target A/B, with and without the hint;
- retention vs model_7600;
- style score.

**Main metric** (D-056 plateau rule): the no-hint legal-return rate pooled over all 14 families. Baseline S-D3-style-c: 78.7 %, style 4.84.

**Evaluation scripts now reset before the first step** (`stage2_eval.py`, `style_score.py`, as in reach_eval.py). Check on S-D3-style-c (dev seed 4200418, no hint, target A):
- legal 78.5 % → 78.9 %;
- robot falls 4.3 → 4.8 % per episode;
- recovery 0.975 m in both;
- every family within noise.

So the earlier Stage 5 numbers stand. The final gate re-evaluates S-D3-style-c with the same script and seeds as the H4 candidate.

## Runs (budget: 15 under D-056)
| # | Run | Change (written before launch) | From | Endpoint | Main metric | Style |
|---|---|---|---|---|---|---|
| 1 | h4-01 | the plan as written: fresh PPO, settings above | scratch | model_1300 (cap) | **0.0 %** | **2.74** |
| 2 | h4-02 | + one-shot return shaping at first contact (D-057), task `Picklebot-Latent-Drill3-Shaped-G1` | h4-01/model_1300 | | | |

## Run 1: h4-01 (dev seeds 4200420-423; `stage5b-h4-h4-01-*.json`)
- **Every family has 0 % legal returns.** Contact is 18 %, the paddle moves at 0.8 m/s at contact, contact height is 0.57 m, and no ball crosses the net. Rally endings: second bounce 7,610, out 2,961, wrong side 2,003.
- **Style 2.74** (target <= 3.86; S-D3-style-c 4.84; human floor 0.94). **Robot falls 0.5 %** per episode (S-D3-style-c 4.8 %). **Recovery median 0.58 m** (S-D3-style-c 0.98 m).
- **Training curve:** no falls after iteration 400 and paddle contact rising slowly (0.04 -> 0.15 per episode), but legal returns stay at 0. Action std grew from 1.0 to 1.26.
- **Reading:** the decoder makes the motion human-like and stable. The policy has not found a swing, and the rewards give nothing between touching the ball and a legal return.

## Distillation from the flat student: rejected (D-057)
- `scripts/distill_h4.py` is DAgger through the frozen decoder, teacher S-D3-style-c (tests in `tests/test_distill_h4.py`). In the smoke run (60 iterations, 1024 envs) the imitation error rose from 0.30 to about 2.0 and stayed there, and robot episode endings grew.
- **Expressiveness floor** (`scripts/latent_reach_floor.py`, `stage5b-h4-latent-floor.json`): per-state best fits on the teacher's own states, MSE in the teacher's action units.

| lambda | legs | waist | left arm | right arm | right wrist | all | latent saturated |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.103 | 0.092 | 0.187 | 0.372 | 0.355 | 0.185 | 70 % |
| 2 | 0.068 | 0.061 | 0.149 | 0.277 | 0.301 | 0.140 | 54 % |
| 3 | 0.050 | 0.046 | 0.125 | 0.217 | 0.258 | 0.112 | 41 % |
| *teacher action variance* | 0.356 | 0.186 | 0.624 | 1.193 | 16.4 | 2.18 | |

The decoder gets close only with most latent commands pinned at the barrier, i.e. at the edge of the human-motion space. The flat student's wrist variance (16) shows it slams the wrist between limits.
