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
