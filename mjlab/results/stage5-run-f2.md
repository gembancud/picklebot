# Stage 5 run F2 (`footwork-f02`): wider shaping did not unlock left, forward or back

Date: 2026-10-06. Task `Picklebot-Footwork-Wide-G1` = run F1's task plus one change, the **distance-shaping range**:
- `approach_far`: exp(−(d/1.5 m)²) on the paddle–ball distance, weight 1, from the bounce to the hit;
- `recovery_reward` widened from std 0.5 m to 1.5 m.

A test checks that nothing else differs. Warm-started from `footwork-f01/model_9800`. 4096 envs, train seed 1, 7,000 s cap: iterations 9,800 → 12,050. **Fixed endpoint `model_12000`.**

## Training
Healthy throughout: value loss 0.11–0.14, action std 0.74, falls 0–0.13. Legal return 1.16 → 1.22–1.24 per episode. **`approach_far` stayed flat at 0.07 and recovery at 0.23** from iteration ~10,000 on: the wider signal did not change behaviour.

## Evaluation (dev seed 4,200,090; 2048 envs × 16 s; paired targets; scored on `Picklebot-Footwork-G1`, which has identical observations and dynamics)
| Family | Contact | Legal (pooled) | F1 legal | A/B gain [95 % CI] | F1 gain |
|---|---:|---:|---:|---:|---:|
| easy_forehand | 86.8 % | 82.0 % | 78.6 % | +0.773 [0.754, 0.791] | +0.455 |
| wide_forehand | 86.5 % | 82.5 % | 80.2 % | +0.751 [0.733, 0.770] | +0.506 |
| backhand | 86.8 % | 80.8 % | 77.3 % | +0.575 [0.553, 0.596] | +0.386 |
| deep | 85.7 % | 79.1 % | 80.4 % | +0.756 [0.738, 0.774] | +0.556 |
| short | 83.7 % | 72.1 % | 70.6 % | +0.598 [0.577, 0.619] | +0.375 |
| high | 84.7 % | 70.8 % | 70.7 % | +0.432 [0.411, 0.453] | +0.487 |
| low | 86.5 % | 83.9 % | 84.9 % | +0.735 [0.716, 0.754] | +0.778 |
| fast | 88.3 % | 84.6 % | 83.6 % | +0.703 [0.683, 0.722] | +0.724 |
| topspin | 86.6 % | 81.3 % | 82.0 % | +0.734 [0.715, 0.753] | +0.598 |
| backspin | 86.2 % | 65.8 % | 72.1 % | +0.039 [0.031, 0.048] | +0.042 |
| reach_forehand | 85.5 % | 74.4 % | 73.8 % | +0.612 [0.591, 0.633] | +0.571 |
| **reach_backhand** | **0.3 %** | **0 %** | 0.1 % | 0 | 0 |
| **reach_short** | **0 %** | **0 %** | 0 % | 0 | 0 |
| **reach_deep** | **0 %** | **0 %** | 0 % | 0 | 0 |

- **Overall:** A/B gain **+0.481 [0.476, 0.487]** (F1 +0.391); falls 7 in 8,192 robot episodes (0.09 %).
- **Recovery error:** median 0.78 m, p90 1.35 m (F1 0.80 / 1.35).
- **Movement:** pelvis max displacement p50 0.22 m, p90 1.28 m; foot path p50 0.41 m, p90 1.79 m.
- **Retention** (fixed start, target A, same feeds as `model_7600`): **82.0 % vs 82.1 %**, within ±3 points on every family. Backhand recovered from −8.5 to +0.1; high is −3.0.

## What F2 shows
1. **The shaping range was not the bottleneck.** With a 1.5 m kernel the robot is rewarded for closing distance at 1–3 m, yet left, forward and back balls still get zero contact, and the recovery error is unchanged.
2. **What did improve is in hitting, not moving:** aiming (+0.48 overall, easy +0.77) and retention (backhand fixed). These are probably the extra training time, since F2 is a continuation, rather than the shaping change.
3. **The robot has one movement: a lean plus a step to its right.** It never learned general stepping or walking. Its whole lineage began from a standing policy (Stage 2, `model_700`), not from mjlab's walking policy. PPO exploration around a standing posture does not discover coordinated multi-step gaits in a few thousand iterations, whatever the shaping.

## Against the Stage 5 gate (for the gate step)
| Criterion | Result | Verdict |
|---|---|---|
| ≥ 85 % on every Stage 4 family from random starts | 65.8–84.6 % | fail |
| ≥ 75 % on every reach family | 74.4 % / 0 / 0 / 0 % | fail |
| Contact ≥ 92 % on Stage 4 families | 83.7–88.3 % | fail |
| A/B gain interval > 0 on every family | > 0 for all eleven hit families; 0 for the three never touched | fail |
| Median recovery error ≤ 0.5 m | 0.78 m | fail |
| Falls ≤ 1 % per robot episode | 0.09 % | pass |
| Retention within 5 points | −0.1 overall, worst −3.0 | pass |

Files: `stage5-f2-{A,B}.json`, `stage5-f2-gain.json`, `stage5-f2-retention-A.json`, `stage5-f2-retention-parent-A.json`, `stage5-f2-motion.json`.
