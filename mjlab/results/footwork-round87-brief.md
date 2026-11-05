# Panel round 87 brief: D-223 (h1 attribution read) reads INVALID - the tally over-counts first hand-offs by about 2 %, 2026-11-05

Read first:
- D-223 and its result in docs/DECISIONS.md;
- round 86 in mjlab/results/footwork-review.md;
- results/h1r86-summary.txt;
- results/h1r86-read.json and h1r86-smoke.json (pairs.handoff_by_d, len_hist, open_len_hist);
- picklebot_mj/pairs.py (ho_* and _ho_tally, on_reset, step);
- picklebot_mj/d1_rule.py (h1_split, h1_recon, h1_route).

## Result

**Smoke (dev 4220376):** VALID.

**Read (dev 4220375):**
- Totals match court_counts exactly.
- First hand-off legal is 0.7289 against 1 - h1 = 0.7425. The gap of 0.0136 is above the 0.01 line, so it is INVALID as coded.
- h1_route would also read INVALID-SPLIT: near first hand-offs n 176 (< 200).
- No route is taken.

**The over-count:** class 0 has 1,608 feeds and 436 misses, against 1,573 rallies that reached shot 1 and 405 that ended there. That is 35 extra feeds and 31 extra misses.

**Leading hypothesis (untested):**
- `fire` clears `handed` only for the env that gets the feeder ball.
- The partner env can keep a stale `handed` flag and a stale `ho_cls` from an earlier rally. For example, a reset (leak) ball, since `pairs.on_reset` leaves `handed` set (architecture, D-219).
- Once the court restarts, that ball finishes as a "live" own-ball feed of class 0.
- court_counts carries the same feeds, which is why the totals reconcile and only the class split does not.

## Reported, unvalidated (the class-0 rows carry the over-count)

| | n | legal | d <= 0.3 m | 0.3-0.5 | 0.5-0.8 | 0.8-1.2 | > 1.2 m |
|---|---|---|---|---|---|---|---|
| first: share | 1,608 | 0.729 | 0.110 | 0.124 | 0.169 | 0.223 | 0.375 |
| first: legal | | | 0.84-0.88 | 0.864 | 0.842 | 0.793 | 0.556 |
| later: share | 88,815 | 0.998 | 0.561 | 0.323 | 0.101 | 0.012 | 0.002 |
| later: legal | | | 0.998-0.999 | 0.999 | 0.998 | 0.978 | 0.822 |

If this survives a fix, the first hand-off is both a position problem and a ball problem:
- Receivers are far from their spot, 60 % beyond 0.8 m against 1.4 % for later hand-offs.
- Even near receivers return it legally at only about 0.85, against 0.999.
- That matches the spawn-scramble picture of h0: both robots start the rally away from their spots.

**Resources:**
- The GPU is idle.
- Training seeds: next free 224.
- Dev seeds: next free 4220377 (4220340 held; 4220349-4220356 CONFIRM only).

## Questions

1. **Correction check.** Is INVALID right? Is the over-count hypothesis right? Check the code.
2. **Next step.** Vote with coded lines and seeds:
   - **(i) Fix and re-read:**
     - The class and bin are booked only for balls received in the current rally, for example by clearing `handed` or `ho_cls` for both envs at `go` and on reset, logging only.
     - A test reproduces the stale-flag case.
     - D-223's read is repeated unchanged on fresh dev seeds, with the same smoke and lines.
     - Say whether H1_RECON_H1 stays 0.01 (it cannot be loosened).
     - Say whether the near-split minimum of 200 needs a larger read (e.g. 4 x 120 s or more envs) to be readable. That is a change of read size, not of the line.
   - **(ii) Treat the unvalidated split as enough** and name the next phase now.
   - **(iii) Other.**
3. **The target.** Does this change the round-86 estimate (best reachable P(5+) about 0.45-0.55)? The target itself is unchanged.
