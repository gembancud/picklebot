# Panel round 67 brief: d1s6 (parked readiness) reads NO-DOSE, 2026-11-02

Read first:
- D-202 in docs/DECISIONS.md;
- round 66 in mjlab/results/footwork-review.md;
- mjlab/results/d1s6-summary.txt (and .json);
- mjlab/scripts/diag/d1_stage6.sh;
- `parked_mask` / `parked_ready` in mjlab/picklebot_mj/tasks/footwork_specialist.py.

## Result

d1s6 = the parent d1s3 child (model_31399) trained 1,200 iterations with one change: parked_ready, weight 2. It pays ready_value only while both robots are parked on a dead court, not busy and not young. Endpoint model_32598. Verdict **NO-DOSE** (first in precedence; GUARDS also failed).

**The run itself was clean:**
- smoke 2.82 falls (half-split 5.26 -> 0.92);
- every +360 line CONTINUE: falls 1.60, legal_return 0.804;
- mean rally length 3.64 vs the parent's 3.26, so no farming;
- speed kept: sustained left / back 1.62 / 1.79 vs 1.61 / 1.77.

**Training dose log (report only):**

| point | paid share of dead-court env steps | mean value when paid |
|---|---|---|
| smoke start | 13.5 % | about 0.10 |
| smoke end | 13.5 % | 0.20 |
| +360 | 9.3 % | 0.27 |
| end | 8.6 % | 0.29 |

**Endpoint vs parent, same dev seeds:**

| line | child | parent | result |
|---|---|---|---|
| DOSE: pelvis speed p50 at the feeder fire | 0.284 | 0.278 | need <= -0.05: fail |
| DOSE: recovery distance p50 at the fire | 0.997 | 0.893 | need <= -0.10: fail |
| F-UP: pairs feeder legal | 0.6076 (low 0.590) | 0.6285 | fail |
| F-BIN: 0-1 launch bin feeder legal | 0.6905 | 0.7505 | fail |
| F-BAND: k = 0 matched-band contact | 0.892 | 0.905 | fail |
| P5-KEPT: P(5+) open | 0.3716 | 0.3873 | fail |
| REFEED3: feeder legal at 3 s | 0.727 | 0.756 | fail |
| K3-KEPT: k >= 3 legal | 0.968 | 0.959 | kept |
| AGILE-KEPT: R_LB | 0.847 | 0.824 | kept; first step left / back no slower |
| partner legal | 0.9923 | 0.9917 | |
| h5f court falls | 5.19 % | 6.2 % | target 4 % |

**GUARDS: breached.**
- fast contact 0.389 vs 0.514 (-12.5);
- easy_forehand contact 0.620 vs 0.704 (-8.3);
- left + back feeder contact 0.384 vs 0.437 (-5.2).

**Rally gate:** not met. 22b (reported): P(5+) 0.390, feeder 0.646.

**Pattern across the last three feeder runs:**
- d1s4: readiness at events (D-200, NO-DOSE with harm);
- d1s5: the rally cap (D-201, SMOKE-FAIL);
- d1s6: parked readiness.

None moved the feeder ball. Both reward runs cost fast / left / back contact. In training the paid value rose (0.10 -> 0.29), yet at the evaluated fire the robot is no slower and is further from its spot.

**Known (round 65):** the policy does not observe parked, court_dead, the refeed timer or the next receiver. The term pays for a state the policy cannot identify from its inputs.

Nothing is running. The GPU is idle.

## Questions

1. **Correction check.** Are the DOSE / GUARDS reads valid?
   - The dose runs use the BallIdx-Feeder task, LR 0, 4096 envs, on dev 4220326, for both parent and child.
   - The parent's dose read was copied from d1s5, at the same checkpoint, base and seed.
   - Does a falling paid share (13.5 % -> 8.6 %) with a rising value mean anything measurable?
2. **Why no dose?** Unobservable state, the weight, the size of the paid window, or the recover_xy definition? Name a read that tells them apart cheaply (CPU or one short GPU read), if one is worth doing.
3. **Next step.** Vote, with coded lines and seeds:
   - **(i) (d): observe the restart.** Add parked / countdown / next receiver (and/or court_dead) to the observations. This needs actor and critic input-layer warm-start surgery. Queued by RL "first if (b) reads NO-DOSE".
   - **(ii) (d) plus parked readiness together.** Two changes; justify if you vote for it.
   - **(iii) The falls lever.** Court falls 5-6 % vs the 4 % target, a separate target line.
   - **(iv) Leave the feeder premise for now and take another target line or the queued agility work.** Options: d1 + --recover, d1b, the Fast4 floor test (dev 4220248), H1''.
   - **(v) Other.**

Seeds: dev next free 4220328 (4220328-4220335 reserved for d1s6 new reads, unused); training next free 197.

**Correction (after the reviews):** the dose log is cumulative. The windowed value per paid step was flat at 0.27-0.29 from iteration 10, and the paid share fell 13.4 % -> 8.1 %. The term was never climbed. The "rose 0.10 -> 0.29" above is wrong.
