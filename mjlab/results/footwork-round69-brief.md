# Panel round 69 brief: diag68 routes STATE; design the lever while the drift control trains, 2026-11-02

Read first:
- D-204 and its addendum in docs/DECISIONS.md;
- round 68 in mjlab/results/footwork-review.md;
- mjlab/results/diag68-summary.txt;
- `recovery_reward` in mjlab/picklebot_mj/tasks/return_stand.py;
- the d1s6 design flaw in round 67 (`parked_ready`'s speed x distance value paid stopping, not reaching the spot).

## Result: (i) diag68, verdict STATE

Parent d1s3 model_31399, LR-0, 0.5-s refeed, seeds 4220332 + 4220337 summed (addendum: the first seed alone had 939 < 1,000 k = 1 balls in the band). Pair courts, matched band, second half.

**STATE** (k = 1 top - bottom tercile failure >= 0.10 while k >= 3 stays <= 0.05):

| variable | k = 1 gap | k >= 3 gap | result |
|---|---|---|---|
| pelvis_speed | 0.179 | 0.016 | fires |
| recover_dist | 0.138 | 0.023 | fires |

**BALL** (reweighting removes >= half the k = 1 excess): none fires.

| variable | share of the excess removed |
|---|---|
| bounce_depth | 0.327 |
| angle | 0.138 |
| net_clear | 0.082 |
| spin | -0.055 |

**RESTART (reported, all bands):** k = 1 / 2 / 3+ failure is 0.323 / 0.156 / 0.039 at 0.5 s and 0.295 / 0.161 / 0.042 at 3.0 s.

**Route, pre-registered:** STATE only -> recovery to ready at rally start / after misses.

Motion's mechanism (round 68): `recovery_reward` pays exp(-(d / 0.5)^2) only after the robot's own legal hit (`* t.hit_done`). The receiver of the first handed ball has had no hit in the rally, so nothing pays it to be at its spot. It stands wherever the last rally left it.

## In progress

**(iii) The drift control** rally-d1s3ctlb (training seed 197; relaunched after a task-entry fault) is training. Then come the pooled 4-seed guard reads and GUARD-N / DRIFT.
- All five members said no new lever trains before (i) and (iii) are both in.
- This round designs the lever so it can launch right after (iii).
- **Do not use the GPU.**

## Questions

1. **Correction check.**
   - Is STATE valid as computed (diag68_route, the summed counters)?
   - Anything the summary or brief misstates?
   - Does the 3.0-s read change the reading?
2. **The lever (one change).** Candidates:
   - **(a) Extend recovery_reward** to pay from rally start / after a miss, not only after the robot's own hit. The value is distance only (no speed factor, unlike d1s6), same std and weight, no new observation.
   - **(b) The same, for the partner of the feeder ball's receiver only** (the k = 1 receiver), during the feeder ball's flight.
   - **(c) Other.**
   - Give the mask precisely (which envs, which steps; live court only? dead court?) and how it avoids d1s6's failure (paid for stopping) and d1s4's (planted feet at contact).
3. **Lines, with seeds.** The lever's kill and endpoint lines:
   - **DOSE:** the k = 1 receiver's state at the hand-off: recovery distance and / or pelvis speed vs the parent, from the split tally.
   - **The k = 1 hazard:** a primary line?
   - F-UP / P5 / GUARDS: per round 68, against the parent (pooled, 4 seeds) and the control.
   - RL's unconditional control: the drift control just trained may serve, if the seed and settings match.

Seeds: dev free from 4220338 (4220338-4220340 held for re-reads); training from 199.
