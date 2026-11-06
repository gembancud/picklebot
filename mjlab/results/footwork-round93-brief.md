# Panel round 93 brief: D-231 lifts P(5+) to 0.7236 on the set-start read; NO-CANDIDATE on R3 alone, 2026-11-06

Read first:
- D-231 and its result in docs/DECISIONS.md;
- round 92 in mjlab/results/footwork-review.md;
- results/dr92-summary.txt;
- the frozen target (results/rally-target.md, with the D-228 / D-229 set-start read);
- how R3 is read (the h5f court read: Picklebot-Latent-Court-Res-G1, 2,048 envs, 24 s, random recovery spots, mean actions).

## Result

**R = rally-d1s3dr** (C + the drill reset in training; model_33797):

| line | R | C | verdict |
|---|---|---|---|
| P(5+), new read, dev 4220385-4220388 | **0.7236** (Wilson 0.712-0.735) | 0.5645 | GAIN2 +15.9 (lower bound +14.3), every seed +15 to +17 |
| H0 / FEEDER / K3-KEPT | 0.146 / 0.857 / 0.0243 | 0.245 / 0.762 / 0.0269 | pass |
| r19 guards | worst family -3.9; L+B -3.5 | | pass |
| bars | ready 0.532; falls / 1,000 hits 0.17 | | pass |
| **R3 court falls per episode** | **0.0575** (dev 4220389) | 0.0556 (dev 4220365) | **FAIL (<= 0.04)** |

- **Hazards on the new read:** R 0.146 / 0.107 / 0.037 / 0.012 / 0.003. So (1-h0)(1-h1) = 0.762, against about 0.87 needed.
- **Old read, same seeds (reported):** R 0.390 vs C 0.406 (-1.6).
- **Pairs-read falls (reported):** R 0.0097 vs C 0.0245.

**Verdict: NO-CANDIDATE on R3 alone. CONFIRM did not run, and C stays the parent.**

**The target, as it stands:**
- P(5+) >= 0.80 with Wilson low >= 0.78 on the new read: best shown 0.72.
- R3 <= 4 %: C and R both read about 5.6-5.8 %.

R3 has never been targeted by a lever.

**Resources:**
- The GPU is free.
- The CalTennis pilot (GVHMR -> GMR on the session on disk; D-229's reference route) runs now as a CPU / GPU read, not training.
- Training seeds: next free 230.
- Dev seeds: next free 4220390 (4220340 held; CONFIRM 4220349-4220356 unread).

## Questions

1. **Correction check.** Is NO-CANDIDATE valid? Is anything misstated?
   - Is R3's read the right instrument for the target's "court falls" (24-s episodes, random spots), given the set-start pairs read now shows R's falls at 1 %?
   - Do not re-score; say only whether a read definition is in error.
2. **Next step.** Vote, with one change, parent, lines and seeds:
   - **(i) A falls lever toward R3,** on R or on C. For example:
     - a fall penalty or a stability term;
     - training under the court read's conditions;
     - the anchor.
     
     Name the parent and why. Using R as a parent needs a gate it has not passed; say how that is handled honestly.
   - **(ii) Continue the opening climb** toward 0.80 and treat R3 as its own later phase. Say how that squares with the gate.
   - **(iii) The damping premise read, or the reference-motion route** (the pilot's outcome is reported when it lands).
   - **(iv) Other.**
3. **The target.** With 0.72 and R3 at about 5.7 %, what is the honest estimate now, and what is the shortest route to both bars?
