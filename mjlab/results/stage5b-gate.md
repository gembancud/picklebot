# Stage 5B gate (H4): **MET** — paired final evaluation of h4-25b against S-D3-style-c (2026-10-14)

**Candidate:** `h4-25b-more/model_27700`, the best H4 fixed endpoint by the main metric (D-065; 25 runs in `stage5b-h4.md`, decisions D-056 to D-073).
- **Architecture:** a PPO executor steering the frozen human-motion latent controller (latent-07/10651, lambda 1.0, wrist residual).
- **Training:** a learning-progress feed curriculum, return shaping with a real net-clearance reward, and a prior-likelihood latent penalty.

**Baseline:** `student-drill3-style-c/model_10400`, the flat task-optimised student (style 4.84: effectively no human style).

**Protocol:** the Stage 5 gate on both, with the same script (`scripts/h4_eval.sh`) and the same fresh dev seeds 4200570-573.
- 2048 envs × 16 s; real balls, all 14 families.
- Target A/B, with and without the hint; retention vs model_7600; style score.
- Files: `stage5b-h4-gate2-{cand,sd3stylec}-*.json`.

## Per family, no hint (target A), legal return
| Family | H4 (h4-25b) | S-D3-style-c | Diff | Gate (>= base - 5) | H4 A/B gain [95 % CI] |
|---|---:|---:|---:|---|---|
| easy forehand | 96.6 % | 95.3 % | +1.3 | pass | +0.667 [0.644, 0.691] |
| wide forehand | 98.0 % | 97.4 % | +0.6 | pass | +0.732 [0.711, 0.752] |
| backhand | 96.6 % | 97.1 % | -0.5 | pass | +0.581 [0.557, 0.605] |
| deep | 98.2 % | 95.1 % | +3.1 | pass | +0.683 [0.660, 0.707] |
| short | 97.8 % | 97.8 % | 0.0 | pass | +0.666 [0.644, 0.689] |
| high | 98.3 % | 96.0 % | +2.3 | pass | +0.586 [0.561, 0.611] |
| low | 97.5 % | 98.3 % | -0.8 | pass | +0.706 [0.684, 0.728] |
| fast | 94.9 % | 97.5 % | -2.5 | pass | +0.643 [0.620, 0.666] |
| topspin | 96.1 % | 96.5 % | -0.4 | pass | +0.752 [0.731, 0.773] |
| backspin | 97.4 % | 97.3 % | +0.1 | pass | +0.579 [0.556, 0.602] |
| reach forehand | 93.7 % | 97.0 % | -3.3 | pass | +0.566 [0.540, 0.592] |
| reach backhand | **90.1 %** | 27.4 % | +62.6 | pass | +0.304 [0.277, 0.330] |
| reach short | **83.6 %** | 5.3 % | +78.3 | pass | +0.643 [0.618, 0.667] |
| reach deep | **73.3 %** | 1.4 % | +71.9 | pass | +0.130 [0.107, 0.152] |
| **Pooled** | **93.9 %** [93.4, 94.3] | 78.3 % [77.6, 79.0] | +15.6 | | |

| Other | H4 | S-D3-style-c | Target |
|---|---:|---:|---|
| **Style score** (nearest-clip pose distance; human floor 0.94) | **3.81** | 4.84 | <= 3.86 (**pass**) |
| Contact (no hint) | 98.3 % | 80.8 % | |
| Legal with the stance hint (target A) | 90.3 % | 80.3 % | |
| Robot falls per episode | 1.68 % | 4.51 % | <= 1 % (Stage 5) |
| Recovery median / p90 | 0.275 / 1.18 m | 0.975 / 2.08 m | <= 0.5 m (Stage 5) |

## Verdict
**H4 gate (D-056 target a): MET.**
- Every family is within 5 points of S-D3-style-c or better; seven are better.
- Style 3.81 <= 3.86.
- Target hits and A/B gain are reported with intervals; the gain CI is above 0 on all 14 families.

The H4 executor plays the whole Drill 3 ball-machine drill with human-like motion at better-than-baseline task performance. It returns 93.9 % against 78.3 %, and the reach families that the flat student could not play reach 73-94 %.

**Original Stage 5 thresholds (D-056 target b), reported:**

| Threshold | H4 | |
|---|---|---|
| Stage 4 legal >= 85 % (94.9-98.3 %) and contact >= 92 % (>= 99.2 %) | met | ✓ |
| A/B gain CI > 0 on every family | met | ✓ |
| Recovery <= 0.5 m | 0.275 m | ✓ |
| Reach >= 75 % | forehand 93.7, backhand 90.1, short 83.6 | 3 of 4 ✓ |
| | **reach deep 73.3 %** | ✗ (-1.7) |
| **Falls <= 1 %** | 1.68 % | ✗ |
| **Retention within 5 points of model_7600** (Stage 4 families from the old fixed start) | fast -24.2, low -13.3, backhand -10.1 | ✗ |

On retention: H4 was trained only from the randomised start box, never the Stage 4 fixed start.

## Review videos (`mjlab/artifacts/videos/h4/`, dev seeds 4200575-576)
- `gate2-side.mp4` and `gate2-behind.mp4`: 24 s of continuous drill play with close cameras, no hint, all families, several feeds per robot episode.
- `gate2-vs-sd3stylec.mp4`: side-by-side on the same feeds; **left H4, right S-D3-style-c**.
- `gate2-backhand.mp4`: backhand and reach-backhand feeds from behind.

## History
The first gate attempt, h4-10 on 2026-10-13 (pooled 58.4 %, backhand 0 %), is kept in `stage5b-h4.md` (runs 1-10 and D-063). Its paired files are `stage5b-h4-gate-*.json`.

## Next
Stage 5C, full-court coverage (D-069). The executor still plays from near the baseline centre: feeds come within 2.5 m of wherever it stands, there is no net play and no volleys, and its leftward and backward speed is limited (D-063).
