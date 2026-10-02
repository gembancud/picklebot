# Stage 4 run A (`lateral-a01`): FAILED, reward-incentive loophole

Date: 2026-10-03. Task `Picklebot-Return-Lateral-G1` (easy_forehand + wide_forehand + backhand, equal weights), grip v2 with rounded-corner contact. Warm-started (rsl_rl resume) from `return-stand-02/model_700`. 4096 envs, seed 1, 7,000 s cap: iterations 700 → 3,366 (~262M steps). **Fixed endpoint `model_3300`.**

## Result (dev seed 4,200,020; 1024 envs × 15 s; per-family legal return)
| Family | `model_3300` (endpoint) | `model_1700` (**diagnostic only**, not selectable) |
|---|---:|---:|
| easy_forehand | **0.2 %** | 100 % |
| wide_forehand | **0 %** | 99.2 % |
| backhand | **0 %** | 100 % |
| deep / short / high | 0.4 % / 2.1 % / 0 % | 100 % / 0 % / 0 % |
| low / fast | 3.9 % / 0 % | 65.0 % / 20.7 % |
| topspin / backspin | 0 % / 27.1 % | 100 % / 94.2 % |
| Contact on trained families | 100 % | 100 % |
| Net clearance at crossing | **4.16 m** | 1.21 m |
| Rally endings | 739 out, 372 lost, 255 wrong side | mostly second bounce/wrong side on untrained families |

Training log: legal-return reward peaked at **1.52 per episode** around iteration 1,750, then fell to 0.14 by 3,000. Episodes grew to 148 of the 150-step maximum, rally-end terminations fell from ~35 to 4 per log window, and total reward kept rising.

## Diagnosis
The rally-end condition (`drill_over`: legal return or any fault) was a **true termination**, while every surviving step earns the standing/balance rewards. A legal return therefore *forfeited* the remaining episode's balance reward, worth more than the +5 return bonus. The policy learned to hit **sky-high lobs** that are still in the air when the 3 s episode times out: no fault, no early end, maximum balance reward.

## Fix (for the rerun `lateral-a02`)
- `drill_over` becomes a **time-out** (`time_out=True`): PPO bootstraps the value at the reset, so ending a rally costs nothing. Falls remain a true termination.
- Episode length 3 → 4 s, so high returns can land inside the episode.
- Regression test `test_rally_end_is_a_time_out_not_a_termination`.

## What run A did show (diagnostic, not a claim)
Mid-run, the same recipe learned all three lateral families to ~100 %, including backhands (0 % for the Stage 2 policy), plus large transfer to deep, low and backspin. The fixed-endpoint rule still applies: `model_1700` is neither promoted nor used as a parent. The rerun starts again from `model_700`.
