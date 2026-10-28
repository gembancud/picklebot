# Environment audit, 2026-10-28

Scope: the environment side of `Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1`
(registered at `mjlab/picklebot_mj/tasks/__init__.py:2157-2171`), traced through every config function it builds on,
back to `return_stand_env_cfg` and mjlab's flat G1 velocity config. Read-only. Nothing that imports mjlab or warp, and
nothing on the GPU, was run. Three small CPU-only scripts used only the analytic ball model (`picklebot_mj/ball_sim.py`,
pure torch). They are in the session scratchpad: `feed_geom.py`, `feed_dir.py`, `pace.py`. One more read TensorBoard
scalars of `lrsweep-1e-4`.

Line numbers are for commit 64aff3c.

## Summary

- **One confirmed geometric bias plausibly explains a large part of the left (and fast/low) gap.** Every start-anchored
  feed is aimed relative to `ROBOT_START = (-5.6, 0.35)`, while the robot is told to recover to y = 0. So every
  feeder family arrives 0.35 m further to the robot's left than its definition says. That covers drill v2 feeds, 75 %
  of court feeds (about 80 % of training feeder balls), and every M1 / pairs / direction-split read. The same checkpoint
  returns pelvis-anchored feeds (court read) far better on exactly the families this shift hurts.
- **One confirmed pair-mode bug: a reset does not park the env.** The reset path marks the new ball dead, then revives
  it a few lines later. As a result, each robot episode starts with a live ball that the pair logic does not know
  about. That ball can earn an unearned "early" legal return (+5, rally bonus, streak, sometimes +3 partner credit for
  the partner) when the partner's hand-off arrives.
- **One confirmed reward conflict.** The pace ceiling (-25 x clamp((|v_out| - 9.5) / 2, 0, 1)) is close to fully on for
  every return that the keep-alive reward pays in full. Landing in the keep-alive box after 1.3-1.5 s needs about
  10.6-11.7 m/s of outgoing speed even from x = -4.5 to -5.6. The pairs read shows the compromise: mean out speed
  10.1 m/s, mean landing x 3.93 (short of the box at 4.7), and only 14 % of legal landings in the box.
- **Medium and low items:**
  - `stance_progress` still pulls toward a stale spot (known since D-142, still in this chain).
  - For deep balls the planner puts its stance spot about 2.5 m behind the robot. The move drill never practises going
    behind x = -6.4.
  - Swing episodes are dead in pair mode.
  - The ball term's seed is always 0 in training.
  - Some generators share seeds.
  - The fall penalty was dropped from the chain long ago.
  - Families are clamped to constant aims.
- **Nothing else turned up.** I found no sign error, frame error, mirroring error, two-sidedness error in the paddle
  contact, obs/action clipping, curriculum stuck, mis-scaled dt or double-counted term. The list of what was checked and
  found correct is at the end.

---

## Confirmed bugs or confirmed defects

### F1 (HIGH). Start-anchored feeds are aimed 0.35 m left of where the robot is sent to stand

- **Where:**
  - `picklebot_mj/tasks/return_stand.py:42` `ROBOT_START = (-5.6, 0.35)`
  - `return_stand.py:60` `RECOVERY_FIXED = (-5.6, 0.0)  # evaluation: baseline centre`
  - `_anchor` start branch at `return_stand.py:632-642`. It returns `ROBOT_START` for v2 feeds and court-anchored
    court feeds.
  - Feed lateral position at `return_stand.py:736`: `y = (ay + lateral_y).clamp(...)`, with vy = 0, so the ball stays
    on that line.
  - The robot's recovery target:
    - `RECOVERY_FIXED` at each episode start (`return_stand.py:437-440`);
    - `0.4 * y_pelvis` after a contact (`drill_v2.py:65-69`);
    - `RECOVERY_FIXED` for court-anchored court feeds (`return_stand.py:728-732`).
  - Evaluation does the same:
    - `stage2_eval.py:134-135` (`--rally` sets `feed_anchor = "start"`, recovery fixed);
    - `scripts/diag/feeder_speed_envelope.py` (`b.feed_anchor = "start"`, `recovery_mode = "fixed"`).
  - The start-pose code knew about the offset and re-centred it: the court reset range is y +-2.6 absolute
    (`tasks/__init__.py:849-851`), and `stage2_eval.py:143` subtracts `ROBOT_START[1]`. The feed anchor was never
    re-centred.
- **What is wrong:**
  - The family ranges are defined relative to the pelvis ("its right is -y", `feeds.py:4`). The Stage 2-4 drills
    started the robot at y = 0.35, so the anchor matched.
  - Since the rally drill (D-092) and drill v2 (D-097), the robot recovers to y = 0 or to 0.4 y, but balls are still
    aimed from y = 0.35. Every start-anchored family is therefore shifted 0.35 m to the robot's left:
    - "easy_forehand" (-0.65..-0.30) becomes a ball at the body (-0.30..+0.05);
    - "backhand" becomes a wide backhand (0.65..1.0);
    - reach_backhand spans 1.35..2.85 m to the left, while reach_forehand spans only 0.65..2.15 m to the right;
    - cross_backhand clamps at the left sideline in 97 % of feeds; cross_forehand clamps in about 50 % (see F9).
  - The paddle is in the right hand, so a forehand needs the pelvis 0.5 m to the left of the ball. The shift turns most
    neutral feeds into "step left to make room" feeds.
- **Evidence.**
  - Simulation (`feed_geom.py`): analytic ball, 1,500 feeds per family, true spin, the planner's "top" interception
    rule and its stance offsets, robot at (-5.6, 0.0). Median move to a forehand stance (and lateral part):
    - easy_forehand 0.45 m (0.37 m to the left), deep 0.42, low 0.46, fast 0.58 (in 0.94 s);
    - with the anchor at y = 0 the same feeds need about 0.02-0.1 m laterally.
  - Best-stroke median move: reach_backhand 1.77 m against reach_forehand 0.99 m. About 0.7 m of that 0.78 m asymmetry
    comes from the anchor offset; the rest is the 0.5 vs 0.4 m stance offsets.
  - The same checkpoint (lrsweep-1e-4 model_28197) on its three reads, legal return per family:

    | family | court read (pelvis-anchored, `lrsweep-1e-4-early-court.json`) | v2 read (start-anchored) | pairs read (start-anchored) |
    |---|---:|---:|---:|
    | backhand | 0.95 | 0.81 | 0.80 |
    | reach_backhand | 0.91 | 0.83 | 0.74 |
    | fast | 0.91 | 0.69 | 0.66 |
    | low | 0.95 | 0.83 | 0.73 |
    | easy_forehand | 0.94 | 0.91 | 0.87 |
    | deep | 0.99 | 0.94 | 0.86 |
    | reach_forehand | 0.91 | 0.96 | 0.93 |

    The families that the shift moves left or makes body-close lose 10-25 points under start anchoring.
    reach_forehand, which the shift brings 0.35 m nearer, does not lose. This is the signature of the offset.
    It is confounded by the robot being out of position between rally feeds in the start-anchored reads, which is why
    the verification below is needed.
  - The direction split's "left" bucket is mostly backhand-side families. Their difficulty is inflated by the same
    0.35 m. `feed_dir.py` estimates that with the anchor at y = 0 the left share would fall from 17.8 % to 14.5 % of
    feeds, and the right share would rise from 24 % to 47 %.
- **Confidence:**
  - That the offset exists and reaches training and evaluation: certain.
  - That it is unintended: likely. The drill v2 docstring calls the anchor "the fixed start spot" and the recovery spot
    "the baseline centre" as if they were the same place.
  - That it explains much of the measured left gap: medium. It inflates the left/fast difficulty. It does not by itself
    prove the robot steps left well.
- **Cheap verification:** one GPU read when the GPU is free. Re-run `feeder_speed_envelope.py` and the pairs read on
  model_28197 with the same seeds and the start anchor moved to y = 0. An eval-only override is enough, for example a
  temporary `ROBOT_START[1]`-free start branch in `_anchor`. Expected result:
  - fast, low and backhand-side legal rates rise toward the court-read values;
  - reach_forehand falls slightly;
  - the left bucket shrinks.

  If it confirms, decide whether training should anchor at y = 0, or at (0.35 + 0.4 y_recovery). Either way, record it
  as a measurement change: the M1 baselines change too.

### F2 (MEDIUM). Pair mode: a robot reset does not park the env; its new ball is live and can earn an unearned legal return

- **Where:** `BallPhysicsAction.reset`:
  1. `return_stand.py:441` `self._feed(env_ids)`.
  2. `:442-450`: pair block, `self.pairs.on_reset(...)`, `self.rules.lost(mk)` (phase DEAD), `self.tallied |= mk`. The
     comment says "the env waits with no ball in play".
  3. `:462` `self.rules.begin_from_feed(env_ids, ...)` calls `_reset_common`, which sets the phase back to SERVE_FLIGHT
     (`rules.py:144,163-171`). `:463-467` does the same for rally families.
  4. `:468-470` sets `tallied[env_ids] = False` again.
  5. Only move-drill episodes are re-killed afterwards (`drill.reset`, `move_drill.py:85-87`).
- **What is wrong:** after any reset (time-out or fall) the env has a live, untallied feeder ball. `PairCourts` believes
  the env is parked (`pairs.py:71`) and `handed` keeps its stale value. Two consequences:
  - The court restarts when both envs look idle. If the feeder ball goes to the partner and the partner makes contact
    before this extra ball has ended (likely: the ball is launched at the reset and the partner's contact comes about
    1.4-1.7 s later), the env "receives" while untallied. `_credit_early` (`return_stand.py:1029-1040`, called at `:987`)
    then pays a legal return: `return_now`, so legal_return +5, the rally bonus and streak +1. This happens whether or
    not the robot hit the ball.
  - `_credit_partner` (`:1042-1046`) can also pay the partner +3 when the stale `handed` is True.
  - Separately, the extra ball's outcome is tallied in the per-feed and per-family counts.
  - Because `init_at_random_ep_len=True` (mjlab `scripts/train.py:176`), pairs are out of sync, so a reset often lands
    while the partner is idle or mid-rally.
- **Evidence:** code order as above. `shadow_swing` pays a small non-zero reward (Episode_Reward 0.0017/s in
  lrsweep-1e-4). It could only do so if the "parked" ghost ball at a reset actually flies, which agrees.
  No test covers this. `tests/test_stage5f.py` exercises `PairCourts.on_reset` in isolation, and the D-136 test calls
  `_credit_early` directly.
- **Size:**
  - Not measured. At most about one spurious credit per robot episode (30 s). For comparison, the policy earns about
    3.8 real legal returns per episode (0.64/s legal_return reward / 5 x 29 s).
  - Effect on learning: reward noise uncorrelated with the action (the critic can partly predict it from the
    post-reset state), plus contaminated counts.
  - Effect on evaluations: small. The 120 s reads reset only on falls.
  - Not specific to left or back.
- **Confidence:** high that the code behaves this way; the frequency is unknown.
- **Cheap verification:** in a 4-env pair-mode instance of this task, call `env.reset()` and check
  `t.rules.dead[~t.drill.move_ep]`: by the comment it should be all True; I expect False. Then count `early` events with
  `env.episode_length_buf < 150` over 60 s of the training config.
- **Fix candidate:** move the pair block after `begin_from_feed` and the flag reset, or re-apply `rules.lost` and
  `tallied` there.

### F3 (MEDIUM). The pace ceiling conflicts with the keep-alive target it sits beside

- **Where:**
  - `ball_out_over` at `return_stand.py:1287-1297`, weight -25 (`tasks/__init__.py:2071`), so -0.5 per contact at
    full penalty;
  - keep-alive box `planner.py:170-186`: landing x 4.7-5.7, |y| <= 1, flight 1.3-1.5 s, weight 2/step_dt, so +2 at a
    full score.
- **Evidence:**
  - `pace.py` uses the drag model of `ball_sim.flight_rk4`, spin-free, contact height 1.0 m, target the box centre
    (5.2, 0). Outgoing speed needed:

    | contact x | 1.3 s | 1.4 s | 1.5 s |
    |---|---:|---:|---:|
    | -4.5 | 10.7 m/s | 10.6 m/s | 10.6 m/s |
    | -5.6 | 11.7 m/s | 11.5 m/s | 11.4 m/s |
    | -7.85 | 13-14 m/s | 13-14 m/s | 13-14 m/s |

    These give pace penalties of 0.53-0.59, 0.93-1.0 and 1.0 respectively. No keep-alive return from the baseline area
    stays under 9.5 m/s.
  - The pairs read (`lrsweep-1e-4-early-pairs.json`, contact_diagnostics):
    - ball_out_speed_mean 10.07 m/s;
    - landing_x_mean 3.93 (box starts at 4.7; score > 0 only beyond 3.7);
    - keep_alive_box share 14.4 %, keep_alive_score_mean 0.33.
- **Effect:** the two terms pull against each other on every return. The pace term behaves like a near-constant tax of
  roughly -0.25 to -0.5 per legal contact, and pushes returns short. It does not specifically explain the left gap.
  For back balls the deep contact makes both the keep-alive box and the ceiling harder, but the penalty is already
  saturated from the baseline.
- **Confidence:** high for the conflict, medium for how much it costs.
- **Cheap verification:** log `|hit_out_vel|` against `keep_alive_now` at legal landings in any read. Or note that
  D-145's threshold (9.5) sits below the speed the box needs (about 10.5 m/s minimum from x = -4.5).

### F4 (MEDIUM-LOW). `stance_progress` (weight 1.0) still rewards motion toward a stale, unobserved spot

- **Where:**
  - term at `return_stand.py:1221-1235`;
  - `stance_xy` is written only by the planner (`:798`) or the off-by-default hint path (`:763`). It is never reset
    at an episode reset.
  - The term is active on every un-hinted feed before the hit: court feeds (80 % of feeder balls, and 80 % of
    hand-offs, since `court_feed` is drawn for received balls too), and the first 0.1 s of planner feeds.
- **Status:** known (D-142, rally run 6 removed it and "did not help"), but it is still in the current chain:
  - added at `tasks/__init__.py:634`;
  - only the NoStance task zeroes it.
- **Evidence:**
  - Episode_Reward/stance_progress is -0.0148/s (lrsweep-1e-4): the robot on average moves away from the stale spot.
    That is small next to spot_progress (+0.256/s).
  - Per step it is up to +-0.02, unobservable to the actor and the critic. That is pure variance.
- **Confidence:** high that the term behaves like this; low that it matters much.
- **Cheap verification:** none needed. If kept, either reset `stance_xy` to the pelvis at each feed, or gate the term
  on `plan_on & ~court_feed`.

### F5 (LOW). Swing episodes are dead in pair mode after one ghost ball

- **Where:**
  - swing episodes are `busy` (`return_stand.py:978-984`), so they never receive and are never fed (`pairs.py:116-139`);
  - shadow swing refeeds through `refeed_timer` (`shadow_swing.py:221`), which pair mode never reads
    (`return_stand.py:975-999`).
- **Effect:** about 5 % of robot episodes (swing_prob 0.05, kept after move_prob 0.35) get one ghost ball (live only
  because of F2), then about 26 s with no task beyond posture and the recovery spot. Wasted samples, no bias.
- **Confidence:** high.
- **Cheap verification:** count `shadow.closed & swing_ep` envs and the time since the close.

### F6 (LOW). The ball term's own seed is always 0 in training; three generators share one seed offset

- **Where:**
  - `BallPhysicsActionCfg.seed = 0` (`return_stand.py:91`, `:1465`); mjlab `train` sets only `cfg.env.seed`;
  - the evaluation scripts do set `b.seed`.
  - `gen_court` (`:313`), `gen_plan` (`:322`) and `MoveDrill.gen` (`move_drill.py:59`) all use seed + 271829;
  - `gen_replay` (`:369`) and `ShadowSwing.gen` (`shadow_swing.py:126`) share seed + 314159.
- **Effect:**
  - Every training run starts the same feed, court-feed, planner-noise and move-spot streams, whatever
    `--agent.seed` is. They diverge only through behaviour.
  - The shared-seed generators produce the same underlying sequence at different offsets.
  - Harmless for learning; it weakens "different seed" claims between runs.
- **Confidence:** high.

### F7 (LOW / info). The fall penalty of D-063 is not in this chain

- **Where:** `_latent_drill3_lp` builds on `_latent_drill3_footwork` (`tasks/__init__.py:669-672`), not on `_fallpen`
  (`:650-655`). The TensorBoard rewards have no `fall` term.
- **Effect:**
  - A fall only ends the episode with a zero bootstrap. With about +2.9/s of positive reward that is still an implicit
    penalty.
  - Training resets are about 7 % falls (fell_over 0.64 vs time_out 8.07 in lrsweep-1e-4).
  - This was a choice at D-066 (run 10's task), not a slip. Listed so it is not mistaken for present.

---

## Suspicions and design tensions (not bugs)

### S1 (MEDIUM, "back"). The planner's "top" rule puts deep-ball stances far behind the baseline, where nothing else trains the robot to go

- **Where:**
  - interception at the ball's rise through `HINT_TOP_Z = 1.1` m after the bounce (`planner.py:84-93`,
    `shadow_swing.py:44`);
  - stance 0.3 m further back; box down to x = -8.5 (`HINT_BOX_V2`).
- **Evidence (`feed_geom.py`):**
  - reach_deep, whose aim is always clamped to -7.5 (see F9), bounces at x = -6.39 (p10-p90 -6.45..-6.34);
  - its planner stance is about x = -8.15, a median 2.55 m behind a robot at -5.6, needing about 1.55 m/s backwards
    in 1.64 s;
  - a legal post-bounce contact at waist height is available about 1 m earlier.
- **The conflict:**
  - On planner feeds the spot input and `spot_progress` reward that long backward run.
  - The move drill's spots stop at x = -6.4 (`move_drill.py:29`), so backward walking beyond the baseline is never
    practised outside ball feeds.
  - reach_deep legal: 0.41 (pairs read), 0.28 (v2 read, with the planner) and 0.35 (court read).
- **Confidence:** medium.
- **Cheap verification:** in a v2 read, histogram `stance_xy[:, 0]` and the contact x for reach_deep, hits against
  misses.

### S2 (LOW-MEDIUM, "left"). The spot channel means the opposite side for left balls than the frozen base learned

- **The mismatch:**
  - The frozen base `RES_BASE` (s5c-18-merge17) was trained on the court chain with `hint_forehand_only=True`
    (`tasks/__init__.py:576-579`; D-059 "run around the backhand"). For it, a hinted spot always meant a forehand
    stance (pelvis 0.5 m to the ball's left).
  - The drill v2 planner (`planner.py:139-147`) uses a backhand stance (pelvis 0.4 m to the ball's right) whenever the
    ball is left of the pelvis.
  - So on planner feeds of left balls, the base's input points about 0.9 m to the other side of what it was trained
    on. The residual must undo this, against `residual_prior_nll`.
- **Reach:** only planner feeds (20 % of feeder balls, about 20 % of hand-offs). The left gap also shows in reads with
  no spot, so this is not the main cause.

### S3 (design). The residual penalty charges exactly the deviation that left/back balls need

- **Facts:**
  - `residual_prior_nll` (-0.05, `latent_reach.py:450-459`, set at `tasks/__init__.py:1009`) is -0.46/s on average.
    That is 72 % of the legal_return income (0.64/s).
  - It is 3x heavier in move-drill episodes.
  - It penalises distance from a base that D-154 itself describes as "trained without footwork".
- **Status:** intended, but it is a direct brake on the left/back residual. Worth a dose check, for example 3x off in
  move episodes, or a lower weight.

### S4 (LOW). Hand-offs hit from very deep are lost at once in the receiver's env

- **Where:** the receiver loses a ball beyond x > HALF_LENGTH + 2.0 = 8.71 (`return_stand.py:942-943`), but the hitter
  may play down to x = -9.21 (lost_back_margin 2.5).
- **Effect:** a contact behind x = -8.71 is an instant receiver miss. Probably rare: the planner box stops at -8.5.

---

## F9 (LOW). Feed clamps collapse two families to near-constants

- reach_deep's aim (-8.0..-7.6) is below `BOUNCE_AIM_MIN = -7.5` for every start-anchored feed (`feeds.py:49,58`,
  `return_stand.py:737`). The aim is therefore always exactly -7.5, and the bounce lands in a 10 cm band (simulated).
- cross_backhand (0.35 + 2.5..4.0) clamps at y = 2.898 in 97 % of feeds; cross_forehand clamps in about 50 %.
  Both lands stay in (vy = 0, so no drift).
- **Effect:** little variety in those families. Not a correctness bug.

---

## Checked and found correct

- **Reward scaling:** mjlab multiplies by step_dt (0.02), and every one-shot term is divided by step_dt in its weight.
  Effective per-event values:

  | term | per event |
  |---|---:|
  | paddle_contact | 1 |
  | legal_return | 5 |
  | keep_alive | 2 |
  | net_clearance | 1 |
  | rally_bonus | 2.5 x streak/10 |
  | partner_return (150 x 0.02) | 3 |
  | ball_out_over | -0.5 |
  | move_arrival | 2 |
  | shadow_swing | 3 |

- **Reward order and flags:**
  - `legal_return` is the last term and clears the step flags; every flag reader comes before it.
  - The zero-weight `placement` is skipped by mjlab (`reward_manager.py:122`), which is harmless.
  - `move_arrival` and `shadow_swing` clear their own flags.
- **Frames and sides:**
  - `_rotate_inv` is R^T v; the yaw formulas are correct.
  - The body frame has +y left. Families are signed with the robot's right at -y.
  - The planner and stance spots choose forehand when the ball is at or right of the pelvis, with the offsets on the
    correct sides.
- **Mirroring:** the hand-off mirror is a 180-degree rotation about z: (x, y, vx, vy, wx, wy) are negated, z, vz and wz
  kept. That is correct for the spin pseudo-vector.
- **Paddle contact:** the paddle is a two-sided box (closest point; `ball_sim.py:208-246`), so backhand contacts on the
  back face work. Body-contact and lost-ball rules are symmetric in y.
- **Observations:**
  - no observation clipping, no action clipping (`clip_actions` None);
  - ball noise is drawn once per control step and shared across the three ball terms, with the critic exact;
  - lags are 0 in this "Clean" task, set by the second `_sim2real` call;
  - no right/left asymmetry in any observation term.
- **Terminations:**
  - `fell_over` (70 degrees) and `blew_up` are terminal; `time_out` is a truncation and is bootstrapped
    (`vecenv_wrapper.py:83`).
  - No position-based termination, so nothing fires on backward steps.
- **No curricula are active:**
  - LP, adaptive and reach are off in drill v2 settings;
  - drill v2 failure weighting is off;
  - the terrain and command curricula are removed.
- **Domain randomisation:** foot friction, encoder bias and torso COM. Push events are removed. Nothing is
  direction-specific.
- **Feed mix:** the gated foot-quality terms are symmetric. The Weak mix reaches court feeds as intended. Left-side
  families are about 28 % of court-feed weight in the back zone, so they are not under-sampled.
- **`_refeed`:** it runs `_feed` for all envs every physics step and restores every non-fired field, ball state
  included. No leaks found.
- **Env-var switches:** the training scripts set only optimizer and runner variables. `PICKLEBOT_RES_BASE`,
  `PICKLEBOT_CONTROLLER`, `PICKLEBOT_LEG_R` and `PICKLEBOT_TEACHER` would act silently at import, but they are not set
  in the rally run scripts.

## Suggested order

1. F1 verification read (one GPU read; it can change how the left gap is interpreted).
2. F2 fix (small code change plus a test). Re-measure nothing old: F2 hardly touches 120 s reads.
3. Decide on F3: raise v0 to about 11.5 m/s, or drop the term. Then on S1 (planner contact height for deep balls, and
   move-drill spots behind the baseline).
