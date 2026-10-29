# Phase 2 plan: left / back footwork under time pressure (2026-10-29)

Status: read-only research for D-169 phase 2. Nothing was run, trained or edited to write this. Every number below
comes from a file named next to it. Estimates are marked **(est.)**.

## 1. Summary

- **The gap.** In the M1 pair read, feeder balls that need a move to the robot's left or back (about 21 % of feeder
  balls) are returned 43-46 %. Forward and right balls are returned 86-93 % (results/rally-19-parent-early-dir.json,
  rally-19-early-dir.json, rally-14-endpoint-dir.json).
- **Ceiling of a footwork fix.** Lifting left / back to 70 % gives feeder legal about 85 %. Lifting it to 90 % gives
  about 89 %. With left / back at 90 % and right raised to forward's 92.7 %, feeder legal is about 92 %. Footwork is
  necessary for the target but not enough on its own: the target needs about 95 % per ball.
- **What has never been measured.** Fast stepping to the left or back (above about 1 m/s) has never been measured
  cleanly on the stack the rally policy uses.
  - The move drill's 96-99.7 % arrival is measured at a commanded speed of at most 1.0 m/s, with time limits of
    1.5 s + 1.25 s/m.
  - The agility-walker runs that found "no left / back" were confounded (D-086 finding 1).
  - Every lever tried before D-159 was judged with a learner frozen at the learning-rate floor.
- **Nothing in training pays for fast left / back travel.** About 35 % of training episodes are move episodes, and
  they reward tracking a command of at most 1.0 m/s that keeps the robot facing the net. The stance shaping
  (`stance_progress`) is clamped at 1.0 m/s. The frozen base's footwork was copied from a walking teacher that was
  trained at 1.0 m/s or less.
  - Yet the planner's reach check puts the median required speed of most feeder families at 1.2-1.7 m/s, and
    reach_deep at 2.36 m/s (results/feeder-reach-check.json).
- **Recommendation.** Start with one training screen, the "agility screen": a time-pressured move drill on the current
  composite stack, plus a flat-teacher calibration arm. It costs about 2 GPU-hours (est.) and routes the phase:
  - **Route E** (expected): train the rally policy with time-pressured, left / back-weighted move episodes, about
    10 GPU-hours (est.);
  - or **route C**: a fast walking teacher, kickstarted into the residual;
  - or the reading routes.

  Retraining the motion prior (route D) is last: 40-140 GPU-hours, and nothing yet shows that it is needed.

## 2. The gap in numbers

### By direction (feeder balls, M1 pair read)

Direction is from the pelvis at the feed's start to the ball at its closest approach to the paddle, in the start
heading frame (`scripts/diag/feeder_speed_envelope.py`).

| Read | Forward | Left | Back | Right | Left miss: closest distance (p50) | Back miss: closest distance (p50) |
|---|---:|---:|---:|---:|---:|---:|
| run 14 model_27798 (endpoint) | 93.6 % | 43.7 % | 52.7 % | 88.1 % | 0.93 m | 0.29 m |
| run 18b model_29000 (run 19 parent) | 92.7 % | 43.3 % | 46.4 % | 85.8 % | 0.89 m | 0.35 m |
| run 19 model_30200 | 92.2 % | 40.1 % | 43.5 % | 83.3 % | 0.90 m | 0.35 m |
| run 14, anchor y = 0.0 (diagnostic) | 93.8 % | 45.8 % | 53.0 % | 86.3 % | 0.76 m | 0.25 m |

Feed counts in the run 19 parent read: forward 2,585, left 909, back 509, right 2,655. The 0.35 m start-anchor bias
(audit F1) is real but small: about 3 points on left.

### Two different failure shapes

1. **Left: the robot does not get there.** Misses end about 0.9 m from the ball.
   - Left-side families: cross_backhand 72 % legal (misses: median 1.28 m away, 71 % of them to the left);
     reach_backhand 82 %; backhand 77 %.
   - On hits the robot moves fast (cross_backhand hits peak at a median 2.2 m/s); on misses it moves slower
     (1.5-1.6 m/s). Peak speeds are from rally-19-parent-early-dir.json and rally-14-endpoint-dir.json.
   - So the stack can travel left fast in some states, but it commits late or not at all. The panel's view (round 37
     and later): "leaned and reached instead of stepping".
2. **Back: the robot nearly gets there, then the stroke fails.** Misses end 0.25-0.35 m away.
   - Back contact is 60-69 %, back legal 43-53 %.
   - lam_r 2 raised back contact (65.5 -> 69.4 %) but not back legal. So the stroke while moving backwards is part of
     the back gap (round 37, motion).
   - reach_deep is the worst single family: 34-45 % legal, 55-60 % of its misses to the back.
   - Its misses peak at 1.13-1.25 m/s, against 1.44-1.54 m/s on hits. The planner says reach_deep needs a median
     2.36 m/s; only 12 % of reach_deep feeds need 1.5 m/s or less.

### Required speed against what training teaches

From the planner's walkable-contact rollout from the start spot (results/feeder-reach-check.json; the planner's
assumed walking cap is 1.5 m/s):

| Family | Median required speed | Share of feeds needing <= 1.0 m/s | Legal (run 19 parent) |
|---|---:|---:|---:|
| reach_forehand / reach_backhand | 1.21 / 1.39 m/s | 41 / 33 % | 93 / 82 % |
| cross_forehand / cross_backhand | 1.64 / 1.70 m/s | 24 / 24 % | 86 / 72 % |
| easy_forehand / backhand | 1.37 / 1.45 m/s | 31 / 35 % | 82 / 77 % |
| reach_deep | 2.36 m/s | 0.2 % | 34 % |
| fast | 2.18 m/s | 17 % | 64 % |

- **The mirrored pairs need almost the same speed, but the left member loses 11-14 points.** So the asymmetry is
  direction, not distance.
- **Most feeder balls need more than the 1.0 m/s the move drill commands.** The right side copes, so the composite
  can move above 1 m/s to the right.

## 3. How the controller was built, and what it can express

| Layer | What it is | How it was trained | Where it lives |
|---|---|---|---|
| H0 tracking teacher | 2048-1024-512 MLP, PPO motion tracking | tennis-v5 (Tennis-MoCap strokes, GMR retarget) + LAFAN1 (17 clips: walk, run, sprint, fight/sports; jumps dropped, D-051); about 20+ GPU-h (D-052). Later continued on mirrored LAFAN1 (s5c-03b/model_63300, D-079) | tracking runs; `tennis-lafan2.npz`, `tennis-lafan3.npz` |
| H1 latent controller | PULSE-style encoder q(z\|s,g), prior p(z\|s), decoder D(s,z); 32-d latent; proprioception 93-d (picklebot_mj/latent.py) | DAgger from H0 (scripts/distill_latent.py): MSE + smoothness 0.005 + KL 1e-4 + prior imitation 0.5. **latent-07/latent_10651**: 93.2 % tennis, 88.8 % LAFAN1 through the encoder (D-053) | artifacts/train/latent/latent-07 (LATENT_CONTROLLER) |
| Latent barrier | z = mu_p + lam sigma_p tanh(a) | lam 1 covers 0-3 % of clip latents, lam 3 covers 63-83 % (D-080) | tasks/latent_reach.py |
| Frozen base (RES_BASE) | s5c-18-merge17/model_32874: MLP actor, 124 obs -> 35 actions, lam 3 | Two-teacher kickstart (D-084/D-085). Footwork copied in joint space from the flat walking teacher (Picklebot-Teacher-Move-G1/model_15900) in move episodes and after the hit. Hitting copied exactly in latent space from run 17 (PPO hitting teacher at lam 3) | tasks/__init__.py `RES_BASE` |
| Residual (the rally policy) | z = mu_p + 3 sigma_p tanh(a_ref) + lam_r sigma_p tanh(a); wrist +-0.1 rad; optional leg joints (leg_r) | PPO from Stage 5C run 19 through rally runs 1-19. lam_r 2 since run 14. Penalty (lam_r tanh a)^2 at 0.05, 3x in move episodes | `ResidualLatentAction` in tasks/latent_reach.py; `_residualize` |

### What the stack can express

- **Decoder, through the encoder:**
  - LAFAN1 walk, run and sprint, original and mirrored (mirrored walk 92-93 %);
  - the walking teacher's footwork clips (100 %, D-081);
  - the 100STYLE backward-walking and sidestep-walking clips (57 / 57 windows, D-109). Under command delay the
    100STYLE windows stay at 100 % (stage5f.md).
- **Decoder, driven through the prior:**
  - at lam 3 it reproduces the walking teacher's leg actions to an MSE of 0.027 against a variance of 0.389
    (93 % explained, 26 % of latents saturated; results/stage5c-floor-move-l07.json);
  - so slow left / back steps facing the net are on the manifold.
- **Base:** slow, net-facing footwork in every direction (the walking teacher at 1.0 m/s or less: arrival 99-100 %
  in all 8 sectors, mean time 2.0-2.5 s; results/stage5-teacher-move.md), plus run 17's approaches in ball episodes.
- **Composite:**
  - fast travel to the right and forward (cross_forehand hit at a median 2.1 m/s peak, 86 % legal);
  - some fast travel to the left (cross_backhand hits at 2.2 m/s).

### What it cannot express, or what was never shown

- **Fast sidestep running.** 100STYLE sidestep running (SR) failed the retarget: the G1's ankle-roll joints sit at
  their limit in 33-45 % of frames (stage5e-style-reference.md), so it is in no training set. A fast shuffle facing
  the net may be near the G1's kinematic limit. Above about 1.5 m/s the human answer is a crossover or a turn-and-run.
- **Crossovers and drop steps.**
  - The tennis clips have few crossovers (4 forehand, 16 backhand; results/stage5b-footwork-coverage.json).
  - LAFAN1's crossovers are mostly in forward running.
  - The frozen style reference has no crossover or drop-step clips (D-109 item 11).
  - The "turn-and-go footwork for deep balls" item in D-108's shot list was never run.
- **Fast backpedalling.** The 100STYLE backward-walking clip is a slow walk; it was kept out of training (D-109).
  LAFAN1 moving frames are about 10 % back (D-081).
- **A clean measure of fast left / back travel on the composite.** None exists.
  - Agility-walker runs 1, 7, 8, 9 and 11 (D-077 to D-082) were confounded by a world-fixed paddle target that
    penalised travel (D-086 finding 1).
  - Move-drill arrival tests only travel at 1.0 m/s or less.
- **The prior is the bottleneck for selection, not the decoder** (D-080, D-082): at lam 1 PPO could not find
  sidesteps even though the decoder can produce them. Kickstarting from a teacher was what put left / back stepping
  in. **That precedent matters for route C.**

### What training rewards today (rally run 19's params/env.yaml)

- **Move episodes (`move_prob` 0.35, uniform sectors):**
  - `move_track_lin_vel` and `move_track_yaw` (weight 2.0 each) track an internal command toward the spot. Its speed
    is min(1.0 m/s, 1.2 x distance) and it turns the robot to face the net (move_drill.py `CMD_MAX_SPEED`).
  - `move_arrival` pays 100 at arrival (within 0.25 m, slower than 0.2 m/s, held 0.3 s).
  - The time limit, 1.5 s + 1.25 s/m, is about 1.6x the mean arrival time.
- **Ball episodes:**
  - `stance_progress` and `spot_progress` (weight 1.0): pelvis speed toward the stance or spot, clamped to +-1.0 m/s.
  - `approach_ball` and `approach_far` are active only after the bounce.
  - Fast travel is paid only through the sparse contact and return rewards (50 / 250).
- **No overspeed penalty** in the rally task.

So the only signal for fast left / back travel is the sparse hit reward, on about 21 % of feeder balls. Feeder balls
are about 1/3-2/3 of training balls, depending on the court group (D-162, D-163).

## 4. Status of past levers (the D-159 caveat)

| Lever | Run | Result | Learner | Status |
|---|---|---|---|---|
| Leg-joint residual +-0.1 rad | 12 (D-152) | no engagement (output rows at random-walk size) | frozen (1e-5) | open |
| Leg-joint residual +-0.3 rad | 13 (D-153) | arrival -17, falls 4.5 %, left 36.6 -> 30.5 % | frozen | open, but the damage came from joint-space **noise**, which a working learner does not remove |
| lam_r 1 -> 2 | 14 (D-154) | left 36.2 -> 43.7 % (the only lever that moved left) | frozen | kept |
| lam_r 2 -> 3 | 15 (D-155) | left + back contact -3.5 points; left legal 45.5 -> 39.6 % | frozen; `lam_r_init.py`'s 2/3 scaling is inexact for saturated rows | open |
| e4 privileged contact teacher (x1, x30) | 16-17 (D-156/157) | input never used (column norms 0.03-0.06) | frozen | open: e4 is untested |
| Feeder bonus on the weak families | 11 (D-150) | did not move them | frozen | open |
| LR 1e-4 restart | 18b, 19 (D-159/160) | partner balls up fast; left + back down (-6.3 at run 19) | working | the working learner improves partner balls and lets feeder left / back erode |

The last row matters: with a working learner and no footwork signal, left / back **fell**. The current rewards do
not hold, let alone grow, that skill.

## 5. Candidate routes

GPU cost assumes 7.1 s per iteration at 12,288 envs, about 15 min per read, and about 15 min per 200-iteration
1,024-env screen arm (the screen45 and at-T* runs). A full rally run (4,000 iterations, early check at +1,200,
parent re-read, early, endpoint and direction reads) is about 7.9 h of training plus about 1.5-2 h of reads, so
about 10 GPU-h.

### (a) Re-open the leg-joint residual with the working learner

- **Idea:** `leg_r` 0.3 on run 14's task from the phase-1 parent. The code exists (`_leg_residual`,
  `scripts/leg_residual_init.py`, task `...-LegRes30-G1`).
- **Smallest first experiment:** a learning-rate-0 screen (200 iterations, 1,024 envs) of the widened parent at two
  leg-std inits (the wrist mean, as run 13, and 0.02). Measure falls and untimed move arrival against the parent.
  Run 13's damage appeared before any learning, so the init std is the first thing to settle. This is about
  0.5 GPU-h, then a rally run (about 10 GPU-h).
- **Code:** about 10 lines (a std argument in `leg_residual_init.py`; check that it composes with `fresh_init.py`
  and ScheduledPPO's std floor of 0.1. **The floor would hold the leg std at 0.1 or more:** the floor needs a
  per-output exception, another about 15 lines).
- **Risk: high.**
  - Joint-space moves are off the decoder's manifold. The panel agreed (round 37) that small moves give no signal
    and wide moves break the gait.
  - The decoder reads its own last raw output, not the applied target, so its input drifts.
  - Style and falls.
- **Premise in training:** the leg-std screen above (falls and arrival within the family guards at learning rate 0).
  That only shows the lever is safe to try, not that it helps.

### (b) lam_r 3 with the working learner

- **Idea:** widen the residual's latent range to 3 sigma (`...-LamR3-G1`, `LAM_R_3`).
- **Smallest first experiment:**
  - First fix the init: map rows through atanh so that `3 tanh(a')` equals `2 tanh(a)` exactly, clipping at
    |tanh| < 0.999. About 15 lines in a new script; `lam_r_init.py`'s linear scaling started the saturated left /
    back rows away from the parent (round 38).
  - Then a rally run (about 10 GPU-h).
- **Risk: medium-high.** The composite can then sit 6 sigma from the prior mean, off the decoder's support (D-080:
  clip latents have a 90th percentile of 3.2-4.9 sigma). Run 15 lost left / back.
- **Premise in training:** residual saturation by direction. Log, at learning rate 0 on the training task, the share
  of feeder-ball approach steps (feed start to contact) with at least 4 latent dimensions at |tanh(a)| > 0.95, split
  by the feeder's direction. Range binds if the left / back share is at least 2x the forward / right share and at
  least 25 % of steps. About 30 lines of logging, 0.25 GPU-h. If it does not bind, (b) is rejected without a run.

### (c) Fine-tune or replace the base's footwork with a fast walking teacher

- **Idea:** the D-082/D-084 precedent. The latent space could express footwork that PPO never found; a teacher put
  it in.
  - Train a **fast walking teacher**: `Picklebot-Teacher-Move-G1`/model_15900, flat joint-space PPO, on the
    time-pressured drill of section 6 (deadline spots at 1.2-2.2 m/s, all 8 sectors, left / back weighted). Heading
    is free during the run and faces the net in the last 0.5 m, so it can find crossovers and turn-and-run.
  - Check the composite's **expressiveness floor** on its states. `scripts/latent_reach_floor.py` fits the action
    about mu_p; extend it to fit the residual about the base's z_ref.
  - Then **kickstart the residual**. On move episodes, DAgger toward the fast teacher's joint targets through the
    frozen composite. On ball episodes, copy the parent residual's own action exactly (latent loss, as D-084), so
    hitting is kept.
  - Then continue PPO on the rally task.
  - Unfreezing or re-kickstarting the base itself (a new RES_BASE) is the heavier variant. Stage 5E's consolidation
    lost skill (D-107), so the residual-space kickstart comes first.
- **Smallest first experiment:** screen arm F in section 6 is this teacher's first 400 iterations. If F shows the
  body can make the deadlines on the left and back, extend F to a full 2 h teacher run. Then run the floor check
  (0.25 GPU-h).
- **Code:** about 60 lines (deadline drill, shared with route E), plus about 40 lines (floor about the base), plus
  about 150 lines (adapt `kickstart_h4.py` to the residual action term; its `--hit-loss latent` path already copies
  latents exactly).
- **Cost:** teacher about 2-4 GPU-h, floor about 0.25, kickstart about 2, rally PPO about 10. Total about 15-17 GPU-h
  plus reads.
- **Risk: medium.** Kickstarted executors blew up under plain PPO three times (runs 13, 14 and 20 in Stage 5C); as a
  residual they did not (run 19). A flat PPO teacher's gait may score badly on style (style is reported, not gated,
  for the rally target). Hitting retention is guarded by the exact latent copy.
- **Premise in training:**
  - F's deadline arrival in the left / back sectors (sectors 2, 3 and 4) is within 10 points of the forward / right
    sectors (0, 6 and 7): the body can.
  - The residual-about-base floor explains at least 85 % of the fast teacher's leg-action variance: the composite
    can express it.

### (d) New reference motions or a retrained motion prior

- **Idea:** add fast lateral, crossover, drop-step and backpedal motion to H0 and H1, then rebuild the base and
  re-climb.
  - The data would come from route C's fast teacher, recorded as clips (`scripts/motion/record_policy_clips.py`,
    as D-081 did), because no download is approved: 100STYLE SR fails the retarget; any new mocap download is the
    user's call.
  - Retraining the prior moves mu_p and sigma_p, which breaks the frozen base and every residual (D-109: "a frozen
    encoder and prior cannot take in new H0 skills").
  - A decoder-only re-distillation (encoder and prior frozen, D-108 item 5) keeps compatibility, but it cannot make
    the prior select new skills.
- **Smallest first experiment:** record the fast teacher's clips and score them through latent-07's encoder
  (`tracking_eval.py --latent`). At 95 % or more, the decoder already tracks them, and route D is not needed: the
  gap is selection, which route C handles. This is only reached after route C's teacher exists (about 0.5 GPU-h
  more).
- **Code:** about 50 lines plus the existing H0 / H1 pipelines.
- **Cost:** 40-140 GPU-h (D-158's estimate), plus a rally re-climb from a new base.
- **Risk: high** (compatibility, serve loss: s5c-06 lost about 10 points of serve, D-080). Last.
- **Premise in training:** encoder-path tracking of the fast clips below 90 % (the decoder cannot express them), and
  route C failed its floor check.

### (e) A time-pressured move drill in rally training (recommended after the screen)

- **Idea:** change what move episodes teach. The same share of episodes (0.35) gets deadline spots:
  - distance 0.5-3.0 m;
  - a required speed v_req drawn from U(1.0, 2.0) m/s;
  - limit = 0.3 s + d / v_req;
  - the internal velocity command's cap raised from 1.0 m/s to v_req;
  - the heading command off beyond 1.0 m from the spot, toward the net inside it;
  - arrival pays only before the deadline, as now;
  - sector weights 2x on sectors 1-5 (forward-left through back-right; the existing `move_sector_weights` field).

  Everything else is run 14's task (the rally training task).
  - This aims straight at "reads late and does not commit to the step". The policy learns to launch a fast step to
    the left or back from a given spot. Ball episodes keep their sparse reward, which then has a skill to select.
- **Smallest first experiment:** the agility screen (section 6), then one rally run.
- **Code:** about 60-80 lines and about 60 lines of tests.
  - `DeadlineMoveDrill(MoveDrill)`: `_new_spot` and `command` overridden, and per-sector deadline-arrival counters
    added to the training log.
  - A ball-term cfg flag, or a subclass that swaps the drill after `__init__`.
  - Tasks registered in a new module.

  While the phase-1 run trains, all of this goes in **new files** (D-159's rule).
- **Cost:** screen about 2 GPU-h, rally run about 10 GPU-h.
- **Risk: medium.**
  - Transfer from move episodes (ball parked) to ball episodes is not guaranteed. The policy can tell the two apart,
    as it does today.
  - Faster gaits may raise falls; court falls are guarded at 4 % or less.
  - The old untimed move read stays as a forgetting guard (arrival of 90 % or more in every sector).
- **Premise in training:** screen arms A0 and A (section 6). There must be a left / back deadline deficit at
  iteration 0, and the residual must close at least half of it within 400 iterations.
- **Expected gain (est.):** if the screen's rule passes, left / back +10 to +25 points (to about 55-70 %), feeder
  legal +2 to +5 points.

### (f) Other routes the code suggests

1. **Stance-progress cap 1.0 -> 2.0 m/s.** A one-line parameter on an existing reward term. It pays for fast travel
   toward the ideal stance before the bounce, in ball episodes, where route E's transfer risk does not apply.
   - Premise in training: the share of feeder-ball approach steps with pelvis speed toward the stance above
     1.0 m/s (reward capped), by direction. It must be at least 15 % on left / back misses.
   - About 10 GPU-h. A good second lever after E, or a fallback if E's transfer fails.
2. **The e4 privileged contact teacher, re-tested with the working learner.** The code exists (`_teacher`,
   `expand_checkpoint.py`, `TEACHER_GAIN`). It answers "reads late" directly: with the true contact point and time,
   does left / back rise?
   - About 10 GPU-h, plus a DAgger student (about 5-10 GPU-h) if it passes D-156's gate.
   - Premise in training: the used line (zeroing the input loses at least 3 points of left + back contact) plus the
     screen's arm A0 showing *no* motor deficit. If the robot steps fine when it is told where to go, the limit is
     reading.
3. **Feeder families weighted to the left and back** (`feed_mix` toward cross_backhand, reach_backhand, backhand,
   reach_deep and deep).
   - Configuration only, about 10 GPU-h. It was tried only with the frozen learner (runs 5 and 11).
   - Weak on its own: it adds samples, not signal.
4. **The back stroke.** Back misses end about 0.3 m away, so part of back is a contact-quality problem (the paddle
   face while moving backwards; cf. the D-128 face factor). This is outside footwork. Report it rather than chase it
   here.
5. **The feed anchor (0.35 m left bias).** It is part of the frozen read protocol (D-160: "reads stay at anchor
   0.35"). The y = 0 diagnostic gains about 2-3 points on left. It is not a lever, and it is never a loosening.

## 6. The recommended first step: the agility screen (training-side, about 2 GPU-h)

One diagnostic with four arms. It measures, in training, the premise that decides between E, C, (b) and the reading
routes. Training seeds come from 1-999 and are recorded in the ledger. The parent P is phase 1's last passing
checkpoint, or run 18b model_29000 if phase 1 has none.

### The drill (shared by every arm)

- Move-only episodes (`move_prob` 1.0, `swing_prob` 0), the rally task's observations and rewards otherwise.
- Spots at 1.0-3.0 m, **uniform** over the 8 sectors (this is a measurement), v_req drawn from U(1.2, 2.0) m/s,
  deadline = 0.3 s + d / v_req.
- Command cap = v_req; heading as in route E.
- Counted per sector:
  - arrival before the deadline (DA);
  - untimed arrival;
  - peak pelvis speed;
  - falls;
  - for the residual arms, the residual saturation share (at least 4 latent dimensions at |tanh(a)| > 0.95).
- Groups: **LB** = sectors 2, 3 and 4 (left, back-left, back); **FR** = sectors 0, 6 and 7 (forward, right,
  forward-right).

### The arms

| Arm | Policy | Learning rate | Iterations / envs | Purpose |
|---|---|---|---|---|
| A0 | P (residual, lam_r 2) | 0 | 100 / 4,096 | deficit at the start: D0 = DA(FR) - DA(LB) |
| A | P | 1e-4 (ScheduledPPO, P's Adam state) | 400 / 4,096 | can the current action space learn it? |
| F | flat walking teacher model_15900 on the same drill (its own task) | 1e-4 | 400 / 4,096 | the body's ceiling at these deadlines |
| B (only if A fails and A's LB saturation share is at least 25 %) | P widened to lam_r 3 (exact atanh init) | 1e-4 | 400 / 4,096 | does range bind? |

### Pre-registered rule (to be coded so that it prints PASS / FAIL)

1. **D0 < 10 points:** the motor skill has no direction-specific deficit under time pressure. The footwork routes
   (a)-(e) are rejected. The next step is the reading route (f2, e4 re-test), then (f1).
2. **D0 >= 10, and A's DA(LB) at 400 >= DA(LB) at 0 + 15 points, with the deficit at most 0.5 x D0:** the composite
   can learn fast left / back stepping. **Run route E** (section 7).
3. **D0 >= 10 and A fails rule 2, while F's DA(LB) >= F's DA(FR) - 10:** the body can and the residual cannot. If B
   was triggered and passes rule 2, run (b) with the exact init. Otherwise go to **route C** (extend F into the fast
   teacher, then the floor check).
4. **D0 >= 10 and F also fails** (DA(LB) < DA(FR) - 10): at these deadlines the limit is the body or the time budget,
   not the controller.
   - Lower the v_req band to U(1.0, 1.6), report again, and do not run a footwork lever.
   - Earlier commitment is then the only lever left: the reading route.

### Ball-side logging

The ball-side logging is part of the same screen, not a second diagnostic.

- **What:** the training task at learning rate 0, 200 iterations at 1,024 envs, with the feeder ball's direction
  class logged in training, using `feeder_speed_envelope.py`'s classification ported into the ball term's tally.
  Logging only.
- **What it reports:**
  - training left + back feeder legal [train-diag];
  - onset latency by direction: the first control step after the feed's start at which pelvis velocity toward the
    eventual contact point exceeds 0.5 m/s;
  - (b)'s saturation share.
- **Line:** route E's ball-side premise is training left + back feeder legal of at most 55 %, against forward + right
  of at least 80 %. That shows the deficit exists in the population that training acts on, not only in the read
  (the D-166/D-167 lesson).

**Cost:** A0 about 0.15 h, A about 0.4 h, F about 0.4 h, B about 0.4 h (if run), ball-side logging about 0.25 h.
About 1.6-2 GPU-h (est.; iteration time at 4,096 envs is not measured in the logs I read).

**Code:**
- `DeadlineMoveDrill` (about 60 lines, shared with routes C and E);
- per-sector deadline log (about 20 lines);
- the direction tally in training (about 40 lines);
- the saturation counter (about 20 lines);
- `screen_agility.sh` and a summary with the coded rule (about 80 lines);
- tests (about 60 lines).

All in new files while phase 1 trains.

## 7. Route E's rally run (if the screen routes there)

- **One change:** move episodes become the deadline drill: v_req drawn from U(1.0, 2.0), d 0.5-3.0 m, sector weights
  2x on sectors 1-5. The share stays at 0.35. Run 14's task otherwise.
  - Experiment design may prefer the deadline alone with uniform sectors. The weighting is justified only if A0
    shows the deficit is left / back-specific; that is fixed before launch from the screen.
- **Parent:** P, with its optimizer. **Matched arm:** P's continuation without the change (run 19's model_30200 if P
  is model_29000).
- **Training:** 4,000 iterations at 1e-4, cooldown over the last 20 %, early check at P + 1,200.
- **Early-kill lines** (coded; sized from the measured read noise: SD of left + back contact 1.31 points per read,
  so SD of a difference about 1.85):
  - left + back feeder contact >= parent + 3.0;
  - training DA(LB) up >= 10 points [train-log];
  - feeder legal >= parent - 1.0;
  - the cumulative family guards (D-160);
  - untimed move arrival >= 90 % in every sector;
  - court falls <= 4 %.
- **Endpoint (read once):**
  - left + back feeder legal >= parent + 8 points, with a bootstrap low above the parent's point;
  - feeder legal >= parent + 2;
  - P(5+) open >= parent - 1.5;
  - sides within 3 points, falls <= 4 %;
  - M1 and the target read and reported.
- **Cost:** about 10 GPU-h.
- **If it engages but stalls:** the next single change is (f1), the stance-progress cap at 2.0 m/s (the ball-episode
  analogue).
- **If it does not engage while A passed:** transfer from move episodes to ball episodes failed. Go to (f1), then C.

## 8. Ranking by expected gain per GPU-hour toward left / back of 70-90 %

Probabilities and gains are my estimates from the evidence above, not measurements.

| Rank | Route | GPU-h | P(engages) (est.) | Left / back if it works (est.) | Why this rank |
|---|---|---:|---:|---|---|
| 1 | **Agility screen** (section 6) | about 2 | (a measurement) | none on its own | decides the route; every other row's premise comes from it |
| 2 | **(e) time-pressured move drill** | about 10 | 0.5 if the screen routes here | 55-70 % | aims at the measured mechanism (no signal for fast travel); small code; on the decoder's manifold |
| 3 | (f1) stance-progress cap 2.0 m/s | about 10 | 0.3 | 50-60 % | one parameter; ball episodes directly; weaker shaping |
| 4 | **(c) fast teacher + residual kickstart** | about 15-17 | 0.5 if the screen shows an action-space limit | 65-85 % | the only route with a precedent for adding left / back stepping (D-082 to D-085); more code; most headroom |
| 5 | (f2) e4 teacher re-test | about 10 (+5-10 student) | 0.35 | 50-65 % | answers "reads late"; needs distillation to count |
| 6 | (b) lam_r 3, exact init | about 10 | 0.25 | 45-55 % | cheap, but off-support risk, and run 15 went the wrong way |
| 7 | (f3) left / back feed mix | about 10 | 0.2 | 45-50 % | samples without signal |
| 8 | (a) leg residual re-opened | about 10.5 | 0.15 | 45-50 % | off-manifold; run 13's damage came from noise, not the learner |
| 9 | (d) new motion data / retrained prior | 40-140 | unknown | up to 90 % in principle | breaks compatibility; needed only if C's floor check fails |

**Reaching 90 % on left / back** likely needs C, or E followed by C, plus the back-stroke work in (f4). E alone
plausibly reaches the 60s. Even at 90 % on left / back, feeder legal is about 89 %. The target also needs the fast /
low families (forward / right misses) and partner balls.

## 9. Recommendation

1. **Build the agility screen in new files and run it** as soon as the GPU is free, or alongside phase 1 if phase 1
   ends or plateaus.
   - It needs about 2 GPU-h and about 300 lines including tests.
   - Its rule (section 6) is pre-registered here and is to be coded with PASS / FAIL printing before the first arm
     runs.
2. **Expected route: E.** The premise to measure in training before the vote:
   - At iteration 0 on the training stack, deadline arrival in the left / back sectors is at least 10 points below
     the forward / right sectors (A0).
   - 400 iterations of PPO on the current composite (lam_r 2) raise left / back deadline arrival by at least
     15 points and halve the gap (A).
   - Training left + back feeder legal is at most 55 %, against forward + right at least 80 % (ball-side logging).

   The source tag is [train-diag] for A0 and the ball-side logging, and [train-log] for A.
3. **If A fails but F passes:** route C, a fast walking teacher kickstarted into the residual. The floor-check
   premise is that the residual-about-base fit explains at least 85 % of the fast teacher's leg-action variance.
   Route D only if that floor check fails.
4. **If D0 < 10:** footwork is not the deficit. Move to the reading route: the e4 re-test, then the stance-progress
   cap. Report the controller hypothesis as refuted.

## 10. Uncertainties and things to check before building

- **The required-speed numbers come from the planner's model** (`planner._walk_step`), launched from the start spot
  at reset. They are a model of time pressure, not a measurement of the robot. A0 and the ball-side onset latency
  measure the robot.
- **Iteration time at 4,096 envs** is not in the files I read. The screen costs are scaled from the 1,024-env
  screens (about 15 min per 200 iterations, including start-up).
- **The internal velocity command, and its heading, shape the gait** in move episodes. If F finds crossovers and
  turn-and-run only with the heading free, route E's heading rule (free beyond 1 m) matters. Check it in the A and F
  videos (one short render each, CPU-side review).
- **ScheduledPPO's std floor (0.1)** applies to every output. For route (a) it prevents a small leg-noise init.
  Check `picklebot_mj/rl/sched_ppo.py` before any leg-residual work.
- **Residual kickstart through the frozen composite (route C)** has not been built. `kickstart_h4.py` targets the
  plain latent action term. Budget a smoke run that checks a zero-loss start reproduces the parent exactly, as
  D-086 required for the residual.
- **The phase-1 run's outcome may change P.** Every line above is written against "P re-read", so it holds for any
  parent.
