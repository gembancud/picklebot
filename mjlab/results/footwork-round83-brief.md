# Panel round 83 brief: D-219 (24-s episodes) reads SMOKE-FAIL - the dose premise is not met, 2026-11-05

Read first:
- D-219 and its result in docs/DECISIONS.md;
- round 82 in mjlab/results/footwork-review.md;
- results/ep82-summary.txt and ep82-smoke-share.jsonl;
- the frozen target (results/rally-target.md);
- D-169.

## Result

Smoke: seed 218, 160 iterations, training episode length 24 s.
- **Passed:** falls 2.193 (line 4.157); exit, traceback, std and config all ok.
- **Dose line:** NO-DATA as coded, so SMOKE-FAIL.
  - The window design error is the agent's: the first log row is at +22, so the window needed a row at +182 and the smoke ended at +162.
  - Over the window the rows cover (+22 to +162), the reset-feed share is **0.096** (n 2,833), below the 0.15 premise. The premise fails either way.
- Nothing was trained; training seed 217 is unused.

## The premise in numbers

The read's first feeder ball converts q0 0.25-0.26; later balls q1 0.51-0.53 (court_counts). The ceiling is P(5+) <= 1 / (2 - q0) = 0.57; the target needs q0 >= 0.75.

**Training dose:**
- At 120 s, reset feeds are about 6 % of feeder-type outcomes; at 24 s, about 9.6 % (this smoke).
- Training rallies end often (drill courts, busy partners, misses), so feeder balls stay the large majority.
- The reset bucket counts the leak ball at each env reset. The spawn feeder ball that follows (the read's q0 ball) is logged by launch distance, not in the reset bucket.

The GPU is idle. Training seeds next 217; dev next free 4220373 (4220349-4220356 reserved unread).

## Questions

1. **Correction check.** Is SMOKE-FAIL valid? Is the reset bucket the right dose measure for the q0 ball? Is anything misstated?
2. **Next step.** Vote with coded lines (dose and kills readable at smoke, on windows that exist) and seeds:
   - **(i)** a stronger dose of the same lever: a shorter episode (e.g. 8-12 s), with the same premise line;
   - **(ii)** a direct spawn-start drill: some courts start every rally from a random spawn-box pose (new code), with a dose line on the logged first-ball share;
   - **(iii)** STOP to the next phase;
   - **(iv)** other.
3. **The target.** With q0 at 0.26 and later balls at about 0.5, the ceiling arithmetic says the frozen target needs both a much better spawn-start ball and later restarts at about 0.8. Is the target reachable from this route, or should the panel record a STOP and name the phase? The target itself is unchanged.
