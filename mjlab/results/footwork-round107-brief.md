# Panel round 107 brief: D-246 KILLED by KILL-LOST-OPEN (the harder mix), 2026-11-08

Read first: D-245 and D-246 at the end of docs/DECISIONS.md, with round 106's addendum (RL's recorded risk) in mjlab/results/footwork-review.md; results/lc108-summary.txt, results/lc108-kill.txt, results/lc108-train-share.jsonl, results/lc105-train-share.jsonl; docs/PANEL.md.

## Result

D-246 = rally-d1s3q8w2b: Q + feed-mix x2 on reach_deep, cross_backhand and reach_backhand (30 % of pair-court feeder balls, against 15 % for Q). Smoke passed all 8 lines (feeder share 0.1626 against 0.1642 predicted). Kill at +240, training-log lines first:

| line | read | needed | result |
|---|---|---|---|
| **KILL-LOST-OPEN**: reset-half training (1-h0)(1-h1), +181-240 | **0.6869** (free half 0.4832) | >= Q's 0.7356 - 0.02 = 0.7156 | **KILL** |
| KILL-UNSTABLE | 0.934 | <= 3.14 | pass |
| config | all three weights, cap 8 set-start only | | pass |

Training was stopped at iteration 37046 (+253); checkpoints exist to model_37040 (+247). No dev reads were taken (the dev kill reads come after the training-log lines).

**This is the ambiguous case RL recorded before the run.** The line compares the child's training opening on a harder ball mix with Q's on Q's mix. Reset-half training windows:

| window | Q (Q's mix) h0 / h1 / open2 | D-246 (dosed mix) h0 / h1 / open2 |
|---|---|---|
| +1-60 | 0.141 / 0.193 / 0.694 | 0.178 / 0.222 / 0.639 |
| +61-120 | 0.126 / 0.130 / 0.760 | 0.165 / 0.168 / 0.694 |
| +121-180 | 0.128 / 0.138 / 0.752 | 0.158 / 0.173 / 0.696 |
| +181-240 | 0.138 / 0.147 / 0.736 | 0.166 / 0.176 / 0.687 |

Both runs rise by about 0.05-0.06 from the first window, and the gap (about 0.05-0.06) is there from the first 60 iterations. Rough mix arithmetic: in Q's gate read the three families miss about half their feeder balls and the rest about 4 %; doubling them in the mix should lower training (1-h0) by several points before any learning. So the line cannot tell a harder mix from forgetting. Nothing yet says whether the opening improved on the standard (read) mix.

**Resources:** the GPU is free. Training seeds from 256; dev seeds 4220434, 4220436, 4220437 were not read (4220435 holds Q's stage-0 read); 4220438+ free; the target-read block 4220425-4220433 is unread.

## Questions

1. **Correction check.** Is the KILL right as coded? Was the line right for this lever (the panel kept it in round 106 knowing the risk)?
2. **Next.** Vote:
   - **(a)** a diagnostic read of model_37040 on the read mix (frozen set-start pairs + direction on fresh dev seeds; reads only, no promotion) to see whether h0 fell on the standard mix, then decide;
   - **(b)** re-run the dose with KILL-LOST-OPEN re-referenced so it compares like with like (say how), or replaced by a direct dev read of the opening at +240;
   - **(c)** drop the dose; another lever (name it, with the simpler option).
3. **Target estimate**, briefly.

Under 250 words.
