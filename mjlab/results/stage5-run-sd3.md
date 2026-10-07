# Stage 5 Drill 3 run S-D3 (`student-drill3-d3`): real balls with the reach curriculum

Date: 2026-10-07. Task `Picklebot-Student-Drill3-G1`:
- 60 % real hitting over the Stage 4 + reach families (adaptive family mix; reach curriculum from the near versions);
- v2 stance hint until contact;
- 15 % move-to-spot, 25 % ghost swings;
- blow-up guard, lost margin 2.5 m.

Training: RegPPO toward `student-big-03/model_1500`. Warm-started from `student-swing-d2c/model_3900`, 3,900 → 5,2xx at the cap. **Fixed endpoint `model_5200`.**

## Training
- **Curriculum scales by iteration 4,000:** reach_forehand 0.6 (1.0 by 4,250), reach_short 0.5 (then flat to the end); reach_backhand and reach_deep never left 0, so their near versions were not mastered.
- **Health:** legal-return reward 0.53–0.60, falls 1.3 → 2.7, action std 0.71 → 0.81.

## Stage 5 gate evaluation (real balls only, 2048 envs × 16 s, paired A/B)
Seeds: hint on 4,200,230; hint off 4,200,231; retention 4,200,232.

| Family | Legal, hint on | Legal, hint off | Contact (off) | A/B gain (off) [95 % CI] |
|---|---:|---:|---:|---:|
| easy / wide / backhand | 95.8 / 94.9 / 93.0 % | 96.6 / 96.9 / 94.0 % | 96–98 % | +0.71 / +0.92 / +0.75 |
| deep / short / high | 95.5 / 96.9 / 95.4 % | 95.4 / 96.8 / 96.2 % | 97–98 % | +0.75 / +0.81 / +0.80 |
| low / fast / topspin / backspin | 95.2 / 95.1 / 95.7 / 94.9 % | 96.6 / 96.3 / 97.2 / 94.2 % | 97–98 % | +0.90 / +0.88 / +0.85 / +0.56 |
| **reach_forehand** | 94.7 % | **96.6 %** | 96.8 % | +0.87 [0.85, 0.88] |
| **reach_backhand** | 23.6 % | 24.0 % | 36.8 % | −0.002 [−0.010, +0.006] |
| **reach_short** | 5.6 % | 2.0 % | 9.0 % (28 % with hint) | +0.003 |
| **reach_deep** | 1.9 % | 1.5 % | 1.9 % | +0.003 |

- **Overall A/B gain:** +0.631 [0.625, 0.637] without the hint, +0.612 with it.
- **Falls per robot episode:** 5.5–6.2 % (hint off), 5.6–7.0 % (on).
- **Recovery error (median):** 1.03 m (off) / 1.08 m (on).
- **Retention vs `model_7600`** (fixed start, no hint, same feeds): 96.4 % vs 97.6 %.
  - Within 5 points: easy, wide, backhand −3.9, deep −4.9, short, high, topspin, backspin.
  - Outside: **low −6.3, fast −6.2**.

**The hint on real balls** slightly lowers the Stage 4 families (about −1 point) and helps reach_short contact (9 → 28 %), but not its legality.

## Against the Stage 5 gate: NOT MET
| Criterion | Result | Verdict |
|---|---|---|
| Legal ≥ 85 % on every Stage 4 family, random starts | 94.0–97.2 % | pass |
| Contact ≥ 92 % on Stage 4 families | 96.4–98.1 % | pass |
| Legal ≥ 75 % on every reach family at full range | forehand 96.6 %; backhand 24.0 %, short 2.0 %, deep 1.5 % | **fail** |
| A/B gain interval > 0 on every family | reach backhand and deep include 0 | **fail** |
| Median recovery ≤ 0.5 m | 1.03 m | **fail** |
| Falls ≤ 1 % per robot episode | 5.5–6.2 % | **fail** |
| Retention within 5 points | low −6.3, fast −6.2 | **fail** (2 families) |

## Progress against earlier Stage 5 runs (no hint)
| | F2 | S-D3 |
|---|---:|---:|
| Stage 4 family legality | 65.8–84.6 % | **94.0–97.2 %** |
| Stage 4 contact | 84–88 % | **96–98 %** |
| reach_forehand legality | 74 % | **97 %** |
| reach_backhand legality | 0 % | **24 %** |

The robot now beats every Stage 4 legality and contact bar from random starts (corrected metric) and handles reach_forehand. Left, short and deep reach, falls, recovery, and low/fast fixed-start retention remain.

## Follow-up S-D3b (allowed by the Stage 5 gate text: "D3 plus one follow-up"), decided before launch
**One change: a gentler start for the curriculum.** The near versions begin where the robot already succeeds (`REACH_NEAR_V2`, cfg `reach_near_set="v2"`):
- reach_backhand lateral 0.55–0.8 m, overlapping the backhand family;
- reach_short bounce aimed −4.2..−3.9 m (the short family);
- reach_deep bounce aimed −5.4..−5.1 m (just past the deep family);
- reach_forehand unchanged.

Promotion rules are unchanged (70 % over ≥ 300 feeds, +0.1 per step). Warm-started from `student-drill3-d3/model_5200`; scales restart at 0, and reach_forehand is expected to re-promote quickly. **If the Stage 5 gate is still missed, the loop stops for the user.**
