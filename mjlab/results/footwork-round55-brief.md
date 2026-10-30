# Panel round 55 brief: h0-fw-01 killed at +900 (2026-10-31)

Read first: D-185 in docs/DECISIONS.md, mjlab/results/footwork-review.md (round 54), picklebot_mj/h0fw_rule.py, scripts/diag/h0_fw01.sh, results/h0fw01-kill.txt, results/h0fw01-kill*-{child,parent}.json.

## Context

- The bridge prints **CAP-INHERITED** (results/fw2b-summary.txt). Rally run 22b's composite sustains 1.16-1.45 m/s in every sector against the specialist's 1.88-2.10; left / back R = 0.636.
- h0-fw-01 was trained from s5c-03b model_63300 on tennis-lafan3 + footwork-fast, shares 0.5 / 0.125 / 0.125 / 0.25. The one objective change was O1: motion_global_root_pos std 0.3 -> 1.0. The learning rate was a fixed 1e-5, with 900 iterations in segment 1 (checkpoint 2026-10-31_06-12-41_h0-fw-01/model_64199).

## Kill check (coded, D-185): **KILL**

Reads are paired with the parent: dev seed 4220220 (footwork-fast) and 4220221 (tennis-lafan3).

| line | value | limit | |
|---|---|---|---|
| D_fw (footwork-fast FAST) | **0.808** (parent 0.496) | >= 0.70 | ok |
| D_lafan (LAFAN1 FAST) | **0.781** (parent 0.736) | >= 0.80 | **KILL** |
| footwork-fast FAST success | 1.000 | >= 0.90 | ok |
| worst stroke - parent | -0.011 | >= -0.10 | ok |
| S_fw - S_parent | +0.016 | <= +0.05 | ok |
| falls / parent | 0.90 | <= 2 | ok |

**Travel by clip family** (scripts/diag/h0fw_breakdown.py; D = median robot / reference displacement; FAST = reference >= 1.0 m/s):

| family | child FAST | parent FAST | child slow | parent slow |
|---|---|---|---|---|
| footwork_fast | 0.808 | 0.496 | 0.821 | 0.500 |
| LAFAN run | 0.814 | 0.773 | 0.877 | 0.801 |
| LAFAN run, mirrored | 0.817 | 0.782 | 0.778 | 0.778 |
| LAFAN sprint | 0.774 | 0.736 | 0.727 | 0.688 |
| LAFAN sprint, mirrored | 0.758 | 0.710 | 0.661 | 0.633 |
| LAFAN walk | 0.741 | 0.692 | 0.778 | 0.734 |
| LAFAN walk, mirrored | 0.731 | 0.698 | 0.733 | 0.711 |
| fightAndSports | 0.718 | 0.557 | 0.740 | 0.721 |
| fightAndSports, mirrored | 0.642 | 0.597 | 0.671 | 0.706 |
| tennis | n/a | n/a | 0.676 | 0.625 |

Reading:
- O1 + data moved the target skill a lot: footwork-fast went 0.50 -> 0.81. footwork-fast is now in-sample.
- On unchanged data (LAFAN1), O1 moved every family by only +0.02-0.16 in 900 iterations at a fixed 1e-5.
- Tennis travel is 0.68 vs 0.63; strokes are within 1.1 points.
- The kill is binding. The run is stopped and is not relabelled.

## Questions for round 55

1. **Correction check** on D-185, its kill line and the implementation.
   - Was 0.80 on LAFAN1 at 30 % well calibrated? RL's round-54 trajectory argument gave 0.65 for footwork-fast, and 0.80 was its LAFAN figure.
   - Any implementation fault? For example, the kill checkpoint is model_64199, not 64200.
2. **What the result means.** Is O1 too weak, too slow (learning rate / iterations), or the wrong lever on its own? RL noted in round 54 that the actor sees anchor lag only through ±0.25 m observation noise, which is about the size of the kernel.
3. **The next single change, and its parent.** Options:
   - (a) O1 stronger, e.g. weight 0.5 -> 2.0;
   - (b) O2 (full-3D anchor termination at 0.5 m), from model_64199 or from model_63300;
   - (c) the anchor observation noise ±0.25 -> a smaller value (observation change);
   - (d) a higher fixed learning rate (3e-5);
   - (e) a longer run of the same O1 + data. This is not allowed as a continuation of the killed run, only as a new pre-registered run with a reason;
   - (f) other.

   Give coded kill and endpoint lines. The endpoint stays D_fw >= 0.90 and D_lafan >= 0.90, with retention 3 points (D-185). Never loosen.
4. **Is the LAFAN1 line the right endpoint for the rally goal?** Bear in mind that fightAndSports and walk windows include turning and stop-start. Any change of endpoint must name the premise that changed and must not be a loosening. Experiment design: rule on this.

Seeds: dev 4220222-4220224 were allocated to h0-fw-01's endpoint and are released unread; spares 4220227-4220229; next free 4220230. Training seeds from 174.
