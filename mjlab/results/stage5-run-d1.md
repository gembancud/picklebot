# Stage 5 Drill 1 run D1 (`drill-move-d01`): it walks to spots, weaker on its right

Date: 2026-10-06. Task `Picklebot-Drill-Move-G1`:
- 75 % move-to-spot episodes, using mjlab's tracking formulas against an unobserved internal command toward the spot, an arrival bonus and a ready stance;
- 25 % Stage 4 hitting rehearsal from random starts.

Warm-started from `footwork-f02/model_12000` (same inputs). 4096 envs, train seed 1, 7,000 s cap: iterations 12,000 → 13,973. **Fixed endpoint `model_13900`.**

## Training
- **Healthy:** value loss 0.04–0.07, action std 0.74 → 0.57, falls 0–0.13.
- **Walking reward:** move_track_lin_vel 0.01 → 1.1 within ~500 iterations.
- **Arrival reward:** first arrivals by ~12,250, rising to ~0.10 per episode by 13,500, then flat.
- **Ready stance:** ~0.31.
- **Hitting rehearsal:** legal return 0.35–0.45.

## Movement evaluation (dev seed 4,200,100; 2048 envs × 24 s; move episodes only; 16,020 finished spots)
| Direction (from the robot) | Finished | Arrival | Mean time | Median final error | Ready stance at arrival |
|---|---:|---:|---:|---:|---:|
| forward | 2,474 | 97.7 % | 2.66 s | 0.225 m | 99.96 % |
| forward-left | 2,512 | 98.6 % | 2.60 s | 0.175 m | 100 % |
| left | 2,013 | 97.4 % | 2.46 s | 0.175 m | 99.9 % |
| back-left | 1,631 | 99.6 % | 2.20 s | 0.175 m | 99.8 % |
| back | 1,445 | 94.5 % | 2.15 s | 0.225 m | 100 % |
| **back-right** | 1,562 | **63.0 %** | 2.28 s | 0.225 m | 99.9 % |
| **right** | 1,962 | **82.6 %** | 2.52 s | 0.225 m | 99.9 % |
| **forward-right** | 2,421 | **88.0 %** | 2.63 s | 0.225 m | 100 % |
| **all** | 16,020 | 91.0 % | — | 0.225 m | 99.9 % |

- **Falls:** 0 in 6,144 robot episodes.
- **Fewer back spots were issued:** spots that would leave the half court are reversed, and robots near the baseline have little room behind them.

**Before Drill 1 (F2, the same robot lineage)**, the robot could not move left, forward or back at all. **It now walks to 94–99.6 % of spots in five of eight directions,** and stops in a ready stance on essentially every arrival.

## Hitting retention (Stage 4 families, fixed start, hitting only, target A; vs `model_12000` on the same feeds)
Overall 80.1 % vs 82.2 % (−2.0 points). Per family:

| Change | Families |
|---|---|
| Down by more than 5 points | low −6.7, fast −7.0, backspin −7.6 |
| Down by 1–4 points | easy −3.1, wide −3.8, backhand −4.0, deep −1.4, topspin −1.2 |
| Up | short +7.2, high +7.1 |

## Against the Drill 1 gate
| Criterion | Result | Verdict |
|---|---|---|
| Arrival ≥ 90 % in every sector | back-right 63.0 %, right 82.6 %, forward-right 88.0 % | **fail** (3 sectors) |
| Median final error ≤ 0.25 m | 0.175–0.225 m in every sector | pass |
| Ready stance ≥ 80 % of arrivals | 99.9 % | pass |
| Falls ≤ 1 % per robot episode | 0 % | pass |
| Hitting retention within 5 points (per family) | low −6.7, fast −7.0, backspin −7.6 | **fail** (3 families; overall −2.0) |

## Diagnosis
- **The misses are all on the robot's right**, its paddle side. The right-side sectors time out, where the left-side ones arrive in 2.2–2.6 s. This mirrors F1/F2, where the right was the only direction it could move, and suggests the old lean-right habit conflicts with stepping right properly.
  - Uniform spot sampling gives the right-side sectors no extra practice.
- **Hitting retention losses** are on low, fast and backspin balls. These are timing-critical families, and hitting gets only 25 % of episodes.

## Follow-up D1b (loop rule 8, decided before launch)
**One change: oversample the three right-side sectors (back-right, right, forward-right) ×2 in training spot sampling.** Evaluation stays uniform.
- Everything else is unchanged; warm start from `drill-move-d01/model_13900`; evaluation on a fresh dev seed.
- If retention still fails after D1b, the second permitted follow-up (D1c) will change the hitting-rehearsal share (25 % → 40 %).

Files: `stage5-d1-move.json`, `stage5-d1-retention-A.json`, `stage5-d1-retention-parent-A.json`.
