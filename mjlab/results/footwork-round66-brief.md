# Panel round 66 brief: the d1s5 smoke stopped on falls (SMOKE-FAIL), 2026-11-02

Read first:
- D-201 in docs/DECISIONS.md;
- round 65 in mjlab/results/footwork-review.md;
- mjlab/results/d1s5-summary.txt.

## Result

d1s5's pre-registered smoke (training seed 194, 1,024 envs, 40 iterations, `pair_rally_cap` 5) read **SMOKE-FAIL**:
- falls per 1,000 env-s **4.398**, against the line 4.157 (1.5 x run 14's smoke, D-170);
- exit 0, no traceback, std 0.106, config ok (cap 5 present, d1 base, fast-move term).

Earlier smokes of the same parent family on the same line:

| run | smoke falls per 1,000 env-s |
|---|---|
| d1s2 | 2.82 |
| d1s3 | 3.27 |
| d1s4 | 2.61 |

Nothing was trained. The GPU is idle.

**Plausible mechanism (not measured):** with the cap, rallies end after 5 shots and the next feeder ball comes 0.5 s after both robots park. So more feeder balls arrive while the receiver is still moving: the state ballidx63 found fails, and now possibly falls as well. A 40-iteration, 1,024-env smoke is also noisy; its spread has never been measured.

**Rules:** never loosen a threshold, and never re-roll a smoke until it passes.

## Questions

1. **Correction check.** Is the smoke falls line valid under the cap? The episode length is unchanged (120 s); cap restarts are not resets.
2. **Next step.** Vote, with coded lines and seeds:
   - **(i) Accept the stop for (c).** Go to round 65's runner-up, **(b) parked readiness**: a court_dead & parked mask, excluding busy and young episodes, weight 2, d1s4's stds, paying no readiness at contacts (motion and architecture's lines).
   - **(ii) Pre-register a smoke-noise read** before deciding: for example, the parent's own smoke (d1s3's task, no cap) on 3 fresh training seeds, plus the capped smoke on the same 3 seeds. The rule would be fixed before the reads. Then (c) continues only if the capped mean <= 4.157 and is within the parent's spread.
   - **(iii) (d)**, observing the restart: parked, countdown and the next receiver (RL).
   - **(iv)** Other.

Seeds: dev next free 4220328 (4220306-4220327 reserved for d1s5's reads, unused by the child); training next free 195.
