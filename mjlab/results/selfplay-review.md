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
