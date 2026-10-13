# Stage 5B H4: the Drill 3 executor over the latent controller (D-050, D-056)

**Task** `Picklebot-Latent-Drill3-G1` (`picklebot_mj/tasks/__init__.py`):
- **Base:** S-D3b's Drill 3 task (gentle reach curriculum; 60 % real balls over all 14 families with an adaptive mix, 15 % move-to-spot, 25 % ghost swings). This is the task of the S-D3-style-c baseline, without its style reward.
- **Action:** H3's latent action space, a = [a_lat 32, a_wrist 3] through the frozen latent-07/latent_10651 (λ 1.0, wrist residual ±0.3 rad).
- **Rewards:**
  - removed: `pose`, `ready_stance`;
  - added: `latent_l2` −0.01;
  - `action_rate_l2` set to H3's −0.01. The inherited −0.1 on the raw latent action gave −5.5 per episode in the smoke run and swamped the task terms.
- **Network:** the student's 1024-512-256 actor and critic, plain PPO (mjlab G1 defaults).
- **Speed:** about 5.2 s per iteration at 4096 envs, about 1,350 iterations per 2 h run.

**Evaluation** (`scripts/h4_eval.sh`, `scripts/h4_summary.py`): the Stage 5 gate protocol on each fixed endpoint, on fresh dev seeds:
- 2048 envs × 16 s;
- every family, target A/B, with and without the hint;
- retention vs model_7600;
- style score.

**Main metric** (D-056 plateau rule): the no-hint legal-return rate pooled over all 14 families. Baseline S-D3-style-c: 78.7 %, style 4.84.

**Evaluation scripts now reset before the first step** (`stage2_eval.py`, `style_score.py`, as in reach_eval.py). Check on S-D3-style-c (dev seed 4200418, no hint, target A):
- legal 78.5 % → 78.9 %;
- robot falls 4.3 → 4.8 % per episode;
- recovery 0.975 m in both;
- every family within noise.

So the earlier Stage 5 numbers stand. The final gate re-evaluates S-D3-style-c with the same script and seeds as the H4 candidate.

## Runs (budget: 15 under D-056)
| # | Run | Change (written before launch) | From | Endpoint | Main metric | Style |
|---|---|---|---|---|---|---|
| 1 | h4-01 | the plan as written: fresh PPO, settings above | scratch | model_1300 (cap) | **0.0 %** | **2.74** |
| 2 | h4-02 | + one-shot return shaping at first contact (D-057), task `Picklebot-Latent-Drill3-Shaped-G1` | h4-01/model_1300 | model_2700 (cap) | 0.0 % | 2.62 |
| 3 | h4-03 | PPO entropy coefficient 0.01 -> 0.001 (`Picklebot-Latent-Drill3-Shaped-LowEnt-G1`) | h4-02/model_2700 | model_4100 (cap) | 0.2 % | 2.71 |
| 4 | h4-04 | more training (same task and settings) | h4-03/model_4100 | model_5500 (cap) | **3.5 %** | 2.88 |
| 5 | h4-05 | stance hint on half the real-ball feeds (D-058; `Picklebot-Latent-Drill3-HalfHint-G1`) | h4-04/model_5500 | model_6900 (cap) | **15.7 %** | 2.78 |
| 6 | h4-06 | stance hint on 20 % of the real-ball feeds (`Picklebot-Latent-Drill3-FewHint-G1`) | h4-05/model_6900 | model_8300 (cap) | **46.2 %** | 2.81 |

## Run 1: h4-01 (dev seeds 4200420-423; `stage5b-h4-h4-01-*.json`)
- **Every family has 0 % legal returns.** Contact is 18 %, the paddle moves at 0.8 m/s at contact, contact height is 0.57 m, and no ball crosses the net. Rally endings: second bounce 7,610, out 2,961, wrong side 2,003.
- **Style 2.74** (target <= 3.86; S-D3-style-c 4.84; human floor 0.94). **Robot falls 0.5 %** per episode (S-D3-style-c 4.8 %). **Recovery median 0.58 m** (S-D3-style-c 0.98 m).
- **Training curve:** no falls after iteration 400 and paddle contact rising slowly (0.04 -> 0.15 per episode), but legal returns stay at 0. Action std grew from 1.0 to 1.26.
- **Reading:** the decoder makes the motion human-like and stable. The policy has not found a swing, and the rewards give nothing between touching the ball and a legal return.

## Distillation from the flat student: rejected (D-057)
- `scripts/distill_h4.py` is DAgger through the frozen decoder, teacher S-D3-style-c (tests in `tests/test_distill_h4.py`). In the smoke run (60 iterations, 1024 envs) the imitation error rose from 0.30 to about 2.0 and stayed there, and robot episode endings grew.
- **Expressiveness floor** (`scripts/latent_reach_floor.py`, `stage5b-h4-latent-floor.json`): per-state best fits on the teacher's own states, MSE in the teacher's action units.

| lambda | legs | waist | left arm | right arm | right wrist | all | latent saturated |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.103 | 0.092 | 0.187 | 0.372 | 0.355 | 0.185 | 70 % |
| 2 | 0.068 | 0.061 | 0.149 | 0.277 | 0.301 | 0.140 | 54 % |
| 3 | 0.050 | 0.046 | 0.125 | 0.217 | 0.258 | 0.112 | 41 % |
| *teacher action variance* | 0.356 | 0.186 | 0.624 | 1.193 | 16.4 | 2.18 | |

The decoder gets close only with most latent commands pinned at the barrier, i.e. at the edge of the human-motion space. The flat student's wrist variance (16) shows it slams the wrist between limits.

## Run 2: h4-02 (dev seeds 4200425-428; `stage5b-h4-h4-02-*.json`)
- **Legal returns still 0 %, no net crossings.** But the swing is forming:
  - paddle speed at contact 0.8 -> 1.43 m/s;
  - outgoing ball speed 2.6 -> 3.5 m/s;
  - contact 17 %, height 0.59 m.
- **Style 2.62, robot falls 0.34 %, recovery median 0.375 m** (the recovery threshold of <= 0.5 m is met).
- **Training:** return shaping per episode rose from 0.003 to 0.040, fastest at the end. Contact stayed flat at about 0.17. Action std kept rising, 1.26 -> 1.30.
- **Next change** (decided before launch): PPO entropy coefficient 0.01 -> 0.001. The latent passes through tanh, so extra noise costs almost nothing while the entropy bonus keeps paying for it (entropy loss about 58 over 35 dims). Training rollouts drown a coordinated swing in noise.

## Run 3: h4-03 (dev seeds 4200430-433; `stage5b-h4-h4-03-*.json`)
- **Main metric 0.2 %** (no hint); 1.9 % with the stance hint (target A).
  - Per family, no hint: wide forehand 1.5 %, topspin 0.6 %, deep 0.5 %, the rest 0-0.2 %.
- **The swing now exists:**
  - paddle speed at contact 2.93 m/s (from 1.43);
  - outgoing ball 5.4 m/s (from 3.5);
  - contact 22 %;
  - 40 net crossings (from 0).
- **Style 2.71, robot falls 0.8 %, recovery 0.425 m** (still within <= 1 % and <= 0.5 m).
- **Training:** action std 1.29 -> 0.41. Return shaping per episode 0.04 -> 0.18. The legal-return reward first appeared at iteration 3,900 and was still rising at the cap (0 -> 0.026 -> 0.053 per episode over the last 300 iterations).
- **Plateau count** (D-056): runs 2 and 3 both improved the main metric by < 1 point. Run 4 must reach >= 1.2 %, or climbing stops.
- **Next** (decided before launch): more training, no change, from h4-03/model_4100. The curve was still accelerating at the cap.

## Run 4: h4-04 (dev seeds 4200435-438; `stage5b-h4-h4-04-*.json`)
- **Main metric 3.5 %** (+3.3 points; the plateau count resets).

  | | Without the hint (gate) | With the hint (target A) |
  |---|---:|---:|
  | Contact | 21 % | 59 % |
  | Legal returns | 3.5 % | **40.9 %** |

  Per family, no hint: topspin 9.1 %, low 8.1 %, fast 7.4 %, deep 6.3 %, backspin 5.5 %, easy forehand 4.0 %, wide forehand 3.4 %, short 2.6 %, high 1.1 %. Backhand and every reach family are 0-0.2 %.
- **The swing is real:** paddle speed at contact 4.4 m/s, ball out 7.2 m/s, 684 net crossings.
- **Style 2.88, robot falls 0.8 %, recovery 0.375 m** (all within their targets).
- **Training:** the legal-return reward rose 0.05 -> 0.45 per episode and levelled off over the last 500 iterations. Contact per episode drifted 0.20 -> 0.16.
- **Reading:** the executor can return balls when told where to stand. It has not learned to find the interception point from the ball, because every real-ball training feed showed the hint.
- **Next** (decided before launch, D-058): the stance hint on half the real-ball feeds, from h4-04/model_5500.

## Run 5: h4-05 (dev seeds 4200440-443; `stage5b-h4-h4-05-*.json`)
- **Main metric 15.7 %** (+12.2 points). No-hint contact 44 % (from 21 %).
  - Per family, no hint: low 35.3, topspin 34.1, deep 31.5, fast 31.5, backspin 26.3, easy forehand 23.9, wide forehand 17.6, short 12.4, high 6.6 %.
  - Backhand 0 %, reach forehand 1.0 %, the other reach families 0 %.
- **With the hint on every feed: 43.0 %** (run 4: 40.9 %). Hiding half the hints in training did not cost hinted play.
  - Evaluation fix: `stage2_eval.py` now sets `hit_hint_prob` = 1 for with-hint evaluations. The first with-hint pass of this run had used the task's 0.5 and was re-run (same seeds).
- **Paddle speed** at contact 4.7 m/s; 2,482 net crossings.
- **Style 2.78, robot falls 0.2 %.** Recovery median 0.625 m: worse than run 4 (0.375 m) and now outside <= 0.5 m.
- **Training:** legal-return reward per episode dipped 0.45 -> 0.32 (half the feeds lost the hint) and stayed flat.
- **Next** (decided before launch): stance hint on 20 % of real-ball feeds, from h4-05/model_6900.
- **Still open:** backhand and the reach families are at about 0 %, and recovery regressed.

## Run 6: h4-06 (dev seeds 4200445-448; `stage5b-h4-h4-06-*.json`)
- **Main metric 46.2 %** (+30.5 points). No-hint contact 60 %. With the hint on every feed: 48.0 %, so the hint now barely matters.
- **Per family, no hint:**

  | Families | Legal returns |
  |---|---|
  | topspin, short, low | 81.0, 80.6, 79.3 % |
  | backspin, deep, fast, easy forehand, wide forehand, high | 73.2, 73.1, 71.8, 69.4, 68.8, 65.9 % |
  | reach forehand | 7.0 % |
  | **backhand, reach backhand, reach short, reach deep** | **0 %** |

  A/B gain CI is above 0 for short, low, topspin and backspin.
- **Style 2.81, robot falls 0.2 %.** Recovery median 0.775 m (regressing: 0.375 -> 0.625 -> 0.775 m over runs 4-6).
- **Backhand: contact 0 % even with the hint**, although it already gets the largest adaptive feed share (12.4 %). The executor does not get the paddle to balls on its left at all. This is a capability gap, not ball reading.
- **Video check** (`artifacts/videos/h4/h4-05-backhand-behind.mp4`, 4 envs, backhand feeds, hint on): the robot stands in its ready pose, paddle on its right, while each ball passes on its left. No step and no swing.
- **Next** (decided before launch, D-059): the stance hint puts every ball on the forehand side (run around the backhand), from h4-06/model_8300.

| # | Run | Change (written before launch) | From | Endpoint | Main metric | Style |
|---|---|---|---|---|---|---|
| 7 | h4-07 | stance hint on the forehand side for every ball (D-059; `Picklebot-Latent-Drill3-FhHint-G1`) | h4-06/model_8300 | model_9700 (cap) | **50.4 %** | 2.81 |
| 8 | h4-08 | + spot-progress reward (D-060; `Picklebot-Latent-Drill3-Progress-G1`) | h4-07/model_9700 | model_11100 (cap) | 50.5 % | 2.85 |
| 9 | h4-09 | episode mix: move 0.15 -> 0.35, ghost swing 0.25 -> 0.05 (D-061; `Picklebot-Latent-Drill3-MoveMix-G1`) | h4-08/model_11100 | model_12400 (cap) | **54.1 %** | 2.87 |
| 10 | h4-10 | + stance_progress footwork shaping (D-062; `Picklebot-Latent-Drill3-Footwork-G1`) | h4-09/model_12400 | model_13800 (cap) | **58.6 %** | 2.90 |
| 11 | h4-11 | + fall penalty -50 (D-063; `Picklebot-Latent-Drill3-FallPen-G1`) | h4-10/model_13800 | model_14900 (cap; about 1,150 iterations, the GPU was shared with a video render) | 58.1 % | 2.85 |

## Run 7: h4-07 (dev seeds 4200450-453; `stage5b-h4-h4-07-*.json`)
- **Main metric 50.4 %** (+4.2 points).
  - Forehand-side families, no hint: deep 86.4, topspin 86.1, backspin 82.8, wide forehand 82.0, low 81.4, fast 79.2, easy forehand 73.5, high 70.4, short 64.8 %.
  - A/B gain CI above 0 for wide forehand, deep, low, fast, topspin and backspin.
- **Reach forehand 15.5 %.** Backhand, reach backhand, reach short and reach deep are 0 %, **backhand with 0 % contact even with the forehand-side hint**.
- **Style 2.81, robot falls 0.3 %, recovery 0.825 m** (worse again).
- **Video** (`artifacts/videos/h4/h4-07-backhand-*`): the robot still stands still while backhand balls pass. It does not take the hinted 0.8-1.15 m sidestep.
- **Diagnosis:** `move_arrival` is 0 in every H4 run, so the executor never learned to travel to a commanded spot. For forehand feeds the hinted spot is within about 0.2 m of where it stands, so it can ignore the spot input.
- **Next** (decided before launch, D-060): + spot-progress reward toward the spot input when it is meant to be followed, from h4-07/model_9700.

## Run 8: h4-08 (dev seeds 4200455-458; `stage5b-h4-h4-08-*.json`)
- **Main metric 50.5 %** (+0.1; plateau count 1).
  - Forehand-side families 71-85 %.
  - Reach forehand 25.1 % (from 15.5 %).
  - Backhand, reach backhand, reach short and reach deep 0-0.1 %.
- **Style 2.85, robot falls 0.4 %, recovery 0.775 m.**
- **Training:** spot progress per episode 0.0035 -> 0.02; `move_arrival` still 0.
- **Next** (decided before launch, D-061): episode mix move 0.35 / ghost swing 0.05 / real 0.60, from h4-08/model_11100.

## Run 9: h4-09 (dev seeds 4200460-463; `stage5b-h4-h4-09-*.json`)
- **Main metric 54.1 %** (+3.6; plateau count reset).
  - Stage 4 families, no hint: topspin 87.3, low 85.0, backspin 84.9, wide forehand 83.4, easy forehand 81.9, deep 80.7, short 79.6, fast 76.9, high 74.3 %.
  - **Reach forehand 46.0 %** (from 25.1 %).
  - Reach short 3.6 % and reach deep 1.8 % now pass their bar (base 6.0 / 1.4 %).
  - **Backhand and reach backhand 0 %.**
  - A/B gain CI above 0 on 11 families.
- **Style 2.87. Robot falls 2.3 %** (up from 0.4 %; target <= 1 %). Recovery 0.825 m.
- **Move diagnostic** (`scripts/move_diag.py`, `stage5b-h4-h4-09-move-diag.json`, move episodes only, dev seed 4200464): **0 of 2,990 spots reached within 0.25 m**; median closest approach 1.36 m; drill arrival 0 %. The executor moves when the ball pulls it to the right, but ignores abstract spots and never moves left. Its spot input is already body-relative, so this is exploration, not perception.
- **Next** (decided before launch, D-062): + stance_progress, a privileged footwork-shaping reward toward the forehand-side hitting stance on un-hinted feeds before the hit, from h4-09/model_12400.

## Run 10: h4-10 (dev seeds 4200465-468; `stage5b-h4-h4-10-*.json`)
- **Main metric 58.6 %** (+4.5).
  - Stage 4 families, no hint: topspin 90.2, backspin 89.5, high 88.6, short 87.0, wide forehand 86.4, low 85.9, easy forehand 84.7, deep 79.8, fast 78.9 %.
  - **Reach forehand 64.5 %.** Reach short 7.0 % and reach deep 2.3 % pass their bar.
  - **Backhand 0 % (contact 0.1 %), reach backhand 0 %.**
  - A/B gain CI above 0 on 12 families.
- **Contact** is 95-98 % on the Stage 4 families, so their remaining loss is return quality (out 1,121, wrong side 403).
- **Style 2.90. Robot falls 6.0 %** per robot episode (up from 2.3 %). Recovery 0.825 m.
- **Video** (`artifacts/videos/h4/h4-10-backhand-*`): still planted while backhand balls pass on its left.
- **Root cause (D-063):** the latent controller rarely steps left or back. The H3 walker reaches a target 0.8 m to its left within 25 cm only 41.8 % of the time (right 95.7 %, forward 99.3 %, back 24.7 %). Fixing this is outside H4's scope and goes to the user.
- **Next** (decided before launch, D-063): + fall penalty -50 (the drill task had none), from h4-10/model_13800.

## Run 11: h4-11 (dev seeds 4200485-488; `stage5b-h4-h4-11-*.json`)
- **Main metric 58.1 %** (-0.5 vs run 10).
  - Low 92.5 % (passes its gate bar), topspin 90.9, wide forehand 88.3, backspin 85.4, high 83.0, short 82.6, fast 81.5, deep 77.0, easy forehand 76.1 %.
  - Reach forehand 65.5 %, **reach short 20.4 %**, reach deep 3.3 %. Backhand and reach backhand 0 %.
- **Style 2.85, robot falls 5.4 %** (from 6.0 %; the penalty barely helps, since falls were already rare in stochastic training). Recovery 0.875 m.
- **Climbing stops here (D-064).** Candidate by the main metric: **h4-10/model_13800** (58.6 %).

## D-065/D-066: throughput and the learning-progress curriculum (2026-10-13)
- **Throughput:** 175 -> 15 CUDA syncs per step (behaviour-preserving fixes); training at 12,288 envs, 55.3k steps/s against 19.3k at 4,096 before. Details and the equivalence check are in D-066.
  - **Evaluation noise:** the same checkpoint, seed and code give 57.0-58.4 % pooled no-hint legal from GPU nondeterminism. Borderline plateau calls get a repeat evaluation.
- **Learning-progress curriculum** over (family x 5 levels), from easy ends to full families (D-066).

| # | Run | Change (written before launch) | From | Endpoint | Main metric | Style |
|---|---|---|---|---|---|---|
| 12 | h4-12 | learning-progress feed curriculum (D-066; `Picklebot-Latent-Drill3-LP-G1`); 12,288 envs (standing config). *In effect uniform level sampling (attribution bug)* | h4-10/model_13800 | model_14900 (cap) | **63.8 %** | 2.96 |
| 13 | h4-13 | the curriculum's attribution fix (in-flight feeds kept their unit; D-066 bug) | h4-12/model_14900 | model_16000 (cap) | **74.4 %** | 2.96 |

- **h4-12 caveat (found after the run):** `_refeed` computes a feed for every env and keeps it only where it fires. It restored family, target and the other per-feed fields for the other envs, but not the new curriculum unit. In-flight feeds' outcomes were therefore credited to random units: every unit's success average drifted to the overall rate (backhand's top level showed about 75 %), and level sampling was effectively uniform. So run 12 tested broad uniform level sampling, not the learning-progress curriculum. Fixed, with a regression test that fails on the old code; run 13 repeats the curriculum with correct attribution.

## Run 12: h4-12 (dev seeds 4200495-498; `stage5b-h4-h4-12-*.json`)
- **Main metric 63.8 %** (+5.2 over h4-10). **Backhand 27.6 %**, the first backhand returns of any H4 run.
- **Five families now pass the H4 gate bar** (>= base - 5): easy forehand 95.7, wide forehand 94.7, deep 93.7, short 96.4, topspin 95.6 %. Reach short and reach deep also pass.
- **Fail:**
  - high 88.3, low 84.4, fast 81.1, backspin 70.3 % (low, fast and backspin regressed from run 10 by 1-18 points);
  - reach forehand 66.4 %;
  - reach backhand 0 %.
- **A/B gain:** 0.12-0.55 (run 10: 0.05-0.28; base 0.48-0.90), CI above 0 on 12 families.
- **Style 2.96, robot falls 1.7 %** (from 5.7 %), recovery 0.875 m.
- **Reading:** even uniform sampling over difficulty levels (because of the attribution bug) gave backhand the easy, near-body variants it needed to get a first learning signal. The 3x larger batch (12,288 envs) is confounded with it.
| 14 | h4-14 | more training, same curriculum (backhand top-level success still rising 0.25 -> 0.61 at h4-13's cap) | h4-13/model_16000 | model_17100 (cap) | 74.3 % | 3.01 |
| 15 | h4-15 | curriculum keeps rehearsing mastered units (D-067; `Picklebot-Latent-Drill3-LP-Rehearse-G1`) | h4-14/model_17100 | | | |

## Run 13: h4-13, the working learning-progress curriculum (dev seeds 4200500-503; `stage5b-h4-h4-13-*.json`)
- **Main metric 74.4 %** (+10.7; S-D3-style-c 78.7 %). **Backhand 74.5 %** (from 27.6 %). Reach forehand 84.0 %. **Reach short 36.8 %** (the flat student: 6.0 %).
- **Eight families pass the H4 gate bar:**

  | Family | H4 | S-D3-style-c |
  |---|---:|---:|
  | easy forehand | **97.9 %** | 96.0 % |
  | wide forehand | 95.2 % | 97.5 % |
  | deep | 93.9 % | 96.1 % |
  | short | **98.4 %** | 97.9 % |
  | topspin | **98.4 %** | 97.5 % |
  | backspin | 93.2 % | 96.4 % |
  | reach short | 36.8 % | 6.0 % |
  | reach deep | 4.4 % | 1.4 % |

- **Just missing** (inside the +-1.4-point evaluation noise): high 92.0 % (bar 92.1) and low 92.0 % (bar 92.4).
- **Failing:** fast 85.3 % (-12.3), reach forehand 84.0 % (-12.9), backhand 74.5 % (-22.3), reach backhand 0 %.
- **A/B gain:** 0.06-0.73, CI above 0 on 13 families. The executor now aims.
- **Style 2.96, robot falls 1.3 %, recovery 0.925 m.**
- **Training:** backhand's full-range success rose 0.25 -> 0.61 within the run. Reach backhand sits at the floor share (out of band). Curriculum logs: `Curriculum/*` in the run log.

## Run 14: h4-14 (dev seeds 4200505-508; `stage5b-h4-h4-14-*.json`)
- **Main metric 74.3 %** (-0.2; plateau count 1).
- **Gained:** backhand 83.6 % (from 74.5 %), reach short 57.4 % (from 36.8 %), reach deep 5.2 %.
- **Lost:** easy forehand 87.3 % (from 97.9 %), backspin 87.4 % (from 93.2 %), high 89.3 % (from 92.0 %).
- **Passing the gate bar:** wide forehand, deep, short, topspin, reach short and reach deep.
- **Style 3.01, robot falls 1.3 %, recovery 0.875 m.**
- **Diagnosis (D-067):** the sampler starved mastered units of rehearsal, and they decayed.
- **Video** (`artifacts/videos/h4/h4-13-backhand-*`): backhands are now played with a left sidestep and a cross-body swing on the left.
