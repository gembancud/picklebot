# Panel round 60 brief: the d1 teacher check stopped on TEACHER-SLOW, 2026-10-31

Read first:
- D-192 and the D-191 result in docs/DECISIONS.md;
- round 59 in mjlab/results/footwork-review.md;
- picklebot_mj/d1_rule.py;
- results/d1-summary.txt, results/d1-teacher-{fw,walker}.{json,log};
- results/fwfast4-summary.txt.

## What happened

scripts/diag/d1_base.sh ran its pre-launch teacher check (dev 4220249).
- fw1b-S model_16600 and the old walker model_15900 ran on Picklebot-Footwork-Measure60-Court-G1: the kickstart's own MoveDrill geometry, 0.5-3 m spots inside the half court, 60-s episodes, mean actions, 1,024 envs, 120 s.
- The line (experiment design, adopted in D-192): in both left and back, fw1b-S's sustained p50 must be >= 1.6 m/s and >= the walker's + 0.3.
- Verdict **TEACHER-SLOW**. The driver stopped as coded; nothing was trained. The GPU is idle.

| per sector (F, FL, L, BL, B, BR, R, FR) | fw1b-S | walker 15900 |
|---|---|---|
| sustained p50, best full 1-s window (m/s) | 1.05 1.05 **1.07** 1.04 **1.00** 1.00 1.08 1.05 | 0.82 0.84 **0.84** 0.79 **0.76** 0.78 0.84 0.82 |
| peak p50 (m/s) | 1.38 1.45 1.52 1.39 1.31 1.35 1.48 1.45 | 0.97 1.03 1.11 0.99 0.95 0.98 1.09 1.01 |
| first step, time to 1.5 m closer, p50 (s) | 1.40 1.37 1.36 1.38 1.41 1.37 1.37 1.38 | 1.77 1.74 1.71 1.74 1.82 1.75 1.72 1.77 |
| settled share | 0.19-0.34 | 0.00-0.02 (the walker rarely makes the deadline) |
| untimed arrival (worst) | 0.966 | 0.986 |
| falls per 1,000 env-s | 0.090 | 0.008 |
| fallen + censored share | 0.055 | 0.057 |

fw1b-S's speed against the walker:
- sustained +0.23 m/s;
- peak +0.4 m/s (about +40 %);
- 0.35-0.41 s faster over the first 1.5 m (about 21 %).

## The likely reason (to be checked, not assumed)

On 0.5-3 m spots a move is mostly acceleration and braking:
- fw1b-S needs about 1.4 s to close the first 1.5 m;
- on its own 3-5 m Measure60 spots it sustains 1.9-2.1 m/s (D-183), and 2.1-2.4 m/s on 4-6 m spots (D-191);
- so the best full 1-s window on court-length spots cannot be near 1.6 m/s for either teacher.

The 1.6 m/s line was set from the long-spot reads, so it may be mis-calibrated for this geometry. Experiment design also argued it was a premise check: does the kickstart drill ask for speed at all? Judge which reading is right.

## Context

- The ceiling test (D-191 result) read **MIXED**:
  - Fast4 child 2.35-2.53 m/s sustained on 4-6 m spots (+0.22 min(L, B, R));
  - falls 9x fewer;
  - first step about 0.1 s slower than fw1b-S.
- P2 (D-191): the rally composite with the speed reward was safer but not faster; the frozen base is the cap.
- Round 59 correction: s5c-18 copied the walker only in move-to-spot episodes (no `--recover`).
- The P(5+) bound (D-189): footwork alone gives about 0.5; the first handed balls are the bigger leak.
- Stage 2 issues found while coding (to be ruled on before any re-climb):
  - 22b model_30200 already fails rally_check's D-160 family guards against run 14 (reach_deep -34.7, left + back -9.2; results/rally-22b-early-*.json), so "r19-gate unchanged" would fail on guards whatever footwork does;
  - 22b's task does not log move arrival, so a training-log KILL-NO-ARRIVE has no source (an early read at a saved checkpoint would be needed).
- The user wants agility to keep rising toward 3-4 m/s, and the rally target still governs (rally-target.md).

## Questions

1. What does TEACHER-SLOW mean here?
   - (i) The premise failed: the kickstart drill never asks for speed, so d1 as specified can't make a fast base.
   - (ii) The line was mis-calibrated for 0.5-3 m spots, but the premise holds on first-step and peak speed.
   Say which, and what evidence would separate them.
   Rules: never loosen a threshold; the drill is not swapped quietly.
2. Options. Vote, and give coded lines and seeds:
   - **A.** Launch d1 as specified (fw1b-S, the s5c-18 recipe), recording the teacher check as failed. The base gate (R_LB, first step, retention) judges the outcome.
   - **B.** d1 with the kickstart's move episodes on the specialist's drill geometry (FootworkDrill, 1-5 m spots in the Fast25 box) instead of MoveDrill. That is two changes (teacher and drill); the base gate is unchanged.
   - **C.** A new, pre-registered premise check on a geometry-fair metric (first-step time or peak; for example, fw1b-S first-step p50 <= walker - 0.25 s in L and B). It would be read on fresh seeds before any launch, because the current data has already been seen.
   - **D.** Leave footwork for now and turn to the first-handed-ball levers (experiment design's direction x ball-index read).
   - **E.** Other.
3. If d1 goes ahead in any form: rule on the stage-2 issues (the guard reference, the KILL-NO-ARRIVE source).

Seeds:
- dev next free 4220266;
- reserved: 4220248 (Fast4 floor), 4220250-4220256 (d1 base gate, unused), 4220257-4220265 (stage 2);
- training: 184-187 reserved (unused), next free 188.
