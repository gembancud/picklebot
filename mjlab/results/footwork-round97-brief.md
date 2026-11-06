# Panel round 97 brief: D-236 NO-CANDIDATE on the left + back guard alone; R3 and P(5+) pass, 2026-11-06

Read first:
- D-236 and its result in docs/DECISIONS.md (the newest entries);
- round 96 in mjlab/results/footwork-review.md;
- results/lc98-summary.txt (the gate output) and results/dr92-summary.txt (R's gate, D-231);
- the frozen target (results/rally-target.md);
- docs/PANEL.md.

## Result

**M = rally-d1s3drl3 model_34996:** the launcher-court run continued from model_34160, endpoint read on the frozen set-start read, dev 4220385-4220388.

| line | M | needed | pass |
|---|---|---|---|
| P(5+) gain over C | +18.10 points (lower bound +15.73) | > 0 | yes |
| P(5+) | 0.7454 (R 0.7236, C 0.5645) | R-KEPT >= 0.7036 | yes |
| R3 (dev 4220398) | **0.0271** (R 0.0596 on the same seed) | <= 0.04 | **yes** |
| H0 / FEEDER / K3-KEPT | 0.128 / 0.875 / 0.0276 | | yes |
| Worst family contact | +7.8 | > -5 | yes |
| **Left + back feeder contact** | **0.4051 vs 0.4557 (-5.1)** | > -5 | **no** |

**Direction contact:**

| | left | back | forward | right |
|---|---|---|---|---|
| M | 0.346 | 0.568 | 0.914 | 0.783 |
| C | 0.407 | 0.584 | 0.918 | 0.777 |

R (D-231) read -3.5 on the same guard. The direction read pools about 1.5k left + back feeds, so the 1.6-point drop from R is about one standard error. The plausible cause is D-235's form: the move and swing drill dose halved.

**The target still needs:** P(5+) >= 0.80 with Wilson low >= 0.78; M is at 0.745. Per-shot hazards: M h0-h4 0.128 / 0.096 / 0.040 / 0.012 / 0.003. The opening shots dominate.

**Resources:**
- Training seeds from 238. Dev seeds from 4220402 (4220399 and 4220349-4220356 unread).
- The CalTennis motion pilot is starting on the free GPU: GVHMR to the G1, footwork between strokes, about 2.5-3.4 m/s lateral after body scaling. It is a source of fast left and right footwork references, not yet a lever.

## Questions

1. **Correction check.** Is NO-CANDIDATE right as coded? Any defect in D-236's reads or lines? (Never loosen the guard.)
2. **Next.** Vote, with one change, parent, lines and seeds:
   - **(i) Restore the drill dose:** the D-235 form again, with the move and swing chances raised on the remaining drill courts (capped at feasibility), or launcher courts taken elsewhere. Warm start R or M?
   - **(ii) M continued with a left / back move-drill emphasis** (move_sector_weights). A targeted fix of the one failing guard; the parent is M (unpromoted, as R was).
   - **(iii) Accept M as the unpromoted warm start** and go to the opening lever (h0, h1), since P(5+) needs about 5.5 more points. The guard must then pass at that run's gate.
   - **(iv) Other.**
3. **The target.** What is the honest estimate, and what is the next binding lever?
