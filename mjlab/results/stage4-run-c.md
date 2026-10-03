# Stage 4 run C (`aim-all-c01`): all ten feed families with targets

Date: 2026-10-03. Task `Picklebot-Aim-All-G1`: all ten families at equal weight, feeding machine, targets A/B sampled 50/50 per feed, placement bonus on legal landings. Warm-started from `aim-b01/model_5300` (same observation layout). 4096 envs, train seed 1, 7,000 s cap: iterations 5,300 → 7,654. **Fixed endpoint `model_7600`.**

Training stayed healthy throughout (checked every 250 iterations): value loss 0.12–0.14, action std 0.71–0.73, falls 0. Legal-return reward rose from 1.35 to about 1.48 per episode, and placement from 0.25 to about 0.34.

## Evaluation (dev seed 4,200,060; 2048 envs × 16 s; all families; paired targets A and B)
About 1,300–1,450 feeds per family per condition. Legal return is pooled over both targets (~2.7k feeds per family), with the per-condition Wilson intervals in brackets. The parent `aim-b01/model_5300` was scored on the same seed and task.

| Family | Legal `model_7600` (A / B) | Parent | Contact (A) | A/B gain [95 % CI] | Hit A / hit B |
|---|---:|---:|---:|---:|---:|
| easy_forehand | **85.1 %** (84.5 [82.5, 86.2] / 85.7 [83.7, 87.5]) | 80.7 % | 88.2 % | +0.537 [0.520, 0.554] | 74 % / 33 % |
| wide_forehand | **84.6 %** (84.3 [82.3, 86.1] / 84.9 [82.9, 86.7]) | 78.6 % | 88.1 % | +0.681 [0.664, 0.699] | 75 % / 61 % |
| backhand | **84.4 %** (85.4 [83.4, 87.1] / 83.3 [81.2, 85.2]) | 81.1 % | 89.0 % | +0.363 [0.347, 0.380] | 14 % / 59 % |
| deep | 84.6 % | 79.6 % | 89.7 % | +0.501 [0.483, 0.519] | 64 % / 37 % |
| short | 75.8 % | 42.7 % | 87.2 % | +0.439 [0.421, 0.456] | 58 % / 30 % |
| high | **69.2 %** (69.6 [67.1, 72.0] / 68.8 [66.3, 71.3]) | 1.3 % | 85.8 % | +0.446 [0.428, 0.464] | 60 % / 30 % |
| low | 86.8 % | 62.7 % | 88.4 % | +0.795 [0.780, 0.810] | 85 % / 74 % |
| fast | 88.5 % | 62.7 % | 89.1 % | +0.819 [0.804, 0.833] | 83 % / 80 % |
| topspin | 85.3 % | 77.0 % | 87.8 % | +0.667 [0.650, 0.684] | 79 % / 54 % |
| backspin | 73.9 % | 32.1 % | 88.9 % | +0.096 [0.085, 0.107] | 16 % / 3 % |
| **all** | **81.8 %** | 60.1 % | 89 % | **+0.533 [0.528, 0.539]** (parent +0.347) | |

- **Falls:** 0 per robot episode.
- **Rally endings** (target A): 938 LOST, i.e. balls never touched, then 223 wrong side, 58 second bounce, 46 out. Contact (86–90 % in every family) is the binding limit. Given contact, about 96 % of lateral-family touches are legal.

## Observations
- **Big gains on the families new to training:** high 1 → 69 %, short 43 → 76 %, backspin 32 → 74 %, low and fast 63 → 87–89 %. Every family improved over the parent.
- **The lateral families score lower in the all-family mix than in run B's lateral-only evaluation** (90 % for run B on its own task). The parent drops the same way here (90 → 81 %), so this is the harder feed context (the robot's state after difficult feeds), not forgetting. On the same feeds, run C beats its parent on easy by +4.4 points.
- **Aiming is uneven.** The A/B gain is above 0 for every family, but there are strong side biases:
  - backhand hits A only 14 % of the time vs 59 % for B;
  - easy and high favour A;
  - backspin barely aims (gain 0.10).

## Against the Stage 4 gate (for the gate step)
- **Lateral ≥ 85 %:** easy 85.1 %, wide 84.6 %, backhand 84.4 %. At the threshold, with intervals spanning it; two of three point estimates are just below.
- **Depth/height/speed/spin ≥ 70 %:** high is 69.2 % [interval spans 70]; all the others pass (short 75.8 %, backspin 73.9 %, deep, low, fast and topspin ≥ 84 %).
- **A/B gain interval above 0:** passes overall and per family.
- **Easy retention within 5 points:** passes against the parent on the same feeds (+4.4).

Files: `stage4-runc-{endpoint,parent}-{A,B}.json`, `stage4-runc-gain.json`, `stage4-runc-parent-gain.json`.
