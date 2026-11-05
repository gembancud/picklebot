# Panel round 89 brief: D-225 (first hand-off ball quality) reads NEITHER; ball tally multi-counted; receivers moving on the tail, 2026-11-05

Read first:
- D-225 and its result in docs/DECISIONS.md;
- rounds 86-88 in mjlab/results/footwork-review.md;
- results/bq88-summary.txt and bq88-read-*.json (launch_state.ball_by_class);
- D-199, D-202, D-204 (diag68), D-205 and D-214 (the earlier readiness and recovery levers);
- the frozen target (results/rally-target.md);
- D-169.

## Result

**Validity:** H1-RECON is valid on both reads and pooled (0.7238 vs 0.7308). h1_route reads BALL again (near first hand-offs 0.879, n 348, against 0.9992).

**Route as coded: NEITHER.** None of the pre-registered lines fired.

| | feeder-ball returns | handed-ball returns |
|---|---|---|
| keep_alive median | 0.007 | 0.000 |
| ball speed p50 | 9.13 m/s | 9.28 m/s |
| ball speed p90 | 10.19 m/s | 9.61 m/s |
| spin p50 | 74.6 rad/s | 88.0 rad/s |

| | first hand-off | later hand-offs |
|---|---|---|
| receiver speed p50 | 0.30 m/s | 0.24 m/s |
| receiver speed p90 | 1.27 m/s | 0.53 m/s |
| share moving > 0.5 m/s (reconciled tally) | **36.1 %** | **11.9 %** |

**Instrument defect (found after the verdict):**
- The ball-quality histograms are multi-counted: about 2.9x for feeder returns and 2.5x for handed returns, against court_counts. `return_now` / `keep_alive_now` likely stay set across the physics substeps of one control step.
- The ratios differ by class, so the keep_alive, ball-speed and spin lines are not reconciled.
- keep_alive is also mostly 0: 98 % of handed returns and 80 % of feeder returns score 0.
- **The receiver-speed tally is booked once per hand-off and reconciles.**

**Where h1 comes from** (experiment design, round 88):
- 64 % of first hand-off misses come from receivers beyond 1.2 m (position).
- Near receivers miss at 0.12 against 0.001.
- The receivers are also moving on the tail (above).

## The state of the climb

**Parent:** C (rally-d1s3lr3 model_32598), with P(5+) about 0.41. The hazards are h0 0.37 and h1 0.27, then 0.08 and 0.02.

**The panel's estimate since round 86:** best reachable P(5+) about 0.45-0.55 on this body and stack. 0.80 is not shown reachable: it would need h0 and h1 near 0.06 each.

**Closed or failed:**
- residual levers on the frozen base;
- teacher swaps;
- two direct start rewards;
- the readiness levers (D-199, D-202), recovery while parked (D-205, D-214) and the stance fix (D-215).

**Untried:**
- partner credit on the first hand-off (RL, experiment design, round 88);
- the joint fine-tune (d) (experiment design, motion, round 86);
- turn-and-run (architecture, coach, round 86);
- a receiver-readiness lever aimed at the first hand-off specifically.

**Resources:**
- The GPU is idle.
- Training seeds: next free 224.
- Dev seeds: next free 4220380 (4220340 held; 4220349-4220356 CONFIRM only).

## Questions

1. **Correction check.** Is NEITHER valid as coded? Is the multi-count diagnosis right, and does it void the ball lines? Is anything misstated?
2. **Next step.** Vote with coded lines (readable at smoke, on windows that exist) and seeds. Name the simpler option you rejected.
   - **(i)** Partner credit on the first hand-off: RL's and experiment design's round-88 form, one dose, a fail closes the hitter-side route.
   - **(ii)** A receiver-readiness lever on the first hand-off only, for example paying a set receiver (speed at or below a line) at the first hand-off's arrival. The earlier readiness levers failed; say what is different.
   - **(iii)** Fix the ball tally (one count per landing) and re-read with motion's READINESS split. Another read.
   - **(iv)** The joint fine-tune (d).
   - **(v)** STOP this phase. Record that 0.80 is not reachable on this stack as shown, with what would have to be true, and name the next phase under D-169. A new body or controller is outside the loop's authority without the user.
3. **The target.** Is the honest report to the user now that the target is out of reach on this stack? If so, what single change, possibly outside the loop's authority, would the panel ask the user for? The target itself is unchanged.
