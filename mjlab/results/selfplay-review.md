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
