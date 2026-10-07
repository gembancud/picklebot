# Stage 5 gate: NOT MET after S-D3 and follow-up S-D3b (2026-10-07)

Thresholds unchanged. Real balls only, 2048 envs × 16 s, paired A/B, development seeds.

## Runs
| Run | Change | Endpoint | Eval seeds |
|---|---|---|---|
| S-D3 (`stage5-run-sd3.md`) | Drill 3 (reach curriculum, v2 hint, real-ball hint) | `student-drill3-d3/model_5200` | 4,200,230–232 |
| S-D3b (rule 8 follow-up 1) | gentler reach-curriculum start (`REACH_NEAR_V2`) | `2026-10-07_11-51-32_student-drill3-d3b/model_6500` (cap at it. 6,596) | 4,200,240–242 |

**S-D3b curriculum at the end:** reach_forehand 1.0, reach_short 0.6, reach_backhand 0, reach_deep 0. Even the easier near versions of backhand and deep never reached a 70 % legal EMA, although the adaptive sampler gave them a large share of feeds (backhand 12 %, deep 11 %, short 9 %, against a uniform 7 %).

## Per family, no hint (S-D3 → S-D3b)
| Family | Legal | Contact | A/B gain [95 % CI] (S-D3b) |
|---|---|---|---|
| Stage 4 families (10) | 94.0–97.2 → 93.4–97.0 % | 96–98 → 95.8–97.9 % | +0.615 to +0.893, all > 0 |
| reach_forehand | 96.6 → 96.2 % | 96.6 % | +0.847 [0.829, 0.864] |
| reach_backhand | 24.0 → 21.7 % | 35.6 % | −0.001 [−0.007, +0.006] |
| reach_short | 2.0 → 2.3 % | 10.0 % | +0.006 [0.002, 0.009] |
| reach_deep | 1.5 → 1.8 % | 2.1 % | +0.004 [0.001, 0.007] |

With the hint, S-D3b gives reach_backhand 25.2 %, reach_short 7.5 % (contact 27 %) and reach_deep 2.3 %.

- **Falls per robot episode:** 5.7–6.9 % (S-D3: 5.5–7.0 %).
- **Recovery median:** 1.03 m with no hint, 1.08 m with it (unchanged).
- **Retention vs `model_7600`** (fixed start, no hint): 96.2 % vs 97.2 %. Low −6.1 and fast −7.3 are past the 5-point limit; deep −4.9 and backhand −3.9 are close to it.

## Verdict
| Criterion | S-D3b | |
|---|---|---|
| Stage 4 legal ≥ 85 % | 93.4–97.0 % | pass |
| Stage 4 contact ≥ 92 % | 95.8–97.9 % | pass |
| Reach legal ≥ 75 % | forehand 96 %; backhand 22 %, short 2 %, deep 2 % | **fail** |
| A/B gain CI > 0 on every family | backhand includes 0 (short/deep are barely above 0) | **fail** |
| Recovery ≤ 0.5 m | 1.03 m | **fail** |
| Falls ≤ 1 % | 5.7–6.9 % | **fail** |
| Retention within 5 points | low −6.1, fast −7.3 | **fail** |

## Why the loop stops here instead of running follow-up 2
Rule 8 permits a second follow-up, but the evidence says another single-variable change of the same kind will not move the failing items:
- **The curriculum start was not the bottleneck.** S-D3b made the reach starts as easy as the Stage 4 balls the robot already returns at 95 %, and backhand and deep still never promoted.
- **Sampling was not the bottleneck.** The stuck families already received 1.3–1.7× a uniform share of feeds.
- **These balls need a fast, balanced movement the robot does not have.** On deep balls contact is about 2 % (it does not get to the ball). On backhand reach it touches 36 % but returns 22 %, and the videos show it lunging, tipping back and flailing. Falls are about 6 %, and the recovery miss is 1 m (it does not get back to its spot). The S-D2c video review (`stage5-sd2c-videos.md`) found the same: no forward steps, leaning back, no balanced crossover.

That is a movement-quality problem, which the plan already assigns to Stage 5B (human motion priors, D-044). Stage 5B needs downloads the user must approve (rule 10).

## Options for the user
1. **Recommended: approve the Stage 5B downloads.**
   - Tennis-MoCap ~209 MB, CC BY-SA 3.0;
   - LAFAN1 G1 retargets ~90 MB, non-commercial;
   - GMR ~276 MB + dependencies, MIT.

   Accept S-D3b/S-D3 as the provisional Stage 5 student, with the reach-backhand/short/deep, falls, recovery and low/fast retention deviations documented. Then train the motion-prior footwork/stroke and re-check the unchanged Stage 5 gate after Stage 5B.
2. **Run rule-8 follow-up 2 anyway.** One variable, for example a dedicated reach-specialist hitting teacher distilled in, or more time per ball. Expected gain is small given the above.
3. **Revisit the reach families' definition.** Some reach balls may be physically out of range for this body inside the flight time. A reachability audit would check that; it would be a new decision and would not loosen any threshold silently.
