# Footwork phase panel rounds

## Round 51 (2026-10-31): fw1b-S ran through spots

**Inputs:**
- D-179 and D-180;
- fw1b-S's training counters (results/fw1b-S.jsonl);
- the diagnostic read of model_16600 (results/fw1b-S-diag-measure.txt: sustained 1.85 F / 1.92 L / 2.10 B / 1.92 R m/s, untimed arrival 0.33-0.41, censored 0.25).

### Correction checks

| Reviewer | Finding |
|---|---|
| RL | D-180's optimiser fix was right, but its kill line was never enforced: it was a comment, checked by hand. Enforced, it fires at about iteration 300 (0.425), not 726. Noise grew while nothing paid precision: action std 0.32 → 0.51, entropy 2.9 → 19.3, yaw tracking halved. |
| Motion | The kill was right. Many failed spots are hovering inside 0.4 m without settling (ready_stance rose 0.33 → 0.53), not only running through. Noise growth makes the 0.3-s hold harder. Back faster than forward is a red flag: turn-and-run, lunge or skate? |
| Coach | The defect was in D-179's design (first_entry inherited from D-172). A pays a robot that overshoots by a metre and walks back, so log overshoot. |
| Experiment design | Applying the kill was correct. "VOID-unstable" names the wrong cause; it should say kill line, reward defect. The censored-share gate cannot pass at 20-s episodes (a perfect policy censors about 12-14 %): this is the false D-179 premise. |
| Architecture | The partial-window bias: sustained speed was booked before the 1-s window filled, so a spot issued at speed books carried-over speed. Fix it before the next read. Run-through does not inflate the read directly: speed toward the spot goes negative after the pass. The measure read is VOID by construction at 20 s. |

### Votes

| Reviewer | Vote | Parent | Notes |
|---|---|---|---|
| RL | B | model_15900 | 16600 carries the noise drift. Kill lines: std > 0.45, deadline share < 0.15 at 30 %. |
| Motion | A | model_16600 | 1,500 iterations. Early check at 30 %; SA deferred; clip checks with mean actions before step 2. |
| Coach | A | model_16600 | "Arrive in time, then be balanced" is the right skill. Next drill change: heading at most 90° from the net. |
| Experiment design | A | model_16600 | 774 iterations. Measure episodes of 60 s and a 250-300-iteration read; baseline re-read of 16600. Kill lines K-unstable / K-dose / K-speed. |
| Architecture | A | model_16600 | Pay inside FootworkDrill (deadline_drill.py untouched); instrument fix plus 60-s measure episodes before launch; 6 tests. |

### Decision (D-181)

A, by majority (4 of 5):
- the settled in-time arrival pays;
- continued from model_16600 for 1,500 iterations;
- instrument fixes before launch;
- kill lines enforced in code;
- SA deferred.

### Disagreements, recorded

- **Parent (RL).** RL wanted a clean restart, because the drift in 16600 confounds the fix. If A's action std keeps climbing, RL's next single change is entropy_coef 0.001.
- **Iteration budget (experiment design).** Experiment design wanted 774 iterations, for 1,500 in total.
- **Kill lines (experiment design).** Experiment design wanted the D-180 line retired in favour of a dose line. The majority kept it.
