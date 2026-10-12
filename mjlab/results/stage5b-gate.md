# Stage 5B gate (H4): NOT MET — paired evaluation of h4-10 against S-D3-style-c (2026-10-13)

**Candidate:** `h4-10-footwork/model_13800`, the best H4 fixed endpoint by the main metric (D-064; runs and decisions in `stage5b-h4.md`, D-056 to D-064).
- **Architecture:** a fresh PPO executor steering the frozen human-motion latent controller (latent-07/10651, lambda 1.0, wrist residual).
- **Baseline:** `student-drill3-style-c/model_10400`, the flat task-optimised student. Its style reward never took (style 4.84, as S-D3b without it), so it is effectively the no-style performance ceiling.

**Protocol:** the Stage 5 gate on both, with the same script (`scripts/h4_eval.sh`, reset fix included) and the same fresh dev seeds 4200490-493.
- 2048 envs × 16 s; real balls, all 14 families.
- Target A/B, with and without the hint; retention vs model_7600; style score.
- Files: `stage5b-h4-gate-{h4-10,sd3stylec}-*.json`.

## Per family, no hint (target A), legal return [95 % CI]
| Family | H4 (h4-10) | S-D3-style-c | Diff | Gate (>= base - 5) | H4 A/B gain [95 % CI] | Base A/B gain |
|---|---|---:|---:|---|---|---:|
| easy forehand | 83.6 % [80.9, 86.1] | 96.1 % | -12.4 | fail | +0.095 [0.070, 0.120] | +0.669 |
| wide forehand | 85.6 % [82.8, 87.9] | 97.3 % | -11.8 | fail | +0.170 [0.145, 0.196] | +0.896 |
| backhand | **0.0 %** [0.0, 0.5] | 97.9 % | -97.9 | fail | 0 | +0.789 |
| deep | 80.3 % [77.3, 83.0] | 96.3 % | -16.0 | fail | +0.104 [0.078, 0.130] | +0.769 |
| short | 83.0 % [79.9, 85.7] | 98.8 % | -15.8 | fail | +0.077 [0.053, 0.101] | +0.739 |
| high | 89.1 % [86.5, 91.3] | 95.6 % | -6.5 | fail | +0.061 [0.035, 0.088] | +0.754 |
| low | 84.7 % [81.9, 87.1] | 97.2 % | -12.6 | fail | +0.217 [0.193, 0.240] | +0.894 |
| fast | 79.8 % [77.0, 82.4] | 98.1 % | -18.3 | fail | +0.137 [0.115, 0.160] | +0.885 |
| topspin | 91.3 % [89.0, 93.1] | 96.8 % | -5.5 | fail | +0.280 [0.256, 0.305] | +0.835 |
| backspin | 88.1 % [85.7, 90.1] | 97.5 % | -9.4 | fail | +0.143 [0.121, 0.164] | +0.482 |
| reach forehand | 67.2 % [63.7, 70.6] | 97.6 % | -30.4 | fail | +0.054 [0.034, 0.074] | +0.847 |
| reach backhand | **0.0 %** [0.0, 0.5] | 24.7 % | -24.7 | fail | 0 | -0.002 |
| reach short | 5.8 % [4.4, 7.7] | 6.1 % | -0.3 | pass | +0.002 [-0.004, 0.007] | +0.019 |
| reach deep | 2.8 % [1.9, 4.2] | 1.8 % | +1.1 | pass | -0.001 [-0.003, 0.001] | +0.001 |
| **Pooled** | **58.4 %** [57.5, 59.4] | 78.7 % [77.9, 79.4] | -20.2 | | | |

| Other | H4 | S-D3-style-c | Target |
|---|---:|---:|---:|
| **Style score** (nearest-clip pose distance; human floor 0.94) | **2.91** | 4.84 | <= 3.86 (**pass**) |
| Contact (no hint) | 69 % | 81 % | |
| Robot falls per episode | 5.7 % | 4.4 % | <= 1 % (Stage 5) |
| Recovery median / p90 | 0.83 / 1.58 m | 0.98 / 2.08 m | <= 0.5 m (Stage 5) |
| Retention vs model_7600 (Stage 4 families, fixed start) | -7 to -28 points (backhand -100) | within 5 points except backspin +9 | within 5 points |

## Verdict
- **H4 gate: not met.** Style passes clearly: H4 moves far more like the human clips. Only reach short and reach deep are within 5 points of the baseline (both students fail those). Every other family is 5.5-98 points behind.
- **What H4 does well:** human-like ready stance, swing and follow-through on balls fed to its forehand side (80-91 % legal, contact 95-98 %). Falls stay low per feed.
- **What it does not do:**
  - **Backhand and every leftward or backward move (0 %).** The robot stays planted while the ball passes on its left (`artifacts/videos/h4/h4-10-backhand-behind.mp4`).
  - **Aiming:** its A/B gain is 0.05-0.28 against the baseline's 0.48-0.90.
  - **Long or fast travel.**
- **Root cause of the movement gap (D-063):** the latent controller is slow and directionally biased. The H3 walker covers about 1.1 m in 2 s forward or right, but only about 0.5 m left or back. Targets 0.8 m away: within 25 cm 99 % forward, 96 % right, 42 % left, 25 % back. Its motion data is right-handed tennis plus mostly forward locomotion.

## Review videos
- `artifacts/videos/h4/h4-10-side.mp4`: 24 s of continuous play, no hint, mixed families.
- `artifacts/videos/h4/h4-10-backhand-behind.mp4`: backhand feeds only, the failure case.

The closer-camera views and the side-by-side follow at the end of the D-065 loop.

## Next (D-065)
1. GPU throughput.
2. A learning-progress curriculum over continuous feed parameters, with every family starting from easy, learnable variants.
3. If movement still does not learn: a backhand-side paddle test, an agility walker as a footwork teacher, then a controller retrain with mirrored LAFAN1 locomotion.
