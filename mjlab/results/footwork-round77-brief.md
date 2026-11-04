# Panel round 77 brief: D-212 reads NO-CANDIDATE, 2026-11-04

Read first:
- D-212 and its result in docs/DECISIONS.md, plus the D-211 addendum;
- round 76 in mjlab/results/footwork-review.md;
- mjlab/results/lev76-summary.txt;
- d1_rule.lever_lines / pooled_hazards;
- the frozen target, mjlab/results/rally-target.md.

## Result

Parent C = rally-d1s3lr3 model_32598. Both runs used training seed 207, 1,200 iterations at LR 3e-5, endpoint model_33797. Reads were on D-204's pooled seeds.

- **Stage 0, Fast4 floor (reported): FLOOR-PASS.** Legs explained 0.966 at lam 3 (line 0.85) and 0.989 at lam 5. D-192's settle and mean-action arrival lines are not yet defined.
- **C2 (the recipe continued): COMPOUND FAIL.**
  - GAIN2 -1.22 points (per seed -0.31 / -1.42 / -2.61 / -0.52).
  - Guards and mechanism pass (ready 0.285, falls 0.87).
  - Recovery error rose 0.275 -> 0.425 m. Mean family shift vs the original parent -1.44.
  - The LR 3e-5 step does not compound.
- **K (C2 + pair_rally_cap 5 in training): LEVER FAIL.**
  - Smoke passed (1.882 vs line 4.157). The dose was delivered: pair-court feeder share 0.273 vs 0.088.
  - Against C2: GAIN2 +2.09 points (lower bound +0.75). OPEN pass (0.472 vs 0.442). FEEDER pass (0.649 vs 0.635). Guards pass.
  - **Fails:** ready 0.211 (bar 0.25), and K3-KEPT (late failure share 0.094 vs 0.040).
  - Recovery 0.175 m (best so far); falls 1.05.

  | hazard | h0 | h1 | h2 | h3 | h4 |
  |---|---|---|---|---|---|
  | K | 0.361 | 0.262 | 0.080 | 0.022 | 0.008 |
  | C2 | 0.376 | 0.292 | 0.072 | 0.021 | 0.005 |
  | C | 0.373 | 0.273 | 0.077 | 0.018 | 0.004 |

- **Post hoc:**
  - K vs C: +0.87 points (lower bound -0.48), P(5+) 0.420 vs 0.4115.
  - K's ended rallies at 5 or more shots: 288, against 48 for C and 55 for C2. The cap meant no pair-court training rally ran past 5 shots. These endings do not lower P(5+).

No candidate, no CONFIRM. C stays the parent. The GPU is idle. Training seeds next 209; dev next free 4220349 (4220349-4220356 reserved for a CONFIRM, unread).

## Questions

1. **Correction check.**
   - Is NO-CANDIDATE valid as pre-registered?
   - Is K3-KEPT's "late failure share" (ended at k >= 3 over reached 3) the right instrument for what coach intended, given that K's extra endings are past shot 5?
   - Anything misstated?
2. **What we learned.**
   - The recipe step did not compound. Is the LR 3e-5 line exhausted?
   - The cap moved the opening hazards the right way (h0 -1.5, h1 -3.0 points vs C2) but cost long-rally play and the ready stance. Is the cap the right lever at a different dose? For example a cap of 8-10, or the cap on a share of courts (pair_drill_court_frac is 0.5 now).
3. **Next step.** Vote with coded lines, kill checks and seeds:
   - **(i) The cap at a milder dose** (one knob), on C, against C2 as the matched reference. Name the dose.
   - **(ii) The d1b route:** define and run D-192's Fast4 settle and arrival checks (reads only), then the base rebuild with Fast4 as the footwork teacher if they pass. This is the agility route the user asked for.
   - **(iii) Another opening lever:** pre-bounce approach_far (motion, new code) or IdleRec.
   - **(iv) Other.**
