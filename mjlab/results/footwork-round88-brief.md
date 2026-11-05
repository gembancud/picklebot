# Panel round 88 brief: D-224 (h1 attribution, fixed tally) reads BALL; design the pre-registered hitter-side lever, 2026-11-05

Read first:
- D-223, D-224 and their results in docs/DECISIONS.md;
- round 87 in mjlab/results/footwork-review.md;
- results/h1r87-summary.txt and h1r87-read-*.json;
- picklebot_mj/tasks/return_stand.py:
  - `_credit_partner` (D-137), `partner_return`, `keep_alive_landing` (D-129);
  - `feeder_return_now` / `feeder_family_return` (D-150);
  - the pair branch in `_step`;
- picklebot_mj/pairs.py (ho_cls / ho_live);
- picklebot_mj/tasks/__init__.py around lines 1890-2015 and 2189;
- the frozen target (results/rally-target.md).

## Result

- **Instrument check (dev 4220375 re-read):** VALID, 0.7375 vs 0.7466.
- **Read (dev 4220377):** VALID.
- **Pooled:** VALID, 0.7247 vs 0.7322. h1_route reads **BALL**:

| | n | legal | Wilson |
|---|---|---|---|
| near first hand-offs (d <= 0.3 m) | 378 | 0.873 | 0.836-0.903 |
| near later hand-offs | 98,884 | 0.9993 | 0.999-0.999 |

| legal by receiver distance | <= 0.1 | 0.1-0.2 | 0.2-0.3 | 0.3-0.5 | 0.5-0.8 | 0.8-1.2 | > 1.2 m |
|---|---|---|---|---|---|---|---|
| first hand-off | 0.880 | 0.882 | 0.864 | 0.841 | 0.851 | 0.806 | 0.543 (n 1,226; share 0.384) |
| later | 0.998 | 0.999 | 0.999 | 0.999 | 0.998 | 0.982 | 0.829 |

- The first hand-off is hard at every distance.
- Position adds to it, but the share beyond 1.2 m (0.384) is just under the POSITION line of 0.40.
- **Pre-registered next (D-223):** a hitter-side lever on the feeder-ball return only, as its own entry.

## Facts for the design

**C's training task (Picklebot-Rally22b-FastMove-G1) already pays, on every shot:**

| term | weight |
|---|---|
| legal_return | 250 |
| rally_bonus | 125 |
| partner_return | 150 (D-137: to the hitter when the partner legally returns its ball) |
| keep_alive (keep_alive_landing, D-129) | 100 (landing-spot and flight-time score) |
| net_clearance | 50 |
| ball_out_over | -25 |
| paddle_contact | 50 |
| approach_ball | 2 |
| approach_far | 1 |

- The feeder-ball return (the ball that becomes the first hand-off) is paid like any other shot. Nothing singles it out.
- The ball the receiver gets is the hitter's return of the feeder ball, mirrored.
- The hitter made that return after a spawn scramble: q0 0.25, and far-ball legal 0.42-0.45.
- **Unmeasured:** what makes it hard. Candidates are incoming speed, height, spin, landing spot, and flight time against the receiver's readiness.
- **Instrument available:** D-150's `feeder_return_now` flags a legal return of a feeder ball. `pairs.ho_cls == 0` with `ho_live` flags the receiver's first hand-off.
- **Resources:** the GPU is idle. Training seeds next free 224. Dev seeds next free 4220378 (4220340 held; 4220349-4220356 CONFIRM only).

## Questions

1. **Correction check.** Is BALL valid as coded? Are the 25 + 23 early-volley class-0 feeds (handoff_stale[1]) a problem for the reading? Is anything misstated?
2. **The lever.** Vote with one change, parent (C model_32598 on the d1 base unless argued), smoke and kill lines readable on windows that exist, an endpoint gate (h1 and first-hand-off legal on D-204's pooled seeds against C, plus the standing guards), and seeds. Options:
   - **(i) Partner credit on the first hand-off:** an extra one-shot to the hitter of a feeder-ball return when the partner returns it legally (pays the "easy first ball").
   - **(ii) Keep-alive on the feeder-ball return:** the keep_alive_landing score weighted up on that shot only.
   - **(iii) A diagnostic read first:** the incoming ball state of first vs later hand-offs at the receiver (speed, apex, landing point, flight time). The lever is then chosen on what is hard. Read only, about 20 lines.
   - **(iv) Other.**
3. **The target.** With BALL confirmed, what is the panel's estimate for h1 under the best lever, and does it change the 0.45-0.55 estimate? The target itself is unchanged.
