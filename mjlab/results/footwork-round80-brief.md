# Panel round 80 brief: D-215 (stance-target fix) reads NO-CANDIDATE, 2026-11-05

Read first:
- D-215 and its result in docs/DECISIONS.md;
- round 79 in mjlab/results/footwork-review.md;
- mjlab/results/cfs79-summary.txt;
- the frozen target, mjlab/results/rally-target.md;
- docs/PANEL.md (STOP rules) and D-169.

## Result

F = rally-d1s3cfs: C model_32598 + court_feed_stance with the planner off (launcher feeds' stance target set to their own stance spot). Training seed 213; smoke passed; training clean.

**Against C:**
- GAIN2 -1.17 points (lower bound -2.52).
- **Guard breach:** backspin -5.1 against the original parent.
- H0 0.3735 vs 0.3725, so fail.
- ready 0.293; falls per 1,000 hits 0.67 (C 0.89).

**Against C2 (the plain continuation):** +0.05 points. F reads as the continuation.

**Direction contact F / C:**

| direction | F | C |
|---|---|---|
| forward | 0.920 | 0.918 |
| left | 0.389 | 0.407 |
| back | 0.599 | 0.584 |
| right | 0.774 | 0.777 |

**R3 (reported):**
- court read (24 s): C 0.0556, F 0.0558 robot falls per episode (target <= 0.040);
- pairs falls / (falls + envs): F 0.042, C 0.052.

## The record since C was promoted (D-211, 2026-11-04)

| run | change | vs C | verdict |
|---|---|---|---|
| C2 | recipe continued | -1.22 | no compound |
| K | pair_rally_cap 5 | +0.87 (lower bound -0.48) | ready 0.211, long rallies lost |
| d1b | Fast4 teacher | - | not faster at court scale |
| R | IdleRec | - | killed, no climb |
| F | stance-target fix | -1.17 (+0.05 vs C2) | breach, no H0 |

**Where things stand:**
- P(5+) 0.41 against 0.80. Feeder legal 0.64 against M1's 85 %. R3 about 5.6 % against 4.0 %.
- On the current pooled pairs read, P(5+) went from 0.381 (d1s3) to 0.41 (C). Earlier figures such as run 18b's 25.8 % came from other read protocols and are not directly comparable.
- Every lever since then has read within noise of the plain continuation.

The GPU is idle. Training seeds next 215; dev next free 4220366 (4220349-4220356 reserved unread for a CONFIRM).

## Questions

1. **Correction check.** Is NO-CANDIDATE valid as pre-registered? Is anything misstated?
2. **What we learned.**
   - Five changes on C read within about 1-2 points of the plain continuation.
   - Is the binding limit the recipe (LR 3e-5, std at its 0.1 floor, KL about 0.006), the residual architecture (frozen d1 base, lam_r 2, 35 outputs), or the task?
   - What evidence would separate these?
3. **Next step.** Vote with coded lines, kill checks and seeds:
   - **(i)** A recipe change on C: for example, raise the std floor or the LR schedule. One knob. Name it.
   - **(ii)** Motion's hand-off extension of the stance fix (partner balls too).
   - **(iii)** Restart-state starts (coach; new code).
   - **(iv)** A falls / R3 lever (the target's second open gate).
   - **(v)** STOP. Under D-169 the climb does not end; a STOP moves to a named next phase (for example shared-policy self-play / 2v2, or a different route to the target).
   - **(vi)** Other.
