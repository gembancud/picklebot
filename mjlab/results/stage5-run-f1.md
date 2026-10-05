# Stage 5 run F1 (`footwork-f01`): it steps, but only to its right

Date: 2026-10-06. Task `Picklebot-Footwork-G1`:
- free feet, random start box, pelvis-anchored feeds;
- the ten Stage 4 families plus four reach families at equal weight;
- aiming targets and the recovery command.

Warm-started from `aim-all-c01/model_7600`, expanded to 118 / 133 inputs; the expansion is exact (max output difference 0.0 with random new inputs). 4096 envs, train seed 1, 7,000 s cap: iterations 7,600 → 9,886. **Fixed endpoint `model_9800`.**

## Training
- **Opening:** falls hit 75 % in the first iterations (new start spots, no stand-still reward), dropped to 0 by iteration ~7,750 and stayed near 0.
- **Ball rewards:** legal return 0.23 → 1.23 per episode and placement 0.04 → 0.29, still rising slowly at the cap. Value loss 0.10–0.17, action std 0.72–0.77.
- **Recovery reward:** flat at 0.04–0.07 throughout.

## Evaluation (dev seed 4,200,080; 2048 envs × 16 s; paired targets; recovery to the fixed baseline centre)
| Family | Contact | Legal (A / B pooled) | A/B gain [95 % CI] |
|---|---:|---:|---:|
| easy_forehand | 86.1 % | 78.6 % | +0.455 [0.434, 0.476] |
| wide_forehand | 85.6 % | 80.2 % | +0.506 [0.486, 0.527] |
| backhand | 85.6 % | 77.3 % | +0.386 [0.365, 0.407] |
| deep | 86.7 % | 80.4 % | +0.556 [0.536, 0.577] |
| short | 84.7 % | 70.6 % | +0.375 [0.355, 0.396] |
| high | 83.4 % | 70.7 % | +0.487 [0.466, 0.508] |
| low | 88.0 % | 84.9 % | +0.778 [0.760, 0.796] |
| fast | 87.1 % | 83.6 % | +0.724 [0.705, 0.743] |
| topspin | 87.1 % | 82.0 % | +0.598 [0.577, 0.619] |
| backspin | 85.5 % | 72.1 % | +0.042 [0.033, 0.050] |
| **reach_forehand** | **84.8 %** | **73.8 %** | +0.571 [0.549, 0.592] |
| **reach_backhand** | **0.2 %** | **0.1 %** | 0 |
| **reach_short** | **0 %** | **0 %** | 0 |
| **reach_deep** | **0 %** | **0 %** | 0 |

- **Overall:** A/B gain +0.391 [0.386, 0.397]; falls 5 in 8,192 robot episodes (0.06 %).
- **Recovery error** (feeds hit): median 0.80 m, p90 1.35 m (gate ≤ 0.5 m median).
- **Movement** (dev seed 4,200,080, 1,024 envs):
  - pelvis max displacement per episode: p50 0.17 m, p90 1.34 m, max 3.36 m (Stage 4: 0.05 / 0.14 / 0.41 m);
  - foot path: p50 0.31 m, p90 1.72 m.
- **How the failing reach families end** (seed 4,200,081, target A): reach_backhand 939 second bounces, reach_short 1,299 second bounces, reach_deep 1,365 lost behind the robot. No contact at all; the robot does not go to those balls.

**Retention** (Stage 4 families from the fixed start, target A, same feeds as `model_7600` on the Aim-All task): overall 80.3 % vs 82.2 % (−1.9 points). Per family:
- easy −4.5 points;
- backhand **−8.5** points (76.2 vs 84.7 %);
- deep −2.8, high −2.7, topspin −2.0;
- the others within ±2.

## Diagnosis
- **The robot learned to step, but only toward its right, the forehand side, where leaning already brought the paddle close to the ball.** Every ball that needs a step to the left, forward or back is never touched.
- **Cause: both distance-shaping terms are too narrow to guide travel.**
  - `approach_ball` pays exp(−(d/0.25 m)²) for paddle–ball distance after the bounce. At the 1.5–3 m paddle–ball distances of the other reach feeds it is ~0, so nothing rewards moving toward them until the paddle is already within ~0.3 m.
  - `recovery_reward` (std 0.5 m) is ~0.001 of its maximum at the typical 1.3 m start distance, which is why it stayed flat.
  - The right-side reach feeds were learnable only because a lean plus a small step got inside the narrow kernel.
- **Stage 4 behaviour is mostly kept,** apart from backhand from the fixed start (−8.5 points), and falls are negligible.

## Run F2 change (documented before launch)
**One change: the range of the distance shaping.**
- Add `approach_far`: exp(−(d/1.5 m)²) on the paddle–ball distance, weight 1.0, active from the bounce until the hit (the same window as `approach_ball`, which is kept unchanged for precision).
- Widen `recovery_reward` from std 0.5 m to 1.5 m.

Both make distance rewards informative at 1–3 m, where the failing reach feeds and recovery spots are. Everything else stays the same: task, mix, start box, rewards, weights, network. F2 warm-starts from `footwork-f01/model_9800` (same inputs).

Files: `stage5-f1-{A,B}.json`, `stage5-f1-gain.json`, `stage5-f1-retention-A.json`, `stage5-f1-retention-parent-A.json`, `stage5-f1-motion.json`.
