# Panel round 82 brief: D-218 reads INVALID-SPLIT; the read's feeder balls happen early, 2026-11-05

Read first:
- D-218, its addendum and its result in docs/DECISIONS.md;
- round 81 in mjlab/results/footwork-review.md;
- results/half81-summary.txt and half81-*.json;
- dist80b-*.json.

## Result

C model_32598, pairs, 2,048 envs, mean actions:
- **120 s vs 240 s** on dev 4220369-70: the same feeder-ball count (about 2,500 per read, about 2.5 per court). The second half is undefined, so the guard returns INVALID-SPLIT.
  - First-half off-spot share: 0.513.
  - P(5+): 0.405 / 0.416; feeder legal: 0.636 / 0.638.
- **--audit-fixes 120 s** on dev 4220371-72: the reset bucket is 0, but the off-spot share stays at 0.509. P(5+) 0.402 (0.411 without fixes); feeder legal 0.585 (0.632). The leak is not the cause.

**What this establishes:**
- The pairs read's feeder balls almost all happen early in the episode. Once rallies start they run to the timeout.
- The read's opening hazards (h0, h1) and feeder line are therefore mostly about the first few feeder balls after the courts start.

**Inference, not yet measured:**
- Robots spawn across a wide box (x -0.8 to 3.2, y -2.95 to 2.25), and the first feeder ball comes 0.5 s after start.
- If that ball (about 1,024 of about 2,500) is mostly off spot, it carries most of the 0.51 off-spot share.
- The instrument cannot split the court's first feeder ball from later ones.

**Training:** feeder balls are about 6 % reset-type (architecture) and the off-spot share is 0.25-0.29. Episodes are 120 s, with drills on half the courts.

Seeds: training next 217; dev next free 4220373 (4220349-4220356 reserved unread).

## Questions

1. **Correction check.** Is INVALID-SPLIT valid (a guard added before reading the pooled verdict)? Is anything misstated?
2. **Next step.** Vote with coded lines (kills readable at smoke, a dose premise at smoke) and seeds:
   - **(i)** a reporting-only tally of each court's first feeder ball (launch distance, legal), read on C. This confirms or kills the spawn inference before any training.
   - **(ii)** architecture's training episode length 120 -> 24 s (zero code), with a smoke dose premise.
   - **(iii)** RL's feed-the-furthest-robot.
   - **(iv)** STOP to the unfrozen-base phase.
   - **(v)** other.
3. **The target read.** If the first feeder ball after spawn is the dominant loss, the frozen read measures a spawn-start skill: getting to the ball from a random start within 0.5 s. Is that a skill the policy should learn (likely yes, as it is in the frozen read), or does it call for a decision about the instrument? The target and its read are frozen; any change needs a premise and a D-entry, and must never loosen.
