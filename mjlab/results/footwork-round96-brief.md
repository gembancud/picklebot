# Panel round 96 brief: D-235 (launcher courts) killed on a defective line; R3 0.0653 -> 0.0438 at +360, 2026-11-06

Read first:
- D-234 and D-235 with their results and fix in docs/DECISIONS.md (the newest entries);
- round 95 in mjlab/results/footwork-review.md;
- results/fl95-summary.txt (the premise read), results/lc97-summary.txt and results/lc97-kill-court.json;
- the frozen target (results/rally-target.md).

## Result

**D-234 premise read: FEED.**
- The d1 base passes R3 on R3's own instrument (0.0345).
- R's excess (0.0622) is 63 % with a ball in play after 1 s, mostly the first feed after the random spawn.

**D-235: launcher courts.** A quarter of the courts (the top half of the drill courts) play the court read's own 8-s episodes inside R's drill-reset rally training.

**First smoke: SMOKE-FAIL, two agent defects.**
- The launcher feeds were drill-v2 feeds aimed at the start spot.
- The smoke falls estimator assumed Poisson resets.

Both were fixed. With the fix, R reads 0.057 on the launcher courts against 0.062 on the court read. The rerun smoke passed.

**Rerun: training killed at +360 by D-194's KILL-NO-HIT.**
- Training legal_return 0.488 against the 0.705 line.
- That line averages a per-episode reward sum over the episodes that ended. The 8-s launcher episodes end about 15x as often as 120-s rally episodes, so the line measures the episode mix. This is a defect in the agent's line selection.
- Falls 1.99 passed (kill > 3.14). KILL-LOST-OPEN passed (0.619 -> 0.660).
- Reported: the pair-court rally length in training was 6.97, against D-232's 4.75 at the same point.

**Reported, read by hand after the kill:** model_34160 (+360) on the court read, dev 4220397.
- R3 **0.0438** against R's 0.0653 on the same seed (the bar is 0.04).
- Legal returns 0.729 against 0.686.
- The rally side (set-start read) was not read.

**R3 so far:** C 0.0556; R 0.0575-0.0653; F 0.0584; K 0.0523; **L(+360) 0.0438**; d1 base 0.0345.

**Resources:** the GPU is free. Training seeds from 237. Dev seeds from 4220402 (4220398-4220399 unread).

## Questions

1. **Correction check.** Is the KILL verdict right as coded, and is calling the line defective honest? Are there other defects (the 4.157 smoke line is about 10x loose on the exact count; anything else)?
2. **Next.** Vote, with one change, parent, lines and seeds:
   - **(i) Rerun D-235 from R with corrected kill lines** (a fresh seed, 1,200 iterations). Name the legal-return line, for example an exact count of legal returns per feed on the non-launcher courts against R's own training value, or the pair-court share log.
   - **(ii) Continue the killed run from model_34160** with corrected lines (saves 360 iterations; is it honest?).
   - **(iii) Read model_34160 on the full gate now** (set-start read + R3 on dev 4220398), reported or as a gate.
   - **(iv) Other.**
3. **The target.** What is the honest estimate for both bars now?
