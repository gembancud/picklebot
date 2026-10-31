# Panel round 61 brief: the d1 base reads BASE-PASS; review stage 2 before it launches, 2026-10-31

Read first:
- D-192 and D-193 (with its addendum) in docs/DECISIONS.md;
- round 60 in mjlab/results/footwork-review.md;
- results/d1r-summary.txt;
- picklebot_mj/d1_rule.py (the stage-2 functions at the end);
- scripts/diag/d1_stage2.sh (the draft, not launched);
- scripts/rally_check.py (`d1s2_gate`, and `r19_guards` with its new `ref` argument).

## Result: s5c-d1-fw1bS model_32854

The kickstart ran with seed 184: 1,179 iterations (s5c-18: 1,199).
- Final mse_move 0.0258 (s5c-18: 0.0336).
- mse_hit 0.00114.
- At the 30 % check, mse_hit was 0.00161 against a kill line of 0.0017.

**Agility**, dev 4220250, Measure60-L3Base (3-5 m spots, Fast25 box), base only, mean actions. Paired against model_32874:

| | model_32874 | d1 |
|---|---|---|
| falls per 1,000 env-s | 56.8 | 12.0 |
| worst untimed arrival | 0.448 | 0.830 |
| fallen + censored | 0.256 | 0.087 |
| sustained p50, F..FR (m/s) | 1.12 1.08 1.04 1.38 1.53 1.39 1.30 1.20 | 1.58 1.51 1.46 1.69 1.83 2.01 1.68 1.57 |
| peak p50 (m/s) | 1.27-1.78 | 1.87-2.26 |
| first step p50 (s) | 1.38-1.85 | 1.27-1.51 (faster in every sector) |
| settled | 0.00-0.05 | 0.14-0.52 |
| R_LB | 0.623 | 0.801 |

Verdict: **MIXED**. It is valid and the first step is no slower, but R_LB is below 0.85.

**Hitting**, D-086 battery, dev 4220251-4220256:

| | model_32874 | d1 |
|---|---|---|
| main | 0.8013 | 0.8022 |
| passing cells | 43 / 55 | 43 / 55 |
| worst drill5b family | — | reach_short -2.7 points |
| style | 4.030 | 4.028 |
| move-drill falls | 0.0111 | 0.0073 |
| court falls | 0.0356 | 0.0318 |

Verdict: **RETAINS**. PROTOCOL-DRIFT not flagged: the parent's main is 0.8013 against the archived 0.7993.

**Base verdict: BASE-PASS** (MIXED + RETAINS). By D-192, stage 2 follows.

## Stage 2 as drafted (scripts/diag/d1_stage2.sh, not yet launched)

**One change against rally 22b:** the frozen base. `PICKLEBOT_RES_BASE` points to d1 model_32854 instead of RES_BASE model_32874.
- Kept from 22b: the task and its overrides, ScheduledPPO at a constant 1e-4 (no cooldown), KL guard 0.05, std floor 0.1, critic warm-up 0, 12,288 envs.
- Starts from 22b model_30200 and runs 1,200 iterations to a fixed endpoint.
- Training seed 186; smoke seed 187. The smoke asserts base_checkpoint = the d1 base and save_interval 40.

**Reads and kills:**
- **Zero-shot (reported), dev 4220257:** 22b on the d1 base; a pairs read and a Measure60-RallyLamR2 read.
- **Kill at +360:**
  - KILL-UNSTABLE: falls per 1,000 env-s over +341-360 > 2x the reference.
  - KILL-NO-HIT: mean Episode_Reward/legal_return over +341-360 < the reference - 0.05.
  - KILL-NO-ARRIVE: the model_30560 Measure60 read (dev 4220258) fails D-188 validity.
- **Endpoint**, paired against 22b on its own base, same seeds:
  - pairs 4220259;
  - pairs3 4220260 (reported);
  - direction split 4220261;
  - Measure60 4220262;
  - the child's h5f battery 4220267-4220282.
- **Run verdict** (`rally_check d1s2-gate`, vs 22b):
  - P(5+) open >= 22b + 2.0, with the Wilson low above 22b;
  - partner >= 22b - 1.5;
  - feeder >= 22b - 1.0;
  - sides within 3;
  - court falls <= 4 %;
  - D-160 guards with the same slacks against 22b.
- **Agility** (`agility_verdict` vs 22b's composite): AGILE / MIXED / CAP-HELD / INVALID.
- **Final:** D1-PASS (rally pass + AGILE) / ADOPT-AGILITY-NOT-MET (rally pass + MIXED) / PANEL.
- **Reported:** r19-gate, M1 and target against run 14, with an expected FAIL. 22b feeder legal is 0.656 against run 14's 0.823, and 22b fails the D-160 guards.

## A change to a panel line for you to rule on

Round 59 (experiment design) said the +360 training-log kill compares against "22b's last-100-iteration training falls" and "22b's legal_return - 0.05".
- I tested that literal line on **22b's own log**, as if 22b were the child.
  - 22b at +341-360 after its resume: falls 2.35, legal_return 0.602.
  - 22b's last 100 iterations (30100-30199): falls 1.57, legal_return 0.755.
- **The literal line would have killed 22b itself (KILL-NO-HIT).** Episode_Reward/legal_return averages only the episodes that end in the window, and 120-s episodes first end about 250 iterations after a resume.
- **The draft uses 22b's own same-age window instead** (iterations 29341-29360 of its run): kill if falls > 2 x 2.35, or legal_return < 0.602 - 0.05. A replicate of 22b then reads CONTINUE.
- **Rule on it.** Accept, amend (for example, a different window, or reads only), or reject. Never loosen a threshold.

## Questions

1. Does BASE-PASS lead to stage 2 as drafted, or should d1b (move-episode geometry 1-5 m) come first, given R_LB 0.80 (MIXED)? The pre-registered path is stage 2.
2. Correction check of the stage-2 draft:
   - lines, seeds, the one-change claim;
   - constant LR vs 22b's cooldown schedule (22b ran 1e-4 with a 20 % cooldown over 4,000 iterations);
   - critic warm-up 0 (architecture had raised the default in round 59).
3. The kill-reference change above.
4. Anything missing that would make the stage-2 result uninterpretable.

Seeds:
- dev: 4220257-4220262 and 4220267-4220282 to be ledgered at launch;
- training: 186-187;
- next free: dev 4220283, training 189.
