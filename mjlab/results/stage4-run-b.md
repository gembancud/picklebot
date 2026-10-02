# Stage 4 run B (`aim-b01`): aiming on the lateral families

Date: 2026-10-03. Task `Picklebot-Aim-Lateral-G1` (easy_forehand + wide_forehand + backhand, feeding machine, targets A/B sampled 50/50 per feed, placement bonus on legal landings). Warm-started from the expanded `lateral-a03/model_3000` (`parent-lateral-a03-aim112`, actor 112 / critic 127 inputs, identical actions for any target). 4096 envs, train seed 1, 7,000 s cap: iterations 3,000 → 5,358. **Fixed endpoint `model_5300`** (last saved checkpoint).

Training stayed healthy throughout (monitored every 250 iterations): value loss 0.11–0.16, action std 0.66–0.70, falls ~0. The placement reward per episode rose 0.24 → 0.39, and legal_return held at 1.51–1.60.

## Paired A/B evaluation (dev seed 4,200,050; 1024 envs × 16 s, about 6.7–6.9k feeds per condition)
The same feeds are played twice, once with target A forced and once with B. Assignment gain = ½[(P(in A | A) − P(in A | B)) + (P(in B | B) − P(in B | A))]. All feeds count, and misses count as landing in neither.

| Family | Gain `model_5300` [95 % CI] | Hit A / hit B | Legal (A / B) | Gain parent | Parent legal (A / B) |
|---|---:|---:|---:|---:|---:|
| easy_forehand | **+0.745** [0.732, 0.757] | 77.3 % / 71.6 % | 88.8 % / 91.3 % | +0.000 | 93.1 % / 93.6 % |
| wide_forehand | **+0.769** [0.756, 0.781] | 81.5 % / 72.2 % | 88.5 % / 91.3 % | +0.001 | 91.7 % / 92.1 % |
| backhand | **+0.579** [0.565, 0.594] | 57.5 % / 58.4 % | 88.8 % / 91.7 % | +0.001 | 91.3 % / 91.2 % |
| **all lateral** | **+0.697** [0.690, 0.705] | 72.1 % / 67.4 % | 88.7 % / 91.4 % | −0.001 [−0.009, +0.008] | 92.0 % / 92.3 % |

Crossover is essentially zero: told A, the policy landed in B once in 6,897 feeds; told B, it never landed in A. The parent lands 36 % in A and 2 % in B whatever the target.

## Retention (easy family, same feeds and seed)
- Pooled over both targets: **90.0 % vs the parent's 93.3 %, −3.3 points.** This is within the 5-point limit.
- Worst single condition: target A, 88.8 % vs 93.1 %, **−4.3 points**. Within the limit, but close to it.
- The loss comes from contact (96 % → 89–92 %), not from landing accuracy. Rally endings are almost all `LOST`, i.e. balls never touched: 180 with target A and 247 with B, against about 10 for the parent. Wrong-side and second-bounce faults fell from about 55 to about 7. The policy swings harder (paddle 7.0 vs 6.4 m/s, ball out 12.7 vs 11.6 m/s) and misses more often.

## Untrained families (diagnostic only; dev seed 4,200,051, target A, all 10 families)
Legal return: easy 87.7 %, wide 86.2 %, backhand 86.6 %, deep 85.8 %, topspin 82.6 %, low 69.6 % (was 15 % for `lateral-a03`), fast 67.8 % (was 8 %), backspin 29.9 %, short 22.4 %, **high 0 %** (8 % contact). Falls 0. These families are run C's job, so no claim is made here.

## Notes
- **Per-family landing tallies** (`land_family`) were added to the task term, `stage2_eval.py` and `aim_gain.py` for this step. The A/B pairs were re-run after the change: per-family sums equal the totals in all four conditions.
- **Feed counts differ by a few** (≤ 4 of ~6,900) between identical-seed reruns, from GPU non-determinism; the rates agree to within 0.1 points.
- Files: `stage4-runb-{model_5300,parent}-{A,B}.json`, `stage4-runb-gain.json`, `stage4-runb-parent-gain.json`, `stage4-runb-model_5300-all.json`.

## Verdict
Step complete. Aiming is learned on every lateral family, with each gain's interval far above 0 and legality retained within the limit. Backhand aiming is the weakest (58 % target hits). The contact drop of about 5 points is the main cost; carry it into run C.
