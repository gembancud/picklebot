# Panel round 98 brief (narrow): D-237 SMOKE-FAIL on the sector-share line, 2026-11-06

Read first:
- D-237 at the end of docs/DECISIONS.md;
- round 97 in mjlab/results/footwork-review.md;
- results/lc99-summary.txt;
- mjlab/picklebot_mj/tasks/move_drill.py (_new_spot: a spot with less than 0.5 m of room is reversed, and its sector becomes (s + 4) % 8).

## Result

The smoke (seed 239, 160 iterations from M) passed seven of eight lines:
- exact falls 0.639;
- launcher courts at 0.038 falls per episode;
- dose 1.988;
- config (weights (1,1,2,2,2,1,1,1) in env.yaml).

**Failed:** the sector share of 2-4 (left, back-left, back) was 0.436 of 5,345 move spots, against the line >= 0.45.

Spots issued per sector 0-7: 645, 521, 801, 728, 804, 487, 635, 724.
- **Left (2) is boosted:** 801 against right (6) 635.
- **Back is partly flipped forward near the baseline:**
  - 4 -> 0: forward 645 against forward-left 1's 521;
  - 3 -> 7: forward-right 724 against back-right 5's 487.

The agent set the 0.45 line from the 0.545 pre-flip share, without allowing for the flips that architecture flagged in round 97. Uniform weights would give less than 0.375 after flips; this smoke did not measure it.

Nothing else ran. Seed 239 is used. Training seed 238 and dev 4220402-4220403 are still unread, except dev 4220402, which stage 0 used for M's direction read.

## Question

Vote one, in under 200 words, with the reason:
- **(a)** Weights x3 on sectors 2-4: (1,1,3,3,3,1,1,1), architecture's round-97 form. Same lines, including >= 0.45. New smoke seed 240, training 238.
- **(b)** Keep x2 and re-derive the line. The agent's view: this is loosening after seeing the data, so it is not allowed.
- **(c)** Weight only the left sectors (2, 3) x2, because back flips forward anyway, with a line on the share of sector 2-3 instead. This changes the target of D-237.
- **(d)** Other.
