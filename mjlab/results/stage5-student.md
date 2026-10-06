# Stage 5 student: DAgger distillation of the two teachers (D-042)

Date: 2026-10-06.
- **Teachers:** walking `teacher-move-01/model_15900`, hitting `teacher-hit-b01/model_18600`.
- **Distillation** (`scripts/distill.py`):
  - 4096 envs on the Drill 1 task, 50 % move and 50 % hit episodes; hit episodes use the hitting teacher's feed mix;
  - β (teacher share of the executed action) decays from 1 to 0 over the first 40 % of 1,500 iterations;
  - MSE on deterministic actions, routed by episode type; train seed 1;
  - the student's exploration std is the teachers' mean.
- **Network:** rsl_rl's MLPModel has no LayerNorm, so the students are plain ELU MLPs (a recorded deviation from D-042).
- **Evaluation:** students and teachers on the **same** dev seeds, 4,200,170 (move) and 4,200,171 (hit), with the corrected metric (D-043).

| | Teachers | Big student 1024-512-256 (`student-big-01/model_1500`) | Small control 512-256-128 (`student-small-01/model_1500`) |
|---|---:|---:|---:|
| Final imitation MSE (move / hit) | — | 0.0005 / 0.0010 | 0.0010 / 0.0023 |
| Arrival, all sectors | 99.89 % | **99.89 %** (each sector within 0.4 points) | 99.95 % |
| Ready stance at arrival | 99.97 % | 99.95 % | 99.95 % |
| Legal return, range over 11 families | 98.8–100 % | 98.8–100 % (each within 0.7) | 98.8–100 % |
| Contact | 99.4–100 % | 98.8–100 % | 99.0–100 % |
| A/B gain, overall | +0.855 | +0.823 | +0.822 |
| A/B gain, easy / deep / high / topspin | +0.79 / +0.82 / +0.87 / +0.88 | **+0.64 / +0.76 / +0.82 / +0.84** | +0.62 / +0.72 / +0.88 / +0.81 |
| A/B gain, backspin | +0.58 | +0.65 | +0.71 |
| Retention vs `model_7600` (fixed start) | 97.1 % vs 97.4 % | **96.7 % vs 97.4 %** | 95.4 % vs 97.4 % (backhand −6.8, fast −7.4) |
| Falls | 0 | 0 | 0 |

## What this shows
1. **One network now walks and hits at teacher level.** Drill 1's shared-policy training could not get there. The big student matches the walking teacher exactly (99.89 %) and the hitting teacher's legality within 0.7 points on every family, with no falls.
2. **Aiming precision is partly lost in the copy:** easy −0.15, deep −0.065, high −0.05, topspin −0.033. Both students lose it on the same families, so it comes from the objective rather than capacity. Uniform action-MSE spends almost all its effort on the long stretches between contacts, while placement is decided in the few steps around contact.
3. **Capacity:**
   - The larger student halves the imitation error, but on in-distribution drills it scores the same as the small one.
   - It does better on the out-of-distribution fixed-start retention test: −0.7 points overall vs −2.0, and no family below −4.9 (the small student has two below −5).
   - The big student is kept.

## Student gate (within 3 points of each teacher on legality, contact and A/B gain per family, and on per-sector arrival)
**Not met.** Walking, legality and contact pass. A/B gain misses on easy, deep, high and topspin.

## Follow-up S-b (loop rule 8, 1 of 2), decided before launch
**One change: contact-weighted imitation.** In hit episodes, states with the ball within 1.0 m of the paddle get 10× weight in the MSE. This targets the moments that decide placement.
- Continues from `student-big-01/model_1500`. β = 0 throughout: the student drives from the start, as at the end of the first run.
- 1,500 iterations, same data mix, learning rate and seed.
- Evaluated as above on fresh dev seeds, with the teachers re-scored on the same seeds.
