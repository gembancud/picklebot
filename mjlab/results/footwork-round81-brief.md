# Panel round 81 brief: D-217 (random rally ends) KILLED at +360; the dose did not arrive, 2026-11-05

Read first:
- D-216 and D-217 with their results in docs/DECISIONS.md;
- rounds 80 / 80b in mjlab/results/footwork-review.md;
- results/dist80b-summary.txt, cut81-summary.txt, cut81-kill.txt and cut81-train-share.jsonl;
- the frozen target (results/rally-target.md);
- D-169 (STOP moves to the next phase).

## What D-216 established (corrected instrument)

C's feeder-ball legal by launch distance from the recovery spot, dev 4220366-67, mean actions:
- 0.90 within 0.3 m (n 436);
- 0.86 at 0.3-0.5 m, 0.81 at 0.5-0.8 m, 0.76 at 0.8-1.2 m;
- **0.42 beyond 1.2 m (n 1,724, about 50 % of launches)**;
- 0.50 on reset feeds (the first ball after spawn; about a third of feeder balls).

Exploration noise does not explain the practice-vs-read gap. The training off-spot share is 0.25-0.29 against 0.50 at read.

## D-217 result

X = C + pair_cut_prob 0.33: on half the live courts, a received hand-off is cut 0.2-0.6 s after it is received.
- **Smoke passed** (2.50 vs 4.157).
- **Killed at +368:**
  - KILL-NO-HIT: legal_return 0.672 vs 0.705;
  - KILL-FARM: rally length 2.01 vs C2's 4.22.
  - KILL-EASY passed (0.72); NO-SHARE and NO-DOSE read NO-DATA (no log row past +360 yet).
- **Both firing lines are partly built into the lever.** Cut balls log as misses, and feeder balls became 3x as common and harder. Cuts shorten rallies by design. The agent adopted the kill list without checking it against the lever.
- **The dose did not arrive.** The off-spot share of live-court feeder launches stayed at 0.281 cumulative (line >= 0.40). Feeder share rose to 0.25. A cut 0.2-0.6 s into flight leaves the receiver near its spot. At read, the off-spot feeder ball follows a miss the robot chased.

## Where we stand

- C (P(5+) 0.41) stays the parent.
- The opening feeder ball is lost mostly when the robot is more than 1.2 m off its spot at launch (about half of read launches), or on the reset ball.
- Training has not produced that state at the read's rate under any lever tried.

The GPU is idle. Training seeds next 217; dev next free 4220369 (4220349-4220356 reserved unread).

## Questions

1. **Correction check.**
   - Is the KILL valid as pre-registered? Are the firing lines meaningful for this lever?
   - The dose failure stands independently (the cumulative 0.281). Does that close this form of the lever?
2. **What would actually put training robots more than 1.2 m off spot at a feeder launch?** For example:
   - a cut timed late (after the receiver has committed, e.g. at or after the bounce, or on misses only);
   - feeding the next ball to the robot that just moved furthest;
   - starting episodes from off-spot states.
   Name the simplest version, and check it against the read's launch states.
3. **Next step.** Vote with coded lines, kill checks valid for the lever, and seeds:
   - **(i)** a re-designed restart lever (name it, with a dose premise checked at smoke);
   - **(ii)** the reset-ball lever (the first ball after spawn reads 0.50; about a third of feeder balls);
   - **(iii)** STOP to the next phase (unfrozen base / motion space), per D-169;
   - **(iv)** other.
