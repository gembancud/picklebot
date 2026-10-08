# Stage 5B style prior in the executor (plan decided before the run, 2026-10-08)

**Starting point:** the provisional Stage 5 student, `2026-10-07_11-51-32_student-drill3-d3b/model_6500` (D-046), and its task, `Picklebot-Student-Drill3-Gentle-G1`.

## Method: AMP-style discriminator reward (`picklebot_mj/style.py`)
The alternative, distilling the tracking teacher, does not fit: that teacher acts on a reference-motion command the executor does not have.
- **Discriminator.** It scores state transitions (φ_t, φ_t+1) as robot-like or human-like.
  - φ is heading-invariant and in the pelvis frame, 80 dims: joint positions and velocities, pelvis height, pelvis linear and angular velocity, projected gravity, hands and feet relative to the pelvis.
  - Expert transitions come from `tennis-v5.npz` (90 clips, 42 min) and `lafan-g1.npz` (24 footwork clips, 93 min), never across a clip boundary.
- **Training (AMP losses).** Least-squares GAN loss with a gradient penalty (weight 5) on expert samples; network 1024-512; Adam 5e-5.
  - It trains on a 200k replay buffer of recent robot transitions: 4 gradient steps every 24 env steps (once per PPO rollout).
  - So PPO and RegPPO are unchanged.
- **Style reward:** r = max(0, 1 − 0.25 (D − 1)²), weight **0.5**. That is on the same scale as the task's main terms (legal return 0.56, pose 0.51, upright 0.82 per episode in S-D3b's logs): the even task/style split of AMP.

## The run: S-D3-style
**One change vs S-D3b:** the style reward. Task `Picklebot-Student-Drill3-Style-G1`.
- **Unchanged:** RegPPO toward `student-big-03/model_1500` with the same settings (train_student.sh defaults), the same drills and mix, seed 1.
- **Warm start:** from S-D3b/model_6500. ≤ 2 h, fixed endpoint at the cap.

## Gate (from the tracker)
1. **The Stage 5 gate is still met to the extent S-D3b met it.** No task regression beyond 5 points against S-D3b on the same evaluation (`s5_gate_eval.sh`, fresh dev seed):
   - Stage 4 families and reach-family legality and contact, falls, recovery;
   - each family compared.
2. **A clearly better style score.**
   - **Measure:** the median nearest-clip pose distance (`scripts/motion/style_score.py`, Stage 5 gate setting, no discriminator involved). Pose features are joint positions, projected gravity, and hands and feet relative to the pelvis, standardised by the clips.
   - **"Clearly better" fixed now:** at least **20 % lower** than S-D3b's on the same seed. The human-to-human floor is reported for scale.
3. **Side-by-side videos** of S-D3b and the style run, same families and seed, sent to the user.

**Rule 8 applies** if the gate is missed.

## Result: S-D3-style (`2026-10-08_18-22-58_student-drill3-style/model_7800`, 1300 iterations to the cap)
- **Style score** (dev seed 4,200,400): nearest-clip pose distance median **4.85**, against S-D3b 4.82 (target ≤ 3.86). **No improvement. FAIL.** The human-to-human floor is 0.94.
- **Task** (`s5_gate_eval.sh`, dev seeds 4,200,260–262, no hint), against S-D3b (4,200,240–242):

| | Stage 4 families legal | reach FH / BH / short / deep legal | Falls | Recovery |
|---|---|---|---|---|
| S-D3b | 93.4–97.0 % | 96 / 22 / 2 / 2 % | 5.7–6.9 % | 1.03 m |
| S-D3-style | 92.6–97.1 % | 96 / 25 / 2 / 1.5 % | 5.2–6.1 % | 1.03 m |

  - No family regresses beyond 5 points against S-D3b.
  - Fixed-start retention against model_7600 shows the S-D3b deviations (low −6.1, fast −6.7; also backhand −7.0, deep −5.4) and stays a documented Stage 5 deviation (D-046).
- **Training:** the style reward fell from 0.30 to 0.06 per episode while the legal-return reward held (0.77 → 0.71). The discriminator kept improving; the policy did not move toward human states.

**Diagnosis:** the RegPPO pull-back toward the old student (coefficient 10 decaying to 1 over 1500 updates, plus a 100-update critic warm-up) stayed strong through this short run and anchored the actor to its old motion.

## Follow-up 1 (rule 8), decided before launch: S-D3-style-b
**One change:** a weaker pull-back, `PICKLEBOT_REF_COEF=1`, `PICKLEBOT_REF_FINAL_COEF=0.1` (decay 1500 and warm-up 100 unchanged).
- **Warm start:** from S-D3-style/model_7800. The discriminator continues from its saved weights (`PICKLEBOT_STYLE_LOAD`).
- **Unchanged:** everything else, including style weight 0.5.
- **Evaluation:** as above, on fresh dev seeds; the style score on 4,200,400 for a like-for-like comparison.

## Follow-up 1 result: S-D3-style-b (`2026-10-08_20-31-47_student-drill3-style-b/model_9100`)
- **Style score** (4,200,400): **4.85**, unchanged (target ≤ 3.86). **FAIL.**
- **Task** (4,200,270–272, no hint): Stage 4 families 95.3–97.6 % legal (better than S-D3b); reach FH 96.6, BH 25.7, short 5.0, deep 1.5 %; falls 5.5–6.0 %; recovery 0.98 m. Fixed-start retention against model_7600 is now within 5 points on every family (low −3.8, fast −4.5).
- **Training:** the style reward fell to about 0.01. The discriminator separated robot from clips almost perfectly (D 0.98 on clips, −0.99 on robot, loss 0.03), so the reward carried no signal.

**Feature analysis** (`artifacts/eval/style_gap.py`): the largest robot-vs-clip gaps are:
- waist pitch: robot 0.00 against clips 0.34 rad (z −2.1);
- the right **wrist** yaw, pitch and roll (z +1.8, +0.9, −0.65);
- shoulder roll and yaw (the free arm hangs; the players hold it up);
- hands relative to the pelvis.

The robot's spread is 20–40 % of the clips' in many joints. The wrist gap can never close: the wrist aims the paddle for the task, and the clips' wrist angles are the retargeting's swing-direction heuristic, not racket data. So the discriminator always has an easy cue and the reward saturates at zero.

## Follow-up 2 (rule 8, the last), decided before launch: S-D3-style-c
**One change:** the discriminator does not see the six wrist joints (angles and velocities); task `Picklebot-Student-Drill3-Style-NoWrist-G1`, 2 × 74 features.
- **Warm start:** policy from S-D3-style-b/model_9100; a fresh discriminator (its input changed); the weak pull-back as in follow-up 1.
- **Unchanged:** everything else.
- **If the style gate is still missed, the loop stops for the user.**
