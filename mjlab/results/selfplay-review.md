# Rally target: panel rounds (D-134 onward; charter docs/PANEL.md)

## Round 21 - the new target; the hand-off; run 1 (2026-10-21)

**Brief:** the user's target is frozen in `rally-target.md`: 80 % of rallies reach 5 good robot-to-robot shots (about 96 % per shot). The start point is Stage 5H run 4: about 12.7 % per shot on the partner's balls, P(4+) 0.65 %, falls 3.85 % per episode. The R4 protocol hands a return to the partner at the net crossing.

**Correction check (5/5):**
- The crossing hand-off hides the first 0.55-0.9 s of the partner's shot. A real opponent's ball is seen from the paddle, so the read is pessimistic and training sees the wrong thing. Fix it before the first read, behind a flag, with tests.
- Court main >= 76.8 % was the Stage 5F/5H readiness rule. For this target it becomes a relative guard (no more than 5 points below the parent), not an absolute kill line.
- The R2 read with no refeed delay (29.9 %) matched the 0.5 s read, so recovery time is not the gap.

**Votes:**

| Question | Result |
|---|---|
| The contact hand-off, in reads and in training | 5/5 |
| Run 1 = continued pair self-play with the contact hand-off, parent run 4's endpoint, 900 iterations | 5/5 |
| Run 2 = softer shots (higher keep-alive weight) | 4/5 (RL: a rally-length reward first) |
| Feeder distribution frozen as the target's protocol | 5/5 (coach: feeder-ball legal caps P(5+) and must reach about 90 %) |
| Stop rules in D-135 | 5/5 |

**Code:**
- `pairs.py`: `handoff` flag, a `waiting` mask (the partner's ball, not yet touched) and `p_len_ge_5`.
- `return_stand.py`: `pair_handoff` passes the legal first contact to the pair logic.
- `stage2_eval.py`: `--pair-handoff`.
- Tests:
  - the contact hand-off receives on contact and charges faults to the hitter;
  - crossing is unchanged;
  - the run 1 task differs from run 4's only in the hand-off.

**The panel's note for the user:** 96 % per shot is far from 13 %. It will likely need runs over 2 h or a bigger controller. The stop rules in D-135 bring that question back with evidence.

## Round 22 - the baseline under the contact hand-off (a surprise check, 2026-10-21)

**Brief:** in the contact read, own-ball legal rose from 13.1 % to 19.2 %. Feeder-ball legal fell from 76.5 % to 64.7 %, and falls per shot rose from 0.8 % to about 3.2 %. A stalled-court bug in the first contact read was fixed and the read was redone (`selfplay.md`).

**Correction check (5/5):**
- The fix keeps every count rule of D-135; it only lets a stalled court restart. Rally counts now match the crossing read.
- The feeder drop is a behaviour effect, not a count error: feeder balls are counted the same way in both modes. The motion and RL members' reading: the parent never saw a ball leave the far paddle, so it reacts badly, sometimes falls, and is out of position for the next feeder ball.

**Votes:**

| Question | Result |
|---|---|
| Launch run 1 unchanged (training with the contact hand-off is the planned answer) | 5/5 |
| Kill lines stay relative to the parent's early reads on the same seeds | 5/5 |

**Coach:** feeder-ball legal (64.7 %) now caps P(5+) harder. Even at 96 % on the partner's shots, P(5+) would be at most 0.647 x 0.96^4, about 55 %. Report it every read.

## Round 23 - run 1 killed; reachability (2026-10-21)

**Brief:** run 1 (training with the contact hand-off) was killed at 33 %. Own-ball legal fell from 18.3 % to 14.2 % (the intervals do not overlap), and move arrival from 86.1 % to 74.3 %. The question: is the target reachable within 2 h runs?

**Correction check:**
- The kill is right (5/5).
- **Architecture** found a training-side bug: a return the partner volleyed before it landed was counted legal but never rewarded. It hit every volleyed return under the contact hand-off. Fixed and tested (D-136).
- **RL:** a hidden second change. The court share was set from crossing hand-offs, so court feeds fell below 40 % with contact.
- **Experiment design:**
  - The Wilson intervals ignore clustering by court, so later gates should use court-level bootstrap intervals.
  - Faults excluded on the same step should be counted against hitter faults.
- **Motion:** the contact refeed also moves when the receiver's stance and recovery targets are set.

None of these would lift 19 % per shot to 96 %.

**Votes: back to the user, 5/5.**
- Slope: about 2 points per run, so more than 20-40 runs.
- Feeder-ball cap: P(5+) at most about 55 %.
- Falls per shot cap P(5+) too.
- Run 1 went backwards.
- D-135's stop rules fired. The remedies are the user's hard stops (runs over 2 h, a bigger controller).

**Options, by member:**

| Option | Who favours it |
|---|---|
| Cooperative reward (pay the hitter when the partner returns its ball, drop the pace term, recalibrate the court share) with longer runs (4-8 h) | RL (first), coach, architecture |
| An added intermediate milestone (partner-ball legal >= 50 %, feeder-ball >= 85 %, then P(3+) >= 50 %); the 80 % bar stays | coach, experiment design, architecture |
| Footwork first (arrival >= 95 % in every direction, falls < 1 % per shot) | motion (first) |
| A bigger controller (teacher, then distilled student) | all: last, no evidence that capacity is the limit |

## Round 24 - the user's answer; rally run 2 (2026-10-21)

**Brief:** the user approved a cooperative reward plus an intermediate milestone, and longer runs (cap 6 h). The draft M1 was partner-ball >= 50 % and feeder-ball >= 85 %.

**Correction check:**
- Round 23's "pace term" does not exist in the pair task. The competitive pull is placement: up to 150 for a landing 1.6 m to one side, against keep-alive's 100 for a centred ball. It sends the partner to its weakest directions (left and fwd-left, about 87 % arrival).
- **Architecture:** `targets=False` would drop observation columns and break the parent load, so use placement weight 0.
- **Experiment design:** the 2 h cap was a PANEL.md rule. D-137 names the changed premise (the user's approval).

**Votes:**

| Question | Result |
|---|---|
| Run 2 = cooperative credit (placement 0 + partner_return), one change | 5/5 |
| partner_return weight | 150 (coach, motion, RL) vs 250 (experiment design, architecture): 150 |
| When it pays | at the partner's legal return (coach, motion, experiment design, architecture) vs the partner's contact (RL): legal return |
| Court share corrected as a fix of run 1's hidden change | 5/5 (measured: hand-offs 49.97 % of feeds started, so 0.80) |
| M1 adds sides within 3 points | 4/5 |
| M1 uses court-cluster bootstrap lower bounds | 3/5 (RL, experiment design, motion) |
| M1 read once at a fixed endpoint | experiment design, unopposed |

**Not adopted (one member each):**
- falls per shot <= 2 % and arrival >= parent as M1 bars (motion): reported instead;
- a 10 % footwork tripwire (motion);
- a 63 % stop check (experiment design).

**The RL member's timing point,** answered: under the contact hand-off, the hitter already holds the partner's return in view when the credit lands, so it is not a parked, ball-free state.

**Experiment design's caution:** run 2 = run 1 corrected + cooperative credit. Its gain is not credited to the credit alone.

## Round 25 - run 2's endpoint; run 3 (2026-10-22)

**Brief:** run 2 passed M1's partner-ball item (54.3 %) but not feeder-ball (75.8-77.0 %, bar 85 %). P(5+) is 7.9 %. The curve was still rising at the 6 h cap. Forward move arrival fell to 65-72 %.

**Correction check:**
- The read is right (5/5).
- **Experiment design:** the M1 table must state the D-138 number (75.8 %).
- **Experiment design:** the forgetting guard was broken at the endpoint (fwd-left 65 % against 84.8 %); the guard only ran at the early check.
- **Experiment design:** about 4 points of the feeder gap are pair state (crossing read 80.2 % against contact 75.8 % on the same model).
- **Architecture:** the per-family table mixed in partner balls with random labels. Fixed: feeder balls only.
- **Everyone:** the rest of the gap is reach. Legal given contact is about 92 %, so the misses are mostly no contact, at the court ceiling of about 77 %.

**Votes:**

| Question | Result |
|---|---|
| Run 3 | (a) continue unchanged: RL, architecture; (c) footwork rehearsal: experiment design, motion; (b) higher court share: coach. The tie goes to least new code: **(a)** |
| Interim video | 4/5 yes (experiment design: no; videos only at milestones, and the longest rally is cherry-picked). Both clips are chosen before rendering, one of them unpicked |

**Forecasts:**
- RL and architecture: feeder-ball ends around 77-81 %, so M1 is unlikely from continuation alone.
- **The next lever if it stalls:** footwork rehearsal (`move_prob` / `move_sector_weights`, weighted toward the forward directions), or the court-family mix (`COURT_MIX`) toward the weak families.

**Motion:** a training-free reach check against the controller's speed envelope would tell whether 85 % is physically reachable. If it is not, the next decision is a controller change, which is the user's call.

## Round 26 - run 3's endpoint; the drill-episode bug; run 4 (2026-10-22)

**Brief:** run 3 ended with feeder-ball legal at 77.9 % (M1 not met). The move-drill pair bug is confirmed: 38 % of balls went to robots in move episodes.

**Correction check:**
- The bug reading and the fix are right (5/5).
- **Architecture:** the feeds also overwrote the move spot. Swing episodes stalled their court, so they are now busy too.
- **Motion:** idle swing episodes are the cost. Re-measured: 0 balls to busy robots, with feeder balls up 5 % because stalls are gone.
- **Experiment design:** the footwork link is a hypothesis, not a claim.

**Votes:** see D-140.
- Run 4 = the fix only (5/5).
- Correction against change (3/2).
- No court-share retune (4/1).

**Lined up:** a feeder family mix toward the weak families, after a reach check.

## Round 27 - run 4's endpoint; run 5 (2026-10-22)

**Brief:** run 4 ended with feeder-ball legal at 80.2 % (M1 not met, trigger fired), partner-ball at 53.9 %, and footwork restored (all directions 95.7 % or more). A training-free reach check found a backhand stroke gap, not a reach limit.

**Correction check (5/5):**
- The reads are right. The partner-ball drop (2 points) is about 1.5 times the seed-to-seed swing: likely a cost of fewer hand-offs, not proven. The bar is still met.
- The reach model is conservative: a ranking, not a ceiling.

**Votes:**
- Run 5 = a weighted court-feed family mix, on a new task (5/5).
- The weights are the per-family median of the five proposals (D-141).
- The kill lines blend the majority positions (D-141).

**Pre-launch read** (training conditions, rally-04 model_12100; `rally-05-precheck-{even,weak}.json`): realised feeder-ball family shares, even mix against weak mix:

| Family | Even | Weak |
|---|---|---|
| backhand | 6.3 % | 9.2 % |
| fast | 5.4 % | 9.1 % |
| cross_backhand | 5.1 % | 8.3 % |
| reach_backhand | 5.6 % | 7.7 % |
| high | 6.6 % | 3.9 % |
| reach_forehand | 5.6 % | 3.5 % |
| short | 5.4 % | 4.4 % |
| reach_deep | 5.2 % | 5.6 % (little moved) |
| drop | 5.2 % | 5.8 % (little moved) |
| low | 6.8 % | 6.8 % (zone filter and drill v2 dilute these) |

- Balls to busy robots: 0 in both.
- Hand-offs 2,681 against 2,579.

## Round 28 - run 5's endpoint; the trend; run 6, then the user (2026-10-23)

**Brief:** run 5 reached 81.9 % feeder-ball legal (M1 not met) and 55.2 % partner-ball legal, which is flat for four runs. The question: is the target reachable, and is one more run worth it?

**Correction check:**
- The reads are right (5/5).
- **Experiment design:** the final target needs about 97 % per partner shot with feeder-ball at about 90 % (P(5+) = feeder x q^4). By shot position, partner-ball legal is 46, 54, 66, 68, 68 %.
- **Architecture:** a stale footwork reward (stance_progress) on court feeds and hand-offs, verified (D-142).
- **Motion and coach:** low readiness at the partner's launch, and one hard, deep shot for every return.

**Votes:**
- **Reachability (5/5):** M1 is 1-2 runs away; M2 and the final target are out of reach within the rules.
- **Run 6:** first 4/5 run 5 unchanged (architecture: the fix); then a follow-up once the bug was verified, 5/5 for the fix as the one change.
- **Back to the user after run 6, whatever the result** (coach, motion, RL, architecture; experiment design accepts it in place of a two-run budget).

## Round 29 - the user's answer; the partner-ball run (2026-10-23)

**Brief:**
- The user asked for a vote and to press on with the loop, "do what you have to do".
- The panel's earlier read: partner balls are the blocker (flat at 52-56 %); contact about 67 %, legal given contact about 90 %.

**Correction check:**
- **RL and experiment design:** the next-shot rates by position are survival-conditioned, so the first-partner-ball deficit is overstated.
- **Architecture:** ready_reward fires on hand-offs (fire includes recv before ready.launch).
- **Motion:** watch for bobbing to farm the dip score.
- **Experiment design:** run 6's -3.1 points is about twice the seed swing, a probable regression.

**Votes:**
- **Before the premise read:** (b) readiness: RL, motion, coach; (a) keep_alive x2: architecture, experiment design.
- **Both sides pre-registered a premise read.** It found readiness makes no difference (-0.7 points of contact), and the partner's fastest third of shots is reached 44 % of the time against 74-76 % (D-144).
- **Result:** (a) 5/5 by the pre-registered rules.

**Next if it stalls:** run 8 = (b) or a ball-out speed ceiling; then the user (controller or runs over 6 h).


## Round 30 - run 7 killed; run 8 (2026-10-23)

**Brief:** run 7 (keep_alive x2) was killed at the early check: partner-ball legal 55.3 -> 47.8 %, ball out 10.54 -> 10.81 m/s, landings deeper.

**Correction check (5/5):** the kill is right. The keep-alive box does not steer pace; it paid for deeper, faster balls. Experiment design: the drop is about 5 times the seed swing and the mechanism did engage, so it is a real regression; pace is the leading cause, still confounded with depth. The ready reward is out (the premise read found no readiness effect).

**Votes (all (a), a ball-out speed ceiling at the first legal contact):**

| Member | Ramp | Weight |
|---|---|---|
| Motion | 9 -> 12 m/s | -50 |
| Coach | 10 -> 12 m/s | -50 |
| RL | 10.5 -> 12.5 m/s (hinge) | up to -100 |
| Experiment design | 9.5 -> 11.5 m/s | -50 |
| Architecture | 9 -> 12 m/s | -50 |

- **Weight -50:** 4/5. **Ramp:** no majority; same code, so experiment design's 9.5 -> 11.5 m/s by the tie rule.
- **Kill lines:** experiment design's (a manipulation check on the mean ball out or the share above 11 m/s; contact guards against an escape into the net or into skipped contacts), plus run 7's lines unchanged.
- **If it stalls:** back to the user (5/5).

Run 8 = D-145.

## Round 31 - run 8 killed on the feeder line; back to the user (2026-10-24)

**Brief:** run 8 (the pace ceiling) engaged strongly (ball out 10.54 -> 9.95 m/s; share above 11 m/s 34.7 -> 14.4 %). Partner-ball legal rose 54.2 -> 64.7 % and P(5+) 8.4 -> 13.9 %, but feeder-ball legal fell 81.2 -> 78.4 %, below the 79.2 % line, so the run was killed.

**Correction check (5/5):**
- The kill is right by the rules. Experiment design's court bootstrap of the difference gives -2.8 points (95 % interval -3.6 to -2.0): real, not noise.
- **RL and experiment design, a planning error:** run 8 aimed at partner-ball legal, whose M1 bar (50 %) was already met. The M1 blocker is feeder-ball legal (85 %), and nothing aimed at it.
- **Likely cause (RL, motion, architecture, experiment design):** the -50 penalty cancels the +50 contact reward on hard, deep and reach feeds, whose returns come off fast whatever the swing. Paddle speed fell everywhere (6.55 -> 6.34 m/s), and second-bounce endings rose (8,525 -> 11,122). Repositioning for shorter partner balls is a possible second cause: the court drill lost only 1.3 points of contact.
- **Coach's option (a ramp from the larger of 9.5 m/s and the incoming speed) is close to a no-op:** the mean incoming speed at contact is 3.9-4.1 m/s, so the ramp would almost always still start at 9.5 m/s.

**Options to put to the user (first choices):**

| Option | First choice |
|---|---|
| Ceiling on returns of partner balls only (`pairs.handed` gate; about 3 lines) | RL, architecture, experiment design |
| Weight -25 | motion |
| Charge only the added pace | coach |

- **Second choice:** the controller option (RL, coach, experiment design; motion and architecture third).
- **A run over 6 h:** last for four members. Architecture ranks it second, to test an early-training transient.

**Recommendation to the user (majority):**
1. Run 9 = the ceiling on partner-ball returns only, from rally-05 model_15000, kill lines of D-145 unchanged. Additions: kill if any feeder family loses more than 5 points of contact (experiment design). Endpoint success also needs feeder-ball legal at or above the parent (experiment design; RL: parent + 2).
2. The controller option.
3. A longer run.

Waiting for the user (D-145: no run 9 without the user).

**Addendum (2026-10-24):** the user answered: press on with the panel's decisions, no 6 h cap, back to the user only at the target or a panel stop vote (D-147). So run 9 = the majority first choice, the ceiling on partner-ball returns only, with experiment design's added family guard (D-148).

## Round 32 - run 9 killed (no engagement); run 10 (2026-10-24)

**Brief:** run 9 (the ceiling on partner-ball returns only) did not engage. Ball out stayed at 10.56 m/s and the share above 11 m/s rose 35.4 -> 36.8 %. In training the gated term was about 5 times weaker than run 8's (-0.009 against -0.046).

**Correction check (5/5):**
- The kill is right. The code worked, but the premise was wrong. Partner balls are a small share of training balls, and the policy cannot see which kind it is playing, so the gate only diluted the signal.
- **Experiment design:** run 9 doubles as a null run from the same parent (feeder -0.4, partner -2.7). So run 8's +10.5 / -2.8 is a real effect with a real cost.
- **Architecture, our own miss:** run 9's smoke already showed a small term. From now on, the smoke compares a new term's size with its parent's before launch.

**Votes:**

| Member | Option | Length |
|---|---|---|
| Motion | (a) run 8's ceiling at -25 | 6,400 iterations |
| RL | (a) | 3,200 |
| Experiment design | (a) | 6,400 |
| Coach | (b) ramp 10.5-12.5 m/s at -50 | 4,500 |
| Architecture | (b) | 3,200 |

- **Run 10 = (a), 3/5.** At -25, every contact still nets at least +25 on hard feeds.
- **Length:** no majority. Both forms are the same code, so the tie goes to experiment design: 6,400 iterations, early check at model_16900.
- **Not stopping (5/5).**
- **RL, experiment design, architecture:** no pace ceiling can lift feeder-ball legal to 85 % on its own. After run 10, the panel must name a lever aimed at feeder balls. Experiment design pre-registered that if run 10 and the next run both end with feeder-ball legal at or below 81.9 %, the next step is the controller option or a stop vote.

## Round 33 - run 10's endpoint; run 11 aimed at feeder balls (2026-10-24)

**Brief:** run 10 ended at partner-ball 63.1 %, feeder-ball 80.1 % (missed its 81.9 % line) and P(5+) 13.3 % (best yet). Feeder misses concentrate in reach_deep, cross_backhand and fast (38 % of 4,655).

**Correction check (5/5):**
- The run was fair and its miss is real (run 9's null drift was -0.4).
- The pace ceiling still taxes hard feeds, whose returns come off fast whatever the swing (fast contact 78 -> 71 %, reach_deep 57 -> 52 %).
- **Motion and coach:** the backhand-side gap is a skill gap (10-30 points behind the forehand mirrors at similar walking speeds). reach_deep and fast need a walk above the 1.5 m/s model cap: a likely controller limit. Both estimate that closing the backhand gap alone falls short of the 1,150 misses M1 needs.
- **Architecture:** court_feed_prob is already 0.80, so option (b) has little room.

**Votes:**

| Member | Option | Form | Parent | Length |
|---|---|---|---|---|
| RL | (c) | +50 on contact with feeder balls of reach_deep / fast / cross_backhand | run 10 | 3,200 |
| Motion | (c) | +50 on legal feeder-ball returns of 5 families | run 10 | 6,400 |
| Architecture | (c) | +125 on legal feeder-ball returns of 5 families | run 10 | 6,400 |
| Coach | (a) | heavier weak-family mix (reach_deep 3, cross_backhand 3, fast 2.5, ...) | run 10 | 6,400 |
| Experiment design | (a) | reach_deep / cross_backhand / fast weights to 3.0 | run 10 | 6,400 |

- **Run 11 = (c), 3/5:** a one-shot bonus on a legal return of a feeder ball (pairs gate) of reach_deep, cross_backhand, fast, reach_backhand or backhand (2 of the 3 (c) votes for the five families and for legal returns).
- **Weight +50:** the size two (c) voters named. The +125 had one vote; the tie rule would go to experiment design, who voted (a).
- **Parent:** run 10's model_21399, 5/5.
- **Length:** 6,400 iterations, 4/5.
- **Kill lines:** D-145's and D-148's unchanged, without the pace engagement check (the parent already has the ceiling). Added (architecture): kill if the five families' feeder-ball legal is not up at the early check. **Success:** experiment design's bar.
- **Not stopping (5/5).** Under D-149, if run 11 also ends with feeder-ball legal at or below 81.9 %, the next step is the controller option (coach, motion, RL, architecture) or a stop vote.

## Round 34 - run 11 killed; D-149 fires: the controller option or stop (2026-10-25)

**Brief:** run 11's feeder bonus did not move its five families (64.6 -> 64.3 %). Feeder-ball legal has been flat at 77-82 % for eleven runs. D-149: the controller option or a stop vote.

**Correction check (RL, experiment design, motion, architecture):**
- The "1.5 m/s cap" behind "reach_deep needs 2.35 m/s" is the planner's assumed walking speed (`planner.WALK_CAP`). The controller's top speed has never been measured, so "controller limit" is an inference.
- The reach model is conservative: 12 % of reach_deep feeds need 1.5 m/s or less, yet 45 % are returned.
- **Motion now doubts the backhand-skill reading:** the Stage 5C agility runs found the latent controller barely steps left or back, the directions that backhand-side and deep balls need.
- **Coach:** D-127 showed that stroke execution is also on the controller side.
- **Architecture:** the decoder is frozen inside the environment. Unfreezing it (e2) is about 300 lines plus checkpoint surgery, and it breaks the frozen base executor. A cheap e2 exists: give the residual joint-space control of the 12 leg joints, as with the wrist (about 40 lines).

**Votes:**

| Member | Vote |
|---|---|
| RL | e1, then e2 or e4 by the measured top speed |
| Experiment design | e1 (commanded walks at 1.5-3.0 m/s), then a walk_cap run or e2 |
| Motion | e1 (per-direction envelope against run 10's misses), then e2 if 50 % or more of misses lie outside it |
| Architecture | e1 (per-feed peak pelvis speed and closest distance in the M1 loop), then the cheap e2 |
| Coach | e2 (decoder fine-tune), with e1 as a pre-launch check |

- **No STOP vote (5/5).**
- **e1, 4/5.** No form had a majority, so the tie rule (least new code) gives architecture's form and rule: one script in the M1 loop, no training.
- Motion's per-direction split is reported alongside.

## Round 35 - run 12 killed; run 13 = the leg residual at +-0.3 rad (2026-10-25)

**Brief:** run 12's leg residual (+-0.1 rad) was killed at its early check: reach_deep + fast contact went 63.5 -> 63.2 %. The leg rows were still growing (weight norm 0.11 against 0.28).

**Correction check (5/5): the kill stands (pre-registered), but the test was weak.**
- **Motion:** +-0.1 rad moves the foot about 6-7 cm on a 0.7 m leg; a sidestep needs about 0.3-0.4 rad of hip roll.
- **RL:** the gradient into a 0.1·tanh output is small, and the KL-limited step is shared with a converged base.
- **Architecture:** the leg noise is white each step, and action_rate penalises it although the policy cannot see its last leg action. The -0.3 point change is within GPU read noise (about ±1.4 points).
- **Coach, RL, experiment design:** the engagement line (reach_deep + fast) was a stand-in. The mechanism is direction: left 36 %, back 52 %. fast misses barely run and split left and right.
- **Motion, RL:** part of the left gap is backhand reach or late commitment (reach_backhand misses peak at 1.28 m/s against 1.83 m/s on hits).

**Votes:**

| Member | Option | Range | Leg init std | Length | Engagement line |
|---|---|---|---|---|---|
| Coach | r1 | 0.3 | unchanged | 6,400 | left + back contact up |
| Experiment design | r1 | 0.3 | unchanged | 6,400 | reach_deep + fast up **and** left + back up |
| Architecture | r1 | 0.3 | unchanged; cut if smoke falls rise | 6,400 | unchanged |
| Motion | r1 | 0.3 | about 0.2 | 9,600 | unchanged |
| RL | r1 | 0.3 | about 0.25 | 9,600 | left + back up by 2 points |

**Decided:**
- r1, 5/5. Range 0.3, 5/5. Length 6,400, 3/5.
- Leg init std: unchanged, 3/5, with architecture's smoke condition. Pre-registered before the smoke: cut to 0.25 if the smoke's fell_over is over 2x run 12's. It was 1.87x (0.182 against 0.097), so the std is kept.
- Engagement: both lines, each with a 3/5 majority: reach_deep + fast contact up (experiment design, architecture, motion) and left + back contact up (coach, experiment design, RL; "up", 2 of 3).
- No STOP vote.
- Pre-registered (experiment design, RL): if run 13 fails to engage, the leg-residual route is closed and the panel chooses between e2 proper (decoder fine-tune) and a stop.
- Not more envs (architecture): 16,384 envs gave only +9 % steps per second (D-065), and memory would leave no room for the early reads.

## Round 36 - run 13 killed; the leg-residual route closed; e2 or stop? (2026-10-25)

**Brief:** run 13 (leg residual at +-0.3 rad) was killed at its early check and made things worse almost everywhere: move arrival -17 points, falls 4.5 %, feeder-ball legal 76.9 %, left legal 36.6 -> 30.5 %. Run 12 (+-0.1 rad) did nothing. Under D-153 the panel chose between e2 proper (decoder fine-tune) and a stop.

**Correction check (5/5):**
- Joint-space exploration over a converged latent policy does nothing when small and breaks the gait when wide.
- **Everyone corrected the premise behind D-152:** the decoder can step left and back. Move-drill arrival is 96-99.7 % in all 8 directions, and D-082's floor test found 93 % of the walking teacher's leg actions reproducible.
- The rally gap is committing and moving with a ball under time pressure (reach_backhand misses peak at 1.28 m/s against 1.83 m/s on hits). That is a policy limit, not a decoder limit.
- **So e2 is aimed at the wrong part** (RL, motion, coach, architecture, experiment design). PPO's gradient does not reach a deterministic decoder without joint-space noise (run 13's failure). It also breaks the frozen base and is about 300-400 lines.
- **Experiment design:** run 12's "up" line had no margin; engagement lines need at least +2 points.

**Votes:**

| Member | Vote |
|---|---|
| Experiment design | **STOP** (options for the user: e2 decoder tail with a BC anchor / e4 teacher-student / re-distil H1 / end at run 10) |
| Coach | other: e4-lite, a stance-hint teacher from run 10, then a no-hint DAgger student (about 100 lines) |
| Architecture | other: e4, a privileged-ball teacher (true contact point and time), then distillation (about 140 lines) |
| Motion | other: a leg-only gait anchor to the walking teacher steered to the stance spot (about 15 lines) |
| RL | other: the residual's latent range doubled, lam_r 1 -> 2, std halved (about 10 lines) |

- **Not stopping, 4/5.**
- **No majority on the route,** so the charter's rule (least new code and fewest moving parts) gives RL's lam_r 2. It stays on the decoder's motion manifold, and D-080 and D-090 named the +-1 sigma range as a limit that has never been widened on the rally line.
- **Pre-registered:** RL and experiment design vote STOP if it fails. Coach and architecture's e4 and motion's gait anchor are the standing alternatives.


## Round 37 - run 14 met its success line; run 15 = lam_r 3 (2026-10-26)

**Brief:** run 14 (lam_r 1 -> 2) met its pre-registered success line at model_27798 and is the new best: partner-ball legal 70.5 %, feeder-ball legal 81.9 % (low 81.3 %), P(3+) 31.6 %, P(5+) 18.7 %, left feeder legal 36.2 -> 43.7 %. M1 still needs feeder-ball legal 85 % (about 700 fewer misses).

**Correction check (5/5):**
- Run 14 was carried out right. Its init started at the parent's point (latent noise flat in TensorBoard, 0.229 -> 0.226), and the kill and success lines were applied as written.
- Why it helped where the leg residual did not (all five): a latent move stays on the decoder's motion manifold and comes out as one coordinated step. Joint-space noise is off that manifold: no signal when small (run 12), a broken gait when wide (run 13).
- RL: the prior penalty is counted in prior-sigma units, so the wider range did not make a given move cost more. It lifted the tanh ceiling at 1 sigma, where the converged base had been pinned with a vanishing gradient.
- Experiment design: the feeder line passed exactly at its bar (81.9 against 81.9). The clear wins are partner balls (+7.4), P(5+) (+5.4) and left (+7.5). Run 14 also trained 6,400 more iterations; runs 12-13 trained the same and did not engage, which mostly, not fully, rules out training time.
- Motion: left misses still peak below what the robot can do (1.99 against 2.7 m/s): it under-commits. Back contact rose 65.5 -> 69.4 % but legal stayed flat, so the stroke while moving backwards now limits back.
- Architecture: `lam_r_init.py` keeps the parent only approximately when latent outputs are saturated.

**Votes:**

| Member | Vote |
|---|---|
| RL | **a**, lam_r 3, 9,600 iterations |
| Motion | **a**, lam_r 3, 6,400 iterations (adds a style line at 4.44) |
| Experiment design | **a**, lam_r 3, 6,400 iterations |
| Architecture | **a**, lam_r 3, 6,400 iterations (smoke stop if fell_over > 1.5 x run 14's 0.106) |
| Coach | **b**, run 14 continued for 6,400 iterations (left had not flattened; do not stack a second dose before the first has finished) |

- **Run 15 = (a), 4/5:** lam_r 2 -> 3 from run 14's model_27798 with the latent rows and std scaled by 2/3, 6,400 iterations (3 of 4), early check at model_29700.
- (b) was judged too slow: left rose about 0.6 points per 1,000 iterations after the early check (experiment design, motion, architecture). (c) changes the same tax and risks style. (d) is more code than the evidence needs yet.
- **Lines (majority on each):** early kill = run 14's early-lamr2 lines unchanged (left + back feeder contact up >= 2 points). Success = feeder-ball legal >= 83.9 % with low > 81.9 % (4/5), partner-ball legal >= 68.5 % (4/5), sides within 3 points, falls <= 4 %. Style is reported (motion's style kill line had one vote). Architecture's smoke falls line is applied.
- **Pre-registered:** training time is a confound and is reported (RL). If run 15 fails to engage, lam_r stays at 2 and the panel chooses among run 14 continued (the control: RL, motion), the e4 teacher, and a stop (experiment design).


## Round 38 - run 15 killed; run 16 = the e4 teacher (2026-10-26)

**Brief:** run 15 (lam_r 2 -> 3) was killed at model_29700. Left + back feeder contact went 58.4 -> 54.9 % against a +2 line. Left legal went 45.5 -> 39.6 %. Partner-ball legal (69.7 -> 71.8 %) and P(5+) (17.8 -> 19.2 %) moved inside read noise. Under D-155, lam_r stays at 2, and the panel chose among run 14 continued, the e4 teacher and a stop.

**Correction check (5/5): the kill was right.**
- The drop is outside read noise. Run 14 read twice gave left legal 43.7 and 45.5 %.
- **Why 3 sigma hurt:**
  - the composite latent (base at 3 sigma plus the residual) can now sit up to 6 sigma from the prior mean, off the decoder's training support (architecture, RL);
  - `lam_r_init.py`'s 2/3 scaling is exact only for unsaturated outputs, so the saturated left and back rows started away from the parent (architecture, motion, RL);
  - the effective step size went up 1.5x (RL).
- Motion and coach: the robot committed *less* to left and back balls. Peak speeds fell (left p90 2.38 -> 2.31 m/s), and misses still end about 0.85 m short. It leaned and reached instead of stepping.

**Votes:**

| Member | Vote |
|---|---|
| Experiment design | **d**: teacher with true contact point and time, 6,400 iterations; pre-registered STOP if the teacher's feeder-ball legal ends below 83.9 % |
| Motion | **d**: same form; STOP if the teacher misses 85 % |
| Coach | **d**: same form, then a DAgger student; STOP if the teacher misses 85 % |
| RL | **b**: run 14 continued, 9,600 iterations, engagement check at 50 % |
| Architecture | **b**: the same; withdrew its earlier (d) |

- **Run 16 = (d), 3/5.**
- **Why (b) lost:** run 14's left gain after its early check (about 0.6 points per 1,000 iterations) cannot close M1's 3.1-point feeder gap in any planned length, and a +2 line at 30 % would not test it fairly (experiment design, motion, coach).
- **Correction to RL's and architecture's premise.** Both said the actor already sees the planner's stance spot, so missing information is not the limit. In code, the M1 read's task (`Picklebot-Latent-Court-Res-G1`) has `planner_mode = "off"`. In training, court feeds (80 %) get no planner spot either (D-116). So in the read that counts, the policy must read the ball by itself, and the teacher's premise stands.
- **Headroom read** (reported, no selection; run 14's model_27798 on 4219801):

  | Planner | Feeder legal | Partner legal | P(5+) |
  |---|---|---|---|
  | As trained (off) | 82.0 % | 70.5 % | 18.6 % |
  | Clean spot | 75.9 % | 68.1 % | 15.8 % |

  Turning on a clean stance spot that the policy only ever saw on drill-v2 feeds makes it worse: it walks to the spot. The existing channel is not a free test of information. The planner-off and direction-split reads were stopped as redundant (the task's planner is already off).

**Form (D-156):**
- Run 14's task plus a trailing 5-dimensional actor input on every live feed, planned from the ball's true state and spin when the feed starts or the partner's ball arrives. Not tied to the planner. The input:
  - the contact point relative to the pelvis in the body frame;
  - its height;
  - the time to contact;
  - an on flag.
- The frozen base reads only its own 124 inputs.
- The parent is run 14's model_27798 with five zero input columns (`scripts/expand_checkpoint.py`), so it starts exactly at the parent.
- Training seed 94, 6,400 iterations.
- Early kill at model_29700 on run 14's lines.

**Teacher gate (pre-registered, read once at the endpoint):**
- feeder-ball legal >= 85 % with a low >= 84 %;
- partner-ball legal >= 68.5 %;
- sides within 3 points, falls <= 4 %.

**After the gate:**
- **Pass:** the DAgger student is built (about 130-200 lines), and M1 is claimed only from the student, on fresh seeds.
- **Fail:** no distillation. Motion and coach vote STOP below 85 %, and experiment design below 83.9 %.


## Round 39 - run 16 killed, its teacher input unused; run 17 = the teacher with its input x30 (2026-10-27)

**Brief:** run 16 (the e4 teacher) was killed at model_29700. Left + back feeder contact went 58.0 -> 56.3 % against a +2 line. The five teacher input columns' first-layer norms were 0.03-0.06, against a median of 3.65 for the original columns.

**Correction check (5/5): "not used" is right, but the cause is not slow learning of new columns alone.**
- **The learning rate sat at rsl_rl's adaptive floor (1e-5) throughout runs 14 and 16** (architecture, RL, experiment design, motion). KL is above its target even there, so there is no spare step size.
- **Every column moved at random-walk size** (architecture, RL, coach). From 27798 to 29700 the old columns moved a median 0.05, the teacher columns 0.03-0.06. The prediction for a pure random walk at 1e-5 over 20 Adam steps per iteration is 0.014 / 0.045 / 0.062 at the three checkpoints, and that is what was measured. There was no consistent gradient on the new columns.
- **The normalizer is effectively frozen** (count about 1.5e10). The teacher inputs reach the network raw and small (xy in metres / 3), so their effective weight is under 1/60, nearer 1/200.
- **Run 16 at 30 % is in effect a read of (b)** (architecture, RL, experiment design): run 14 continued plus an input that did nothing. Left + back -1.8, feeder -0.5, partner +1.2. Each is within about 1 SE (about 1,700-1,900 left + back feeds per read).
- **D-156's STOP lines were never reached** (experiment design). They were endpoint-gate lines, so e4 is untested, not refuted.
- **Motion:** the input gave the contact point, not where to stand. The policy would also have to learn the stance offset and the forehand/backhand side.

**Votes (t2, 5/5; the form split):**

| Member | Form |
|---|---|
| Experiment design | input gain x30 on the teacher term, run 16's widened init, seed 95; used line: input zeroed loses >= 3 points of left + back contact |
| RL | input gain 10/sigma per input; used line: gain 0 loses >= 2 points |
| Architecture | per-column optimizer step multiplier x30 on the five columns (runner subclass); used line >= 3 points |
| Motion | the true stance spot through the spot input on every live feed |
| Coach | the same as motion; used line: spot on beats spot off by >= 2 points of feeder legal |

- **No form had a majority:** gain 2, spot 2, step multiplier 1.
- **Tie rule (least new code, fewest moving parts): the input gain**, at x30 (experiment design's number, and architecture's multiplier).
  - It uses the observation term's built-in `scale` and adds about 15 lines.
  - It keeps the exact parent start and is one change against run 16.
- **Why the spot route lost:**
  - it starts 6 points below the parent (headroom read);
  - the frozen base also reads that input, so it is two changes;
  - `recover_xy` feeds the recovery reward and the court-feed paths (architecture, RL, experiment design).
- **Reported (RL, experiment design):** the slowly adapting normalizer lowers the effective gain over the run (to about 5-12 by the early check).

**Lines:**
- **Early kill at model_29700:**
  - run 14's lines unchanged (left + back feeder contact up >= 2 points);
  - plus the used line: the same checkpoint and seed with the input zeroed (`PICKLEBOT_TEACHER_GAIN=0`) must lose at least 3 points of left + back contact (experiment design and architecture at 3; RL at 2).
- **Teacher gate unchanged** (D-156).
- **Pre-registered:** experiment design, architecture and coach vote STOP if run 17 fails its usage line, its engagement line or its gate. No third teacher form.


## Round 40 - run 17 killed; the panel votes STOP (5/5) (2026-10-27)

**Brief:** run 17 (the teacher input x30) was killed at model_29700 on both lines.
- Engagement: left + back feeder contact 55.7 -> 53.0 % (line: +2).
- Used: with the input zeroed on the same checkpoint and seed, 53.3 % (line: must lose >= 3).

**Correction check (5/5): a fair test, measured correctly.**
- Experiment design recomputed the counts: 936/1682, 898/1693 and 925/1735.
- The gain reached the network (architecture checked mjlab's scale path).
- The zeroed read is clean: the input's own off state, though after normalization it is a constant, not 0 (motion, architecture).
- The raw teacher column norms (0.03-0.04) are still random-walk size, so PPO gave those columns no steady gradient (RL, architecture, experiment design).
- **What it refutes:** growing a new pathway in a converged policy fine-tuned at rsl_rl's 1e-5 learning-rate floor (KL already above target). It does not refute a privileged teacher itself (coach, motion, experiment design).
- **RL:** most of the teacher input is redundant with ball_pos/ball_vel, so advantage gives little credit for using it.
- **Coach / motion:** the miss pattern is unchanged. 74 % of backhand misses need a move to the left; misses end 0.93-0.97 m from the ball at about 2.0 of 2.7 m/s. The robot reads late and does not commit to the step.

**Votes: STOP, 5/5** (experiment design, architecture and coach as pre-registered; motion and RL too).
- Seventeen rally runs: feeder-ball legal 77-82 % throughout (M1 needs 85 %). Best P(5+) is 18.7 %; the target needs 80 %, about 96 % per shot.
- Every warm-start change from a converged policy has read as noise or made things worse. The one exception, lam_r 2, lifted a constraint.

**Options for the user (members' rankings):**

| Option | Ranked | Rough cost |
|---|---|---|
| A privileged teacher trained **from scratch** (fresh optimizer, starting learning rate about 3e-4, contact and stance inputs from iteration 0), then a DAgger student; teacher gate at 85 % before distilling | 1st by coach, motion, RL, experiment design; 2nd by architecture | about 80-300 lines; 25-90 GPU-hours |
| Accept run 14 model_27798 as the result, with a rally video and write-up | 1st by architecture; 2nd by the others | 1-4 hours |
| A bigger network trained from scratch (the user's scaling interest) | experiment design and architecture, 3rd | 30-100 GPU-hours |
| Retrain the motion controller (left/back and crossover steps under time pressure), then the rally ladder again | last by all; move arrival is already 96-99.7 % | 40-140 GPU-hours |

- RL and experiment design would not offer the spot-route teacher: it is the same fine-tune at the learning-rate floor, and it starts 6 points down.


## Round 41 - after the learning-rate fix: run 18b killed on one family; continue it (2026-10-28)

Brief: the LR-floor finding (D-159), the restart, run 18b's early check (P(5+) 18.4 -> 25.8 %, partner 70.0 -> 77.4 %, feeder 82.3 -> 81.1 %, killed on cross_forehand contact -5.3), the audit and its fixes, and the feed-anchor check (real but small; the left weakness is mostly genuine).

**Correction check (all five):** round 40's STOP followed procedure but its finding ("fine-tuning cannot grow a new pathway") was an artifact of the frozen learner; D-159 already withdraws it. Run 18b's kill was correct: cross_forehand -5.3 points is z -3.7 and survives a 17-family Bonferroni; the other 16 families are within |z| < 2.1. Coach and RL: the drift away from rare feeder balls was foreseeable from the sweep, and 18b had no plan for it beyond a kill line. Experiment design: sched-gate's reference (run 14's single endpoint read, 18.73 %) sat about 1 SD high; future gates use a parent re-read. Slips carried forward: training seeds back to 1-999; the critic and value loss go unmonitored.

**Measured read noise (experiment design, six reads of run 14 on different seeds):** SD per read P(5+) 0.38 points, partner legal 0.34, feeder legal 0.24-0.31, left + back contact 1.31, court contact 1.24; same-seed parent re-reads give no pairing, so SD of a difference = sqrt(2) x SD per read. The -5 family line is 2.2-10 SDs per family (about 3-4 % false kills over 17 families): kept.

**Votes:**

| Member | Vote | Summary |
|---|---|---|
| RL | A | continue from model_29000; forgetting per unit of progress is the same at any rate, so a lower rate buys nothing; the data-side fix (heavier weak-family mix) is the pre-registered next step if feeder drift continues |
| Motion | E then B | adopt the open-rally P(5+) and anchor 0.0 reads, then continue with the training anchor at 0.0; falls and arrival healthy, ready stance improved 0.60 -> 0.78 |
| Coach | G | continue from model_29000 with cross_forehand's weight 1.0 -> 2.0 in the court mix (it is a rare ball, diluted by the weak mix that first took effect in 18b) |
| Experiment design | A | continue; the family guard becomes cumulative against run 14; cross_forehand named as an accepted regression (no more than 3 further points); adopt the open-rally P(5+) now through a measurement D-entry |
| Architecture | A | no new code; exact continuation with PICKLEBOT_LR_WARMUP=0 and the loaded Adam state; record PICKLEBOT_* settings per run |

**Decision: A (3 of 5), rally run 19 (D-160).** Lines are experiment design's (sized from the measured noise). Rejected: F (STOP), since the learner moved more in 1,200 iterations than in runs 3-17 together; D (lower rate), the same trade slower; B and C, each the next single change once A has been read (C: pair reset; then the pace ceiling vs keep-alive, coach and RL).


## Round 42 - run 19 killed on feeder-ball erosion; hold the feeder ball's share of play (2026-10-28)

Brief: run 19 (round 41's continuation) at model_30200: P(5+) open 27.2 -> 33.2 %, partner 77.4 -> 88.9 %, feeder 80.9 -> 77.3 % (killed), five families below run 14 - 5, left + back -6.3; the feeder ball's share of balls started fell 25.9 % (run 14) -> 21.5 % (model_29000) -> 13.3 % (model_30200).

**Correction check:** round 41's decision and implementation were right; the error was its fallback (RL, coach and motion withdraw their round 41 levers): a within-feeder family mix cannot restore a share that halved. The drift was already visible in run 18b's own parent read and nobody computed it; the feeder share is now reported in every pairs read and logged in training. court_feed_prob in run 14's task is 0.80 (D-137), not 0.678 (selfplay.md corrected).

**New measurements (members, CPU reads of the result JSONs):**
- Coach / experiment design: the rally is lost at its start, not in its average. Ends by ball at model_30200: feeder ball 25 %, the first partner ball (the return of a feeder-ball return) 31-33 %, then 16-19 %, 11-14 %, 7-9 %. Pooled partner legal (88.9 %) hides a 67 % first partner ball; P(5+) ~ feeder x 0.69 x 0.84 x 0.89 x 0.93.
- RL: 51 % of all balls at model_30200 are beyond shot 6 (run 14: 16 %); a cap at N shots puts the share at 27-31 % across the three policies for N 6-8.
- Motion: feeder-ball falls rose 0.90 -> 1.44 % per feeder ball (z ~ 4; partner-ball falls 0.32 -> 0.21 %). The left loss is a late start, not lost locomotion (move arrival 99.7 %, foot speed and recovery error unchanged); in the feeder-only reads (court, drill v2) the skill held.

**Votes:**

| Member | Vote | Form, N |
|---|---|---|
| RL | A | rally cap, N = 8 shots |
| Motion | A | 15 % of courts feeder-only (no hand-off) |
| Coach | A | rally cap, N = 6 shots |
| Experiment design | A | rally cap, N = 5 shots |
| Architecture | A | hand-off cap 4 (= 5 shots) |

**Decision: A, 5/5; a rally cap, 4/5; N = 5 (experiment design and architecture; no majority on N, so the tie rule: least new code (equal), then experiment design).** Parent run 18b model_29000 (all five), so run 19's model_30200 is the matched no-cap arm. Early-r19 and r19-gate unchanged. Reported beside them: feeder share (training and read), feeder-ball falls per ball, shot-position end rates, feeder n with its SE. Rejected: B (within-feeder mix; it adds no feeder balls), C (lower rate: the same trade slower), D (pair reset, pace ceiling: not the mechanism), F (STOP). Next single changes if the share holds: B (the within-feeder mix) or the first-hand-off ball (coach); a tighter cap if feeder still drifts.


## Round 43 - round 42's premise refuted; a diagnostic, then branch B (2026-10-28)

Brief: run 20 (D-161, rally cap 5) never trained: its smoke's manipulation check read a training feeder share of 0.686 and `scripts/diag/train_share.sh` showed ~0.67 with or without the cap (move 0.35 / swing 0.05 busy partners end most training rallies). Round 42's falling share (25.9 -> 13.3 %) was a property of the pairs read.

**Correction check (all five):** round 42 took a read-side statistic as a training fact; the manipulation check caught it before any GPU-hours. RL and architecture: the 0.67 total also measured the wrong population (busy-partner courts dominate it); the read's feeder ball is the one that restarts play after a two-robot exchange, rare in training. D-161's mechanism and next steps are void; D-160's data-side fallback (a heavier weak-family mix) is void; D-160's open-rally P(5+) and cumulative guards stand. **New rule (experiment design):** every mechanism number in a brief or D-entry carries a source tag ([train-log], [train-diag] or [read:protocol]); a run that acts on training dynamics is voted only on a premise measured in training, before the vote; manipulation checks are measured on the population the mechanism names.

**Findings:** the loss is in reaching the ball and only in pairs (motion: court and drill v2 contact held, families at 94-100 % in the court read; falls rose only in pairs); the policy sees 80 ms of history and no partner state, so the same ball is played the same way in every read and the difference must be the launch state (RL); the left share of feeder balls did not change (architecture).

**Votes:** 5/5 C (a diagnostic first): coach (refeed delay 2 s), experiment design, motion and RL (3 s), architecture (a training split by partner busy / free plus a read split by the previous rally's length). Rule (experiment design, tie-breaker): L3 = feeder legal difference at 3 s; <= 1.0 -> B, >= 2.5 -> A, between -> B. B's form by majority (coach, experiment design, motion): busy partners off the pair courts; RL preferred the cap. **Result: L3 = 1.12 -> B (rally run 21, D-162).**


## Round 45 - redesign after run 21's failed check: measure in training first (2026-10-28)

**Correction check (all five):** rounds 42-44 each chose a training lever from a read-side number or an unmeasured premise; the pre-launch checks worked (no GPU-hours lost) but three rounds went to scalar lines instead of one instrumented diagnostic. The round-45 brief repeated the error: "exploration noise keeps training rallies short" compares a [train-diag] 61 % per shot with a [read:protocol] 80-90 %, which differ in noise, task (training has drill-v2 balls, a noisy planner, a 0.2 s refeed against the read's 0.5 s) and episode clocks. Architecture: at 0.61 per shot the rally-length ceiling with no resets is 1.59 shots, below run 21's 1.64 line, so freeing partners could never pass it. Motion: about 94 % of resets are time-outs, not falls; the training refeed (0.2 s) is already shorter than the read's, so a randomized refeed would not add displaced starts. **Process changes:** a mechanism claim needs a contrast inside training with one factor toggled (RL); before any training vote, a learning-rate-0 measurement on the candidate task with the existing per-group log, and every lever must show a ceiling that clears its line (architecture); pre-register the fail route too (experiment design); a standing table of training vs read config in every brief (motion); name the match situation, not a correlated rate (coach).

**Votes: 5/5 E** (a measurement first). Forms: coach and motion, the robot's state at feeder launch by the previous rally's length; RL and architecture, std-scale arms at learning rate 0; motion, a deterministic read on the training task; experiment design, S1 (mean actions) and S2 (120 s pair-court episodes) with a pre-registered route. **Decision (tie rule: experiment design's design, with RL / architecture's x1 calibration arm): `scripts/diag/screen45.sh`** (D-164).
