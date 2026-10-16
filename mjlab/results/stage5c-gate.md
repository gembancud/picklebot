# Stage 5C gate: full-court coverage — NOT MET (2026-10-16)

The loop ended under the plateau rule (D-075 rule 6, D-090). Three executor runs in a row (18, 19, 22) each improved the main metric by less than 1 point. **21 of the 30 training runs were used**: 1, 2, 3b, 5-19, 20b, 21, 22. Run 4 was never run; runs 3 and 20 crashed or were aborted at start-up and are not counted.

**Final candidate,** named before the final evaluation (D-090): **run 22, `s5c-22-res-rally/model_900`.**
- **What it is:** a residual executor around the frozen two-skill executor run 18, trained with half of its feeds aimed at the court.
- **How it acts:** z = mu_p + 3 sigma_p tanh(a_18) + 1 sigma_p tanh(a), through the latent-07 motion controller.

**Paired final evaluation:**
- **Court drill:** candidate and stage baseline h4-25b on the same four fresh dev seeds, 4200900-903, pooled per cell under the rule declared in D-086 (`stage5c-final-{cand,base}-pooled.json`, per seed `-court-0..3.json`).
- **Other gate jobs:** dev seed 4200904 (`stage5c-final-cand-*.json`).
- No final seeds were used.

## Gate

| Criterion | Threshold | Candidate (run 22) | h4-25b (stage start) | Met? |
|---|---|---|---|---|
| Every family in every court zone | >= 75 % legal | **41 / 55 cells** (pooled over 4 seeds; 67,769 feeds) | 14 / 55 | no |
| Court main metric (pooled legal, no hint) | (plateau metric) | **78.8 %** [78.5, 79.1] | 51.9 % [51.5, 52.3] | — |
| Move-to-spot arrival, every direction (0.5-3 m) | >= 90 % | **99.4-99.95 %** (fwd 99.6, fwd-left 99.4, left 99.4, back-left 99.5, back 99.8, back-right 99.8, right 99.8, fwd-right 99.95) | 0 % | **yes** |
| Volleys | >= 75 % legal | **0 %** in all 4 cells (contact <= 3 %) | 0 % | no |
| Recovery | <= 0.5 m | **1.325 m** median, time model (D-086). The stand-still gap is 2.075 m; 1.625 m at the next feed | 1.53 m (next feed) | no |
| Falls (worse of court and move drill, D-086) | <= 1 % | **3.28 %** court, 0.07 % move drill | 10.3 % | no |
| Style | <= 3.86 | **4.017** | 3.88 | no |
| No Stage 5B family > 5 points below h4-25b | >= -5 pts | backspin **-35**, fast **-6.8**, reach_deep **-9.5**; the other 11 within, most above (reach_backhand +8.2) | — | no |

**1 of 7 gate items is met** (move-to-spot arrival). Move-drill falls also meet the 1 % line, but court falls do not.

### Failing cells (pooled over 4 seeds, Wilson 95 % intervals)

| Cell | Legal | 95 % CI | Feeds |
|---|---:|---|---:|
| volley_forehand@mid / @front | 0.0 % / 0.0 % | <= 0.4 % | 1,941 / 958 |
| volley_backhand@mid / @front | 0.0 % / 0.0 % | <= 0.4 % | 1,984 / 948 |
| reach_deep@front / @mid / @back | 15.4 / 26.9 / 63.5 % | [13.2, 17.9] / [24.9, 29.1] / [60.5, 66.5] | 898 / 1,675 / 960 |
| lob@front / @mid | 36.8 / 51.4 % | [33.5, 40.2] / [48.9, 53.9] | 780 / 1,541 |
| backspin@back | 53.7 % | [50.7, 56.7] | 1,076 |
| cross_backhand@front / @back / @mid | 58.6 / 67.2 / 68.6 % | [55.1, 61.9] / [64.2, 70.1] / [66.2, 70.9] | 799 / 970 / 1,504 |
| drop@mid | 69.7 % | [67.4, 72.0] | 1,556 |

Every Stage 4 family, the reach forehand/backhand families and cross_forehand reach 75 % in all three zones. The intervals are narrow (pooled counts), so none of the failures is close to noise.

## North-star: rallies (reported, not gated; D-086)

The rally evaluation uses court-anchored feeds: every shot lands at a fixed court place, so the robot has to get there, and it counts consecutive legal returns. Below, 90 s episodes, seed 4200860.

| Executor | Legal on court-anchored feeds | P(rally >= 10) [95 % CI] | Mean length of ended rallies |
|---|---:|---|---:|
| run 18 (two-skill merge) | 50.7 % | 0.35 % [0.27, 0.45] | 0.94 |
| **run 22 (candidate)** | **61.8 %** | **1.63 %** [1.43, 1.86] | **1.44** |

On the final seed (60 s) the candidate reaches 1.52 % [1.29, 1.80], with a mean of 1.32. Earlier rally numbers (all 0) were capped: an 8 s training-length episode fits only 7-8 feeds. The evaluation was fixed in D-090. The robot returns 79 % of balls aimed at it but only 62 % of balls aimed at the court, so getting to the ball is the main remaining gap for live play.

## What Stage 5C established

1. **Footwork through the latent controller is solved by kickstarting.**
   - **Data and walkers did not fix it.** Five walker runs (three controllers, two barriers) never stepped left or back, and those runs were confounded by a world-fixed paddle target (D-086). Mirrored LAFAN1 (D-077) and walking-teacher footwork clips (D-081) did not fix it either.
   - **Distillation did.** Distilling the flat walking teacher through latent-07 at lambda 3 did (D-082): the decoder already reproduces 93 % of its leg actions there.
   - **The residual made it trainable.** A residual executor around a frozen two-skill policy then let PPO improve without forgetting (D-086): arrival 94.8-99.9 % in runs 19 and 22.
2. **The latent barrier at lambda 1 reaches almost nothing.** At lambda 1, under 3 % of steps of the controller's own clips fit inside it (32 dims, each within one prior sigma); at lambda 3, 63-83 % do (D-080).
3. **Plain PPO started from a distilled executor collapses into falls** (runs 13, 14 and 20). PPO as a residual around a frozen executor does not (runs 19, 22).
4. **Court-wide hitting:** from 52 % to 79-81 % (runs 17, 18, 19, 22), with Stage 4 families at 91-99 % in every zone.
5. **Not reached:**
   - Volleys: three approaches, never a legal return.
   - Lobs, reach_deep, backspin and cross_backhand cells.
   - Recovery: the robot closes only about a third of the gap in the time allowed.
   - Court falls: about 3-4 % since run 2.
   - Style: 4.0-4.16 for every PPO-trained hitter; the distilled footwork alone scored 3.585.

## Rule deviations (all recorded in DECISIONS.md)

- **Run 4 was never run.** D-078's re-aimed volley feeds entered training from run 12 without a run of their own (D-086).
- **Runs that changed more than one thing:** 6 (teacher and data), 12 (lambda, method, teacher, episode mix, beta phase), 15 (loss, teacher, start), 18 (teacher and start) (D-086).
- **Run endpoints moved after launch:**
  - Run 2's endpoint was refixed during the run (the 3,000-iteration limit could not fit the 2 h cap; D-075 note).
  - Runs 11 (WSL shut down), 19 and 22 (2 h cap) ended at the last checkpoint before the cap.
- **Runs stopped early:** 13 and 20b, both counted.
- **Evaluation definitions changed mid-loop, all user-approved under D-086:**
  - Falls now take the worse of court and move drill.
  - Recovery is now scored by the time model, alongside the original next-feed score.
  - Cells with fewer than 30 episodes count as unresolved.
  - The final evaluation pools 4 seeds.
  - Earlier runs were re-scored where it mattered: runs 15 and 17 on falls. The original recovery number is reported next to the new one.
- **The style kill rule for run 19 was written at 3.86 although its base was already at 4.01.** It triggered and was not reinterpreted (D-087).
- **The rally evaluation was capped by episode length until D-090.**

## Videos (close cameras, candidate run 22, dev seed 4200910; `mjlab/artifacts/videos/h5c/`)

- `s5c-22-side.mp4`, `s5c-22-behind.mp4`: court-wide drill, every family, random court-wide recovery spots, no hint.
- `s5c-22-kitchen.mp4`: start at the kitchen line (x = -2.6); short, reach, cross, volley and lob feeds.
- `s5c-22-move.mp4`: move-to-spot drill, spots 0.5-3 m in every direction.
- `s5c-22-rally.mp4`: a 60 s sequence across the court with court-anchored feeds (wide side camera).

## Recommended next steps (from the D-086 review round)

1. **Rally drill as training,** not only evaluation: court-anchored feeds from a scripted far-court opponent, long episodes, P(rally >= 10) as the main metric. Run 22 (half court-anchored, 8 s episodes) already moved it from 0.35 % to 1.6 %.
2. **Style:** anchor the residual to a reference with style under 3.86, e.g. the distilled footwork (3.585). Or tune the residual penalty against style at each checkpoint.
3. **Volleys:** a ready position at the kitchen line with the paddle up, and a dedicated volley motion source. Likely a goal-conditioned (MaskedMimic-style) controller that takes hand and root targets directly. Every latent-space route here produced zero legal volleys.
4. **Falls and backspin@back:** both regressed under PPO. Consider a backspin family teacher (h4-25b, lambda 1) through `kickstart_h4.py --family-teacher ...@1`.
