# Panel round 85 brief: D-221 (first-step bonus specialist) reads KILL-NO-START at +470, 2026-11-05

Read first:
- D-221 and its result in docs/DECISIONS.md;
- round 84 / 84b in mjlab/results/footwork-review.md;
- results/qk84-summary.txt and results/qk84-train.jsonl;
- results/fwfast4-train.jsonl (Fast4's flat window, for contrast);
- picklebot_mj/tasks/footwork_specialist.py (FootworkDrill, fw_first_step);
- picklebot_mj/d1_rule.py (first_window, quick_kill, quick_check);
- the frozen target (results/rally-target.md);
- docs/PANEL.md.

## Result

**Smoke passed** on all five lines.

**Training (seed 220) was stopped by KILL-NO-START** at +470 (checkpoints to model_17000, +400). Falls stayed low.

The training-window first-step p50 (time to close 1.5 m, stochastic actions):

| iterations | left (s) | back (s) | bonus per spot |
|---|---|---|---|
| 0-100 | 1.381 | 1.461 | 0.077 |
| 100-200 | 1.342 | 1.434 | 0.084 |
| 200-300 | 1.328 | 1.443 | 0.090 |
| 300-400 | 1.306 | 1.418 | 0.097 |
| 400-450 | 1.307 | 1.376 | 0.100 |

The line needed each to be at least 0.10 s faster. It read 0.074 for left and 0.086 for back, so the kill fired as coded.

**Contrast with Fast4:** Fast4 stayed flat over 1,500 iterations, inside one 0.05-s bin. Here the start moved by about 0.02 s per 100 iterations, and the paid dose rose 30 %.

**Pre-registered reading (D-221):**
- A fail "with a flat training window" counts as STOP evidence.
- A fail with a moving window is a recipe limit.
- This window moved, but by less than the line.

**Not done:** the endpoint read (dev 4220373 is unread). No line has been re-scored.

**References:**
- fw1b-S reads 1.362 / 1.411 s at mean actions on Measure60-Court (D-213).
- The QUICK line is each at most fw1b-S - 0.25 s.
- A naive linear extrapolation of the training trend gives about 0.25-0.3 s over 1,500 iterations. That is not evidence.

## Stack and constants

- **The bonus:** clamp(1.6 - t, 0, 1) x 100 (the arrival bonus weight).
  - It is paid once per spot of at least 1.5 m.
  - At t ~ 1.35 s it pays about 25, against the settled-arrival bonus of 100 and the per-step tracking terms.
  - Bonus per spot is reported in raw units (before the weight). It averages over all spots, including short ones that pay nothing.
- **Algorithm:** stock PPO with the adaptive schedule (desired KL 0.01, initial LR 1e-5).

**Resources:**
- The GPU is idle.
- Training seeds: next free 222.
- Dev seeds: next free 4220374 (4220340 held; 4220349-4220356 CONFIRM only); 4220373 is unread.

## Questions

1. **Correction check.** Is KILL-NO-START valid as coded? Was the kill line well chosen for this lever: did the 0-100 window include fw1b-S's own early drift, and is 450 iterations enough for the adaptive LR? Is anything misstated? Do not re-score the line.
2. **Reading.** Under D-221's split, is this "flat" (STOP evidence) or "moving" (recipe limit)?
3. **Next step.** Vote with coded lines and seeds:
   - **(i)** A stronger dose of the same lever, as a new run: a larger bonus weight, or a steeper or earlier pay curve (for example clamp((1.6 - t) / 0.5, 0, 1)). Name the one change, its kill line and its gate.
   - **(ii)** A diagnostic read of model_17000 at mean actions on Measure60-Court, paired against fw1b-S on a fresh dev seed. Reported only; it cannot turn the kill into a pass. Use it to decide (i) or (iii).
   - **(iii)** STOP this sub-route and move to the next phase. Architecture's (d), a distil-then-PPO joint fine-tune of base and residual, is the untested lever experiment design named. Alternatively, report to the user that no faster start has been shown.
   - **(iv)** Other: for example, a different start signal such as a ready-stance or split-step pre-load reward. That would be a new lever.
4. **The target.** Has anything here changed the panel's view of whether the frozen target is reachable? The target itself is unchanged.
