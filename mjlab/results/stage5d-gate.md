# Stage 5D gate: rally training — NOT MET (2026-10-17)

The loop ended under the plateau rule (D-091, D-096). Runs 2, 3 and 4 each failed to improve P(rally >= 10) on run 1 by 2 points. Run 4 was within 3 points of the best, so it was repeated on a second seed, and the repeat confirmed the third strike. **4 of the 15 training runs were used.** No consolidation run was reached.

**Final candidate** (D-096/D-097/D-098): **run 1, `s5d-01-rally/model_1800`.**
- **Why run 1:** it has the highest mean P(rally >= 10) of runs 1-4 on the same two dev seeds, 4200961/4200962 (9.58 %; runs 2-4: 7.91 / 8.44 / 7.87 %).
- **Label: "best rally, failed kill rules".** Its style (4.199) was over the kill threshold (4.17), and every run 1-4 hit a kill rule. Run 22, the best run that passed its kill rules (the stage start), is paired next to it.
- **What it is:** a residual executor around frozen run 18, continued from run 22 by PPO on the rally drill (court-anchored feeds, 30 s episodes, rally bonus).

**Paired final evaluation:**
- **Rally and court:** candidate and run 22 on the same four fresh dev seeds, 4200325-4200328 (rally) and 4200335-4200338 (court).
- **Candidate's other gate jobs:** once, on seeds 4200345-4200350.
- **Seed separation:** these seeds are disjoint from the selection seeds. No final seeds were used.

## Gate

| Criterion | Threshold | Candidate (run 1) | Run 22 (stage start) | Met? |
|---|---|---|---|---|
| P(rally >= 10), 90 s, no hint, pooled over 4 seeds | >= 20 % | **9.59 %** [9.27, 9.91] (3,068 of 32,005 rallies) | 1.75 % [1.64, 1.87] | no |
| Court falls | <= 1 % | **5.9 %** per episode (4 seeds: 6.2 / 6.0 / 5.8 / 5.6 %); move drill 0.11 % | 3.3 % | no |
| Style (nearest clip, tennis-v5 + LAFAN1) | <= 3.86 | **4.202** | 4.017 | no |
| Move-to-spot arrival, every direction | >= 90 % | **99.7-100 %** (fwd 99.9, fwd-left 100, left 100, back-left 99.8, back 99.7, back-right 99.7, right 99.96, fwd-right 99.9) | 99.4-99.95 % | **yes** |
| Court drill main metric | >= 76.8 % | **78.3 %** [78.0, 78.6] (68,991 feeds) | 78.8 % | **yes** |

**2 of 5 gate items are met** (arrival, court main metric).
- **Rally:** the candidate is 10.4 points short of 20 %.
- **Falls:** they rose from 3.3 % to 5.9 %.
- **Style:** it moved away from the gate, 4.02 -> 4.20.

**Other results (not 5D gate items):**
- Court cells >= 75 %: 39 / 55 (run 22: 41 / 55).
- Recovery: 1.175 m on the time model (gate in 5C: 0.5 m).
- Extra rally seed 4200350: 9.06 % [8.46, 9.70].
- The Stage 5B backspin family is 34 points below h4-25b. The other 13 Stage 5B families are within 5 points, most of them above.

## Why the rally gate is far away: per-shot reliability

Feeds are drawn independently, so P(rally >= 10) is close to p^10, where p is the per-shot legal rate on court-anchored feeds.

| Executor | Per-shot p (pooled, 4 seeds) | p^10 | Measured P(rally >= 10) | Mean ended rally |
|---|---:|---:|---:|---:|
| run 22 | 62.5 % [62.2, 62.7] (138,602 feeds) | 0.9 % | 1.75 % | 1.46 |
| **run 1** | **77.4 %** [77.2, 77.7] (135,957 feeds) | 7.7 % | **9.59 %** | 2.69 |

The measured value sits a little above p^10. Time-outs end a rally without counting as a failure, and some families are easier from some positions. **The 20 % gate needs p of about 0.85.** Run 1 gained 15 points of per-shot reliability. The last 8 points sit in a few families that none of runs 1-4 moved (court drill, pooled over 4 seeds):
- **Volleys:** 0 % in all four cells.
- **reach_deep:** 17.9 / 28.9 / 61.1 % (front / mid / back).
- **lob:** 31.3 / 48.9 % (front / mid).
- **backspin@back:** 53.3 %.
- **cross_backhand:** 54.9 / 71.3 / 73.1 % (front / mid / back).
- **reach_short@mid / drop@mid:** 64.6 / 66.4 %.

Every other cell is >= 75 %, most of them above 90 %.

## Runs

| # | Change (written before launch) | P(rally >= 10) | Same-seed mean (4200961/2) | Kill rule hit |
|---|---|---:|---:|---|
| 1 | PPO continuation of run 22 on the rally drill (D-092) | 9.67 % | **9.58 %** | style 4.199 (> 4.17) |
| 2 | + style anchor: prior penalty on the composite latent, 0.05 (D-093) | 7.65 % | 7.91 % | arrival right 85.8 % (< 90 %) |
| 3 | + overspeed penalty -0.5 (v - 1.2)^2 (D-094) | 8.70 % | 8.44 % | style 4.210 |
| 4 | + gait anchor to the walking teacher while walking (D-095) | 8.0 % | 7.87 % | style 4.184 |

Full log: [stage5d.md](stage5d.md).

## Deviations and caveats (stated in full)

1. **The candidate failed its kill rule** (style). Under D-096 the user fixed, before run 4's result, that the best rally run is the candidate whatever its kill rules. A reviewer objected; the user kept the rule (D-098). Run 22 is reported beside it as the best passing run.
2. **Runs 2-4 never compounded on run 1.** Each started from run 22, because run 1 had failed its kill rule. The plateau bar came from a killed run.
3. **Runs 2 and 3 were under-dosed.**
   - The style anchor at 0.05 moved style by about -0.05.
   - The overspeed penalty barely engaged.
   - Neither weight was sized offline against the task reward. D-097 requires that sizing for Stage 5E.
4. **Run 4's gait anchor was flawed.** It matched all joints, arms included, and paid only while the ball was more than 1 m away (D-096).
5. **Run 1 bundled a bug fix:** the court-anchor flag was restored on re-feeds (D-092), on top of the PPO continuation.
6. **Kill rules did not watch court falls.** Court falls have been 3-6 % since Stage 5C, and every 5D run raised them (4.7-6.1 %).
7. **The style gate as measured is probably out of reach on this drill.**
   - Fast poses (>= 0.8 m/s) score about 4.5 for every executor, because the reference has no running with a paddle.
   - h4-25b itself scores 3.88 on the court drill.
   - Rally training raises the fast share from 32 % to 39 % (D-094).
   - Stage 5E adds 100STYLE footwork to the reference (D-097/D-098).
8. **D-097 named out-of-range seeds** (4201000/4201001). The evaluator rejected them before anything ran, and they were replaced with unused dev seeds (D-098).

## What Stage 5D established

1. **Rally training works, but only up to per-shot reliability.** Court-anchored feeds plus a rally bonus raised P(rally >= 10) 5.5-fold (1.75 -> 9.6 %) and per-shot p by 15 points, at no cost to arrival or the court main metric.
2. **Style, speed and gait penalties on the residual did not lower style.** Each cost rally. The problem is in the reference and the drill (fast poses, sprints back to a fixed recovery spot), not the weights.
3. **The remaining misses are specific families.** They need targeted fixes: interception (stance) spot, failure-weighted feeds, a backspin teacher, volleys. More rally PPO does not reach them.

## Next: Stage 5E (D-096..D-098)

Planned in [MJLAB_PIVOT.md](../../docs/MJLAB_PIVOT.md#stage-5e--rally-drill-v2-stance-spot-footwork-style-d-096d-098):
- **Drill v2:**
  - realistic feed mix;
  - recovery that depends on the contact position;
  - pacing set by the robot's own return.
- **Stance-spot planner** fed by noisy, delayed ball state.
- **Sim-to-real latency and noise.**
- **Consolidation, then one change per run:** falls fix, stance spot, failure-weighted feeds, backspin teacher.
- **Footwork style** from 100STYLE (downloaded and verified 2026-10-17, CC BY 4.0).

Gate: per-shot p >= 0.80 with group floors. That implies about 11 % P(rally >= 10), below this stage's 20 %. The stretch target p >= 0.85 matches it.

## Review videos

Candidate and run 22 on the same dev seeds, 4200360-4200364: `mjlab/artifacts/videos/h5c/share5d/`.
- **Clips:** side, behind, kitchen, move, long rally.
- **Formats:** each clip as an H.264 faststart MP4 plus a GIF preview.
- **Files:** `s5d-01-*` (candidate) and `s5d-base22-*` (run 22).
