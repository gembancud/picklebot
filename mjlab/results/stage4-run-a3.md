# Stage 4 run A3 (`lateral-a03`): lateral widening with the feeding machine — PASSED its step

Date: 2026-10-03. Task `Picklebot-Return-Lateral-G1` (easy_forehand + wide_forehand + backhand, equal weights), grip v2 with rounded-corner contact, **feeding machine** (next feed 0.5 s after each rally; 8 s episodes end only on fall/time). Warm-started from `return-stand-02/model_700`. 4096 envs, seed 1, 7,000 s cap: iterations 700 → 3,078 (~234M steps). **Fixed endpoint `model_3000`.** Training stayed healthy throughout (value loss 0.07–0.12, action std 0.69 → 0.57, falls → 0; monitored live).

## Dev evaluation (1024 envs × 24 s per seed, all 10 families sampled uniformly; rates per feed, Wilson 95 %)
| Family | Seed 4,200,030 | Seed 4,200,031 | Contact | Stage 2 `model_700` (v1 robot, single feeds) |
|---|---|---|---|---|
| easy_forehand | **77.6 %** [75.0, 79.9] | **79.4 %** [76.9, 81.7] | 84–86 % | 96.7 % single-feed; **55.7 %** under the feeding machine |
| wide_forehand | **79.3 %** [76.8, 81.5] | **77.9 %** [75.5, 80.2] | 83–84 % | 44.9 % |
| backhand | **79.2 %** [76.8, 81.5] | **79.8 %** [77.3, 82.0] | 85–86 % | **0 %** |
| deep | 79.3 % | 78.8 % | 84–85 % | 76.5 % |
| topspin | 79.7 % | 78.9 % | 85–86 % | 95.5 % |
| backspin | 37.4 % | 38.1 % | 85–87 % | 61.0 % |
| low | 15.7 % | 14.2 % | 68–71 % | 15.0 % |
| fast | 8.3 % | 8.3 % | 53–54 % | 2.6 % |
| short | 5.4 % | 4.9 % | 27 % | 0.3 % |
| high | 0 % | 0 % | 0 % | 0 % |

Robot falls: 1 in 6,144 robot episodes. Stroke: paddle 6.44 m/s at contact, net clearance 0.67 m, landing x 4.2 m.

**Retention (easy feed, same feeding-machine environment):** 55.7 % → 77.6–79.4 %, an improvement, not a loss. The single-feed 96.7 % is not comparable: that environment reset the robot before every ball.

## Reading
- New skills: backhand (0 → 79 %) and wide forehand (45 → 79 %), plus recovery between consecutive shots, all in one policy.
- The ceiling is **contact** (~85 %). Given contact, ~93 % of trained-family shots land legally. Misses likely come from feeds arriving during recovery; not yet diagnosed.
- Backspin regressed versus the single-feed v1 baseline (61 → 38 %); it was not in this training mix.
- Untrained families (high, fast, low, short) remain weak; they are run C's job.
- Two dev seeds agree within ~2 points. One training seed (Stage 5 repeats it).
