# Panel round 78 brief: D-213 reads TEACHER-NOT-READY, 2026-11-04

Read first:
- D-213 and its result in docs/DECISIONS.md;
- round 77 in mjlab/results/footwork-review.md;
- mjlab/results/d1b-summary.txt, plus results/d1b-teacher-fast4.json and -fw.json;
- the frozen target, mjlab/results/rally-target.md.

## Result

Stage A ran on dev 4220357, paired: Fast4 (fw-fast4-01 model_18099) against fw1b-S model_16600 on Measure60-Court (0.5-3 m spots, mean actions).

| line | Fast4 | fw1b-S | pass |
|---|---|---|---|
| VALID: falls; worst arrival; fallen + censored | 0.000; 0.997; 0.049 | 0.024; 0.970; 0.055 | yes |
| ARRIVE | 0.997 | 0.970 | yes |
| SETTLE, left / back | 0.304 / 0.398 | 0.272 / 0.197 | yes |
| FIRST-STEP p50, left / back | 1.374 / 1.315 s | 1.362 / 1.411 s | **no** (left 0.012 s slower) |
| FASTER, sustained p50 left / back | 1.095 / 1.072 m/s | 1.071 / 0.989 m/s | **no** (+0.024 / +0.082; needs +0.10 each) |

- Reported: at court scale both teachers sustain about 1.0-1.1 m/s and peak (p50) at about 1.3-1.5 m/s in every sector. Fast4's 4-6 m speed gain (D-191) does not appear at court scale. Fast4 settles more and falls less.
- **Verdict TEACHER-NOT-READY.** No rebuild. Training seeds 209-210 and dev 4220358-4220364 are unused.

## Where we stand

- **Parent:** C = rally-d1s3lr3 model_32598. P(5+) 0.41; feeder legal 0.64; hazards h0 0.37, h1 0.27.
- **Target:** 0.80. Court falls (R3) still cannot be read: the pairs counter is broken.
- **Closed or parked since round 74:**
  - backhand reweighting;
  - the plain LR 3e-5 continuation;
  - the cap at 5 (opening gain, but long-rally and ready-stance cost);
  - the Fast4 teacher swap.
- **Coded and queued:**
  - d1 + --recover (RL): the kickstart's ball-episode footwork, D-195's gap;
  - IdleRec on C (architecture): the task and s8_climb_kill exist; its only smoke failed at LR 1e-4.
- **Not coded:**
  - pre-bounce approach_far (motion, about 3 lines);
  - restart-state starts (coach);
  - the cap on a share of courts (about 20 lines);
  - the court-falls counter fix.
- **Motion's round-77 read:** in rallies the robot peaks (p90) at about 2.0 m/s, and misses on the left / deep / fast balls peak at 1.6-1.8 m/s, ending 0.8-0.9 m from the ball. The p90 and p50 figures above are not directly comparable.

The GPU is idle. Training seeds next 211; dev next free 4220365 (4220349-4220356 reserved unread for a CONFIRM).

## Questions

1. **Correction check.** Is TEACHER-NOT-READY valid as pre-registered? Was the court-scale read the right instrument for the teacher question? Anything misstated?
2. **What we learned.** If neither teacher moves faster than about 1.1 m/s sustained on court-scale spots, is the speed limit in the teacher or in the task (short spots, deadlines)? What does that say about the agility route toward 3-4 m/s?
3. **Next step.** Vote with coded lines, kill checks and seeds:
   - **(i)** IdleRec on C;
   - **(ii)** d1 + --recover;
   - **(iii)** pre-bounce approach_far on C (new code);
   - **(iv)** fix the court-falls counter first (needed before any target claim);
   - **(v)** other, including a STOP vote. Under D-169 a STOP moves to the next phase rather than ending the climb.
