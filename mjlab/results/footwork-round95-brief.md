# Panel round 95 brief: D-233 (court-task practice) reads KILL-NO-SAFER; two R3 levers have failed, 2026-11-06

Read first:
- D-231, D-232 and D-233 with their results in docs/DECISIONS.md;
- rounds 93-94 in mjlab/results/footwork-review.md;
- results/ct94-summary.txt, ct94-kill.txt and ct94-kill-court.json;
- results/df93-court-R-4220390.json and results/stage5c-d1-child-court.json (the d1 base's court read; on another instrument per round 94);
- the frozen target (results/rally-target.md).

## Result

**K = R continued on Picklebot-Latent-Court-Res-G1.** Smoke passed (falls 3.83 against 4.157).
- **KILL-NO-SAFER at +125:** training falls 3.738 -> 3.747 per 1,000 env-s; the line was <= 0.8 x.
- **Reported:** model_33920's R3 on dev 4220391 is **0.0523**, against R's 0.0575-0.0586; the kill line was <= 0.0486.
- **Driver defect (the agent's):** the watcher crashed before its court read and before stopping training. The agent stopped training at +217 by hand, as the kill required.

**R3 so far** (court falls per episode, the h5f court read; bar <= 0.04):

| policy | R3 | note |
|---|---|---|
| C | 0.0556 | dev 4220365 |
| R (drill-reset practice) | 0.0575 / 0.0586 | dev 4220389 / 4220390 |
| F (R + fall penalty, +360) | 0.0584 | dev 4220390 |
| K (R + court-task practice, +100) | 0.0523 | dev 4220391 |
| d1 base | 0.0318 | different instrument |

**What R3 is:** a single robot facing the launcher, 8-s episodes (about 2.7 feeds each), random recovery spots, all families. R's falls are diffuse (easy families included), about 27 % happen between feeds, and the front-zone families fall most.

**The target as it stands:**
- P(5+) 0.7236 (R, unpromoted) against 0.80 / Wilson low 0.78;
- R3 0.052-0.059 against 0.04;
- C stays the parent.

**Resources:**
- The GPU is free.
- Training seeds: next free 234.
- Dev seeds: next free 4220394 (4220392-4220393 unread).
- The CalTennis pilot waits on the user's yes to a package install.

## Questions

1. **Correction check.** Is KILL-NO-SAFER valid, and is the reading right? Is the manual stop at +217 handled honestly?
2. **Next for R3.** Vote, with one change, parent, lines and seeds:
   - **(i) The mixed form:** court-read episodes inside the drill-reset rally training (motion's 40-80 lines; experiment design's random recovery on drill courts, about 20 lines). This keeps the rally gain and practises R3's states continuously.
   - **(ii) The premise read now** (coach / architecture: time since reset, phase, distance, family, on R and the d1 base on R3's instrument). Two levers have failed without it.
   - **(iii) A longer or stronger court practice:** more iterations, a higher LR, or the fall penalty added.
   - **(iv) Put the facts to the user:** R3's court read keeps the random-spawn scramble the user removed from the rally start. Should R3 also use the set start? This is the user's premise, never a panel loosening.
   - **(v) Other.**
3. **The target.** What is the honest estimate for both bars now, and what should the user be told?
