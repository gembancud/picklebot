# Panel round 80b: a correction to the winning option before launch, 2026-11-05

Round 80's votes:

| option | votes |
|---|---|
| (iii) restart-state starts | 2: coach (pair_drill_court_frac 0.5 -> 0, no new code) and RL (random rally ends on half the pair courts, new code) |
| (i) std floor 0.1 -> 0.2 | 1: architecture |
| (vi) feeder legal by launch distance, then a routed choice | 1: experiment design |
| (iv) the D-063 fall penalty on C | 1: motion |

No option has a majority. Under the least-new-code tie rule, the zero-code options are coach's (iii) and architecture's (i), and experiment design's position (which leans toward (iii)) would pick coach's form.

**The agent checked coach's form in code before launch. It does not do what it was voted to do.**

1. `pair_drill_court_frac` (D-162, return_stand.py:126-130 and 332-336) does not create drill courts; it confines move and swing episodes to that fraction of courts, at move_prob / frac.
   - C trains with move_prob 0.35 and swing_prob 0.05 at frac 0.5, so drills run at 0.70 / 0.10 on half the courts, and the other half have no busy robot and play live rallies, as the pairs read does.
   - Setting frac 0 does not make every court live. It spreads move and swing episodes over every court at 0.35 / 0.05, so hand-offs to a busy partner end rallies on all courts again. That is the problem D-162 was introduced to fix.
   - Making every court live would need move_prob 0 and swing_prob 0 as well. That removes the move and swing drills from training, a second change.
2. The launch-state log (D-165, return_stand.py:338-340) counts pair courts only when drill courts are on. So the training figure of 28 % of feeder balls with the receiver more than 1.2 m off its spot was already measured on the live-rally courts, not on drill courts.
   - The practice-vs-read gap (28 % vs 51 % off-spot; feeder legal about 0.72 in training vs 0.60-0.64 at read) is therefore not explained by drill courts.
   - Candidate explanations not yet tested: exploration noise; episode resets every 120 s in training; the read's episode that never resets except on a fall.

Training seeds next 215; dev next free 4220366 (4220349-4220356 reserved unread).

## Question

Given this correction, re-vote among:
- **(i)** std floor 0.2 (architecture);
- **(iii-RL)** random rally ends on half the pair courts (new code);
- **(vi)** experiment design's launch-distance read, then a routed choice;
- **(iv)** the D-063 fall penalty (motion; R3 is a gate);
- **(v)** STOP to a named next phase;
- **(other)**.

Keep your coded lines from round 80 unless the correction changes them. Reply in under 250 words, ending with `VOTE: (x) <one line>`.
