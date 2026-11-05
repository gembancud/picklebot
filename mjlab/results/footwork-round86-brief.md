# Panel round 86 brief: D-222 (steeper first-step bonus) reads KILL-NO-START; the start-reward sub-route closes; name the next phase, 2026-11-05

Read first:
- D-221 and D-222 with their results in docs/DECISIONS.md;
- rounds 84-85 in mjlab/results/footwork-review.md;
- results/qk85-summary.txt and results/qk85-train.jsonl / qk84-train.jsonl;
- the frozen target (results/rally-target.md);
- D-169 and docs/PANEL.md.

## Result

**Q2** is D-221 with the pay span at 0.5 s, a fresh run from fw1b-S. Its smoke passed, with the curve wired: pay per spot 0.164 against 0.073 before. KILL-NO-START fired at +486.

Training-window first-step p50, the time to close 1.5 m (stochastic actions):

| iterations | Q2 left | Q2 back | Q (D-221) left | Q back |
|---|---|---|---|---|
| 0-100 | 1.376 | 1.461 | 1.381 | 1.461 |
| 100-200 | 1.321 | 1.408 | 1.342 | 1.434 |
| 200-300 | 1.302 | 1.408 | 1.328 | 1.442 |
| 300-400 | 1.283 | 1.410 | 1.306 | 1.418 |
| 400-450 | 1.273 | 1.385 | 1.307 | 1.376 |
| 450-480 | 1.263 | 1.379 | - | - |

- **Left** was 0.103 s faster, a pass. The doubled pay kept it moving.
- **Back** was 0.077 s faster, a fail. It held at 1.41 s from iteration 100 to 400, and doubling the pay did not move it.
- **Pre-registered outcome (D-222, 4 of 5):** the start-reward sub-route closes, with no third dose. The wording is "no faster start shown under a direct start reward", not a body limit.
- **Not done:** dev 4220374 is unread.

## A new fact the agent pulled for this round (training logs, mid_heading_hist)

Heading at mid-move is |pelvis yaw from facing the net| when the robot is halfway to the spot.

| run, direction | 0-30 deg early (0-100) | 0-30 deg late |
|---|---|---|
| Q2 left | 0.97 | 0.90 |
| Q2 back | 0.99 | 0.93 |
| Q left | 0.95 | 0.91 |
| Q back | 0.98 | 0.96 |

**The robot never turns.** It side-shuffles left and backpedals back, facing the net, on 90-99 % of spots, and no spot reaches 60 degrees or more. The drill's heading is free beyond 1 m of the spot, so turning is allowed (D-182: heading free; heading toward the net inside 1 m). Turn-and-run (a drop step or crossover) is how players cover distance behind and beside them fastest. Backpedalling caps acceleration. Whether a turn would pay inside a 0.5-3 m spot that ends facing the net is the panel's question.

## The state of the climb

**Rally:**
- The parent is C (rally-d1s3lr3 model_32598), with P(5+) about 0.41.
- The hazards are h0 0.37 and h1 0.26 (the partner's first ball), then 0.08 and 0.02.
- The target needs (1 - h0)(1 - h1) >= 0.886. Today it is 0.464.

**What has failed:**
- Residual levers on the frozen d1 base: cap, IdleRec, stance fix, cut, and 24-s episodes.
- Teacher swaps: Fast4 was not faster at court scale.
- Two direct start rewards: the start moved, about 0.07-0.10 s in training, and back did not move.

**Never tried:**
- (d), the distil-then-PPO joint fine-tune of base and residual. Experiment design named it; architecture withdrew it for lacking a faster teacher.
- A ready-stance or split-step pre-load reward (coach, round 85 (iv)).
- Any change to how back and side moves are made (turning).
- Any lever aimed at h1.

**Resources:**
- The GPU is idle.
- Training seeds: next free 224.
- Dev seeds: next free 4220375 (4220340 held; 4220349-4220356 CONFIRM only; 4220373-4220374 unread).

## Questions

1. **Correction check.** Is KILL-NO-START valid? Is the sub-route correctly closed under D-222's pre-registration? Is anything misstated, including the heading reading?
2. **The next phase.** Vote with coded lines (readable at smoke, on windows that exist) and seeds. Name the simpler option you rejected and why.
   - **(i) Back and side movement form:** a turn-and-run lever on the specialist, for example a reward or command shaping that permits or pays a drop step on back spots. It still feeds a d1c rebuild only after a gate.
   - **(ii) The partner's first ball (h1)** and the spawn ball on the current body. For example, positioning or readiness after the hand-off, or the feeder-side lever that was never tried.
   - **(iii) (d), the joint fine-tune** of base and residual on the rally task, with a distillation anchor.
   - **(iv) A ready-stance or split-step pre-load reward** on the specialist (a new instrument and new code).
   - **(v) Use what moved:** Q2's left gain is real in training. Read it at mean actions and consider a d1c on it anyway. Note this would be a selection after a kill and needs a line that cannot loosen the gate.
   - **(vi) Other**, or a STOP recorded with what would have to be true for the target. Under D-169 a STOP moves to the next phase; the user decides only at the target.
3. **The target.** With the start-reward sub-route closed, what is the panel's honest estimate of the best reachable P(5+) on this body and stack, and what single phase gives the largest expected gain toward 0.80? The target itself is unchanged.
