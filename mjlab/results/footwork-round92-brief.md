# Panel round 92 brief: effort does not bind; C's baseline on the new set-start read is 0.5645; name the next step, 2026-11-06

Read first:
- D-227 to D-230, with their results, in docs/DECISIONS.md;
- round 91 in mjlab/results/footwork-review.md;
- results/sr91-summary.txt and results/act91-summary.txt;
- the G1 actuator constants (WSL: /home/gem/envs/picklebot-mj/lib/python3.12/site-packages/mjlab/asset_zoo/robots/unitree_g1/g1_constants.py);
- picklebot_mj/tasks/footwork_specialist.py (with_strong_legs);
- the frozen target (results/rally-target.md, with the D-228 / D-229 set-start read).

## Results since round 91

**1. fw-scratch-01 (from a random init on Q2's task):** KILL-NO-START at +1,850. It learned to stand (0 falls, full-length episodes) and never moved: 0 arrivals and 0 first-step samples. PPO from scratch does not find locomotion on this task. The lineage question is still open.

**2. Premise read (fw1b-S, mean actions, dev 4220383):**
- **Saturation:** at the standard limits, the hips and knees reach >= 0.95 x effort on 0.0000 of samples in the first 1.0 s of moves; the ankles on 0.0043.
- **Effort x2 zero-shot:** first step 1.366 / 1.412 s, against 1.364 / 1.407. Unchanged.

**3. fw-act2-01 (Q2 under effort x2 from fw1b-S):** KILL-NO-START at +482 (1.285 / 1.382 s at 400-450). Every window is within one bin of Q2 at standard limits. **Effort is ruled out** as what binds the start.

**4. C's baseline on the new set-start read** (drill reset; dev 4220385-4220388 pooled):

| read | P(5+) | rallies | h0 / h1 / h2 / h3 / h4 | feeder legal |
|---|---|---|---|---|
| set start | **0.5645** (Wilson 0.553-0.576) | 7,331 | 0.245 / 0.187 / 0.065 / 0.013 / 0.003 | 0.762 |
| old read, same seeds | 0.4061 | 10,183 | 0.376 / 0.275 / 0.078 / 0.022 / 0.005 | 0.635 |

- **The gap to the bar** is still the two opening balls: (1 - h0)(1 - h1) = 0.614, against about 0.886 needed.
- **C was never trained under a set start.** Its residual learned the old read's spawn scramble.

**5. Reference motion:** SMPL-X is installed (D-230). The SMPL v1.1.0 models are still needed and wait on the user's second registration.

## The actuator facts (motion, round 91)

- The actuators are BuiltinPositionActuator. kp = armature x (10 Hz x 2 pi)^2, damping ratio 2.0, and G1_ACTION_SCALE = 0.25 x effort / kp, so a unit action asks for about 25 % of the effort limit.
- **Damping at speed:** the knee's damping takes about 63 Nm at 10 rad/s.
- Joint velocity limits are not enforced.

**Resources:**
- The GPU is idle.
- Training seeds: next free 228.
- Dev seeds: next free 4220389 (4220340 held; 4220349-4220356 CONFIRM only; 4220382 and 4220384 unread).

## Questions

1. **Correction check.** Is anything misstated?
2. **The next step.** Vote for one, with the one change, parent, smoke / kill / gate lines readable on windows that exist, seeds and GPU hours. Name the simpler option you rejected.
   - **(a) The damping route:** damping ratio 2.0 -> 1.0 (kd halves) on legs, waist and ankles, in new tasks only, action scale and kp unchanged. A zero-shot premise read first, then Q2 under it.
   - **(b) The action-scale route:** a unit action reaches more of the effort, for example G1_ACTION_SCALE x2 on the legs. This changes the policy's output map, so a warm start must adapt.
   - **(c) The stiffness route:** natural frequency 10 -> 15-20 Hz (kp up).
   - **(d) Practise the new read:** train C's residual under the set start (drill reset in training) with C's recipe. Practice then matches the read; the opening hazards are where the gap is, and C never trained on placed starts. Gate on the new reference seeds against C's 0.5645.
   - **(e) Other**, for example the reference-motion pilot as soon as SMPL arrives.
3. **Order.** If more than one should run, in what order? Which has the largest expected gain toward 0.80 on the new read?
