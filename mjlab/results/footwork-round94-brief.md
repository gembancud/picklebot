# Panel round 94 brief: D-232 (fall penalty on R) reads KILL-NO-FALLS - court falls unchanged, 2026-11-06

Read first:
- D-231 and D-232 with their results in docs/DECISIONS.md;
- round 93 in mjlab/results/footwork-review.md;
- results/df93-summary.txt, df93-kill.txt, df93-kill-court.json and df93-court-R-4220390.json;
- the R3 read (Picklebot-Latent-Court-Res-G1, 2,048 envs, 24 s, random recovery spots, all families, mean actions);
- C's training task Picklebot-Rally22b-FastMove-G1: which courts run what (pair_drill_court_frac 0.5: pair courts and drill courts, move-to-spot and ghost-swing episodes on the drill courts);
- the frozen target (results/rally-target.md).

## Result

**F = R + D-063's fall penalty (-50).** The smoke passed.
- **+360 kill:** D-194's lines CONTINUE; KILL-LOST-OPEN CONTINUE (training opening 0.617 -> 0.659).
- **KILL-NO-FALLS:** model_34160 read **0.0584** court falls per episode, against R's **0.0586** on the same seed (dev 4220390). The line was <= 0.0486, so KILL.

**Reading (agent):** the penalty is almost never paid. Rally training under the drill reset rarely falls (about 0.5 per 1,000 env-s), while the court read's falls come from single-robot launcher feeds, random recovery spots and between-feed recovery. Those states are not trained, or barely trained, in the rally task.

**History:**
- The d1 base alone reads 0.0318 (it passes R3).
- The rally residual lineage raised it: d1s2 0.068, d1s3 0.062, C 0.0556, R 0.0575.

**The target as it stands:**
- P(5+) 0.7236 (R, unpromoted), against 0.80 with Wilson low 0.78, on the set-start read.
- R3 <= 0.04: C, R and F all at about 0.056-0.059.

**Resources:**
- The GPU is free.
- Training seeds: next free 232.
- Dev seeds: next free 4220393 (4220391-4220392 unread, held for this line; CONFIRM 4220349-4220356 unread).

## Questions

1. **Correction check.** Is KILL-NO-FALLS valid, and is the agent's reading right? Check what the rally task's drill courts actually train, and what the court read's falls are.
2. **The next step for R3.** Vote, with one change, parent, lines and seeds. Options:
   - **(i) Practise the court read's states:** mix court-feed episodes (launcher feeds, random recovery spots) into R's training on some courts, with the fall penalty or without it.
   - **(ii) A premise read first:** when and where the court-read falls happen (time since reset, during a feed or between feeds, family, recovery-spot distance), on R and on the d1 base, which passes.
   - **(iii) Anchor the residual toward the base** in the states where the base is stable.
   - **(iv) A question to the user:** whether R3's court read should follow the set-start premise too. The user changed the rally start, not the falls bar. Only if the panel judges the instrument mismatched.
   - **(v) Other.**
3. **Order and estimate.** How do R3 and the remaining P(5+) gap (0.72 -> 0.80) fit together? Which runs first?
