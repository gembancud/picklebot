# Stage 5 hitting teacher: chain runs 1–2, then a backspin follow-up

Date: 2026-10-06. Task `Picklebot-Teacher-Hit-G1`: hitting only, with the Stage 4 families plus reach_forehand at equal weight, random starts, aiming targets, the recovery command and free feet. Parent: `footwork-f02/model_12000`. All numbers use the corrected metric (D-043: feeds cut off by the episode time limit are excluded). Evaluation: 2048 envs × 16 s, paired targets A/B, random starts. Retention: the Stage 4 families from the fixed start versus `aim-all-c01/model_7600` on the same feeds, both scored with the corrected metric.

| | Run 1 `teacher-hit-01/model_14200` (seed 4,200,140) | Run 2 `teacher-hit-02/model_16400` (seed 4,200,150) |
|---|---:|---:|
| Legal, 10 non-backspin families | 98.4–100 % | 99.3–100 % |
| **Legal, backspin** | **83.6 %** | **83.5 %** |
| Contact, all families | 98.9–100 % | 99.4–100 % |
| A/B gain, overall | +0.820 [0.815, 0.825] | +0.807 [0.802, 0.812] |
| A/B gain, backspin | +0.124 | +0.102 |
| Falls per robot episode | 0 | 0 |
| Recovery error (median) | 0.88 m | 0.93 m |
| Retention, overall | 95.9 % vs 97.4 % | 95.2 % vs 97.5 % |
| Retention, worst families | backspin −13.6, backhand −4.9 | backspin −6.8, deep −6.6, low −6.6, fast −4.9 |

**Rule 9:** run 2 improved the main metric by less than 1 point (backspin legal 83.6 → 83.5 %). Chaining stops, and the teacher's endpoint is `teacher-hit-02/model_16400`.

**Gate** (legal ≥ 85 % per family, contact ≥ 92 %, A/B gain > 0 per family, retention within 5 points): **not met.**
- Missed: backspin legal (83.5 %), and retention on deep, low and backspin (−6.6 to −6.8).
- Met: everything else. Contact, aiming and falls pass easily.

## Notes
- **Backspin is the only family the teacher has not mastered.** It touches 100 % of backspin balls, but 16 % are not legal, and aiming hardly works on it (gain ≈ 0.1). Backspin has been the weakest family since Stage 4.
- **The fixed-start retention test may now partly measure a geometry mismatch rather than forgetting.** In that test, feeds are aimed at the fixed start spot (y = 0.35 m), while the robot recovers to the commanded spot (baseline centre, y = 0). From its own random starts, where feeds follow the robot, the same families score 99.3–100 %. Recorded as an open point; the test definition is not changed here.

## Follow-up HT-b (loop rule 8, follow-up 1), decided before launch
**One change: backspin weight ×3 in the hitting-teacher feed mix.** The other ten families stay at weight 1, so backspin rises from 9 % to 23 % of feeds. Warm start from `teacher-hit-02/model_16400`; evaluation as above on a fresh dev seed.

## Follow-up HT-b result: gate PASSED (`teacher-hit-b01/model_18600`, dev seed 4,200,160)
Backspin weight ×3, warm-started from `teacher-hit-02/model_16400`, iterations 16,400 → 18,622.

| | Run 2 | HT-b |
|---|---:|---:|
| Legal, backspin | 83.5 % | **99.1 %** |
| Legal, all other families | 99.3–100 % | 99.2–100 % |
| Contact | 99.4–100 % | 99.2–100 % |
| A/B gain, overall / backspin | +0.807 / +0.102 | **+0.851 / +0.591** |
| Retention vs `model_7600` | 95.2 % vs 97.5 % | **97.45 % vs 97.44 %**; every family within ±3.3 points (backspin +6.9) |
| Falls | 0 | 0 |

**Gate met** on every criterion: legal ≥ 85 %, contact ≥ 92 %, A/B gain > 0 and retention within 5 points, on every family. **Hitting teacher: `teacher-hit-b01/model_18600`.** Fixed-start retention also recovered, so the earlier deep/low/backspin retention misses were mostly unfinished training rather than the geometry effect noted above.
