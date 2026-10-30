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

## Round 52 (2026-10-31): fw1c-A killed on noise; mean-action reads pass

**Inputs:** results/footwork-round52-brief.md.

### Correction checks

| Reviewer | Finding |
|---|---|
| RL | KILL-no-settle read the behaviour policy: noise, not skill. footwork_eval passed falls=None, so the coded verdict was MIXED and "BODY-OK" was worked out by hand. |
| Motion | The same falls=None fault. By hand, 0.29 per 1,000 env-s (A 0.45). |
| Coach | The driver naming bug; otherwise D-181 was right. |
| Experiment design | The JSONs say MIXED. The naming bug also reused the run name. Seeds 4220210 / 4220211 were not ledgered. The D-entry was missing. |
| Architecture | The naming bug crashed the summary, so fw1c-summary.json was never written. stage2_eval also turns observation corruption off, so the gap is not action noise alone. |

### Votes

5 of 5 for (a): confirm on a frozen mean-action read, then step 2's premise checks. 5 of 5 for teacher model_16600:
- A is a killed arm;
- B0 settles in time more often in all 8 sectors;
- A clusters 38 of its 55 falls at back-left.

(b), entropy 0.001 as a run, was rejected (RL, experiment design, architecture). It is kept as the setting for any later fine-tune.

(c), the heading limit, is gated on evidence:
- **Coach:** a mid-move heading counter; more than 20 % of back moves turned more than 90° means the heading limit first.
- **Motion and experiment design:** the clips' direction rule.

### Decision

D-182.

## Round 53 (2026-10-31): DECODER-OK is blind to travel

**Inputs:** results/footwork-round53-brief.md.

**Correction checks.** All five agree that D-183's premise metric ("success") was wrong. Its z-only anchor termination cannot see ground travel; D-176 had already said so. The printed verdicts stand, but they do not answer the question.

**Is the 0.54 ratio real?** All five say very likely:
- global MPKPE agrees with the speed gap, and it is a position quantity;
- the reference velocities are correct;
- the fps chain is correct;
- the same ratio appears in the D-175 ladder;
- H0's objective explains it: re-anchoring to the robot, an anchor kernel of std 0.3 and a lenient velocity kernel.

**Votes:** 5 of 5 for (c), the decisive check first. Then:

| Reviewer | After the check | Thresholds |
|---|---|---|
| Coach | (a) if ARTEFACT, (b) if a gap | 0.85 / 0.70 |
| Experiment design | 0.95 / 0.90 lines, a TR instrument check, and the LAFAN control reported | 0.95 / 0.90 |
| RL | route (b), data-only or an objective change depending on the LAFAN control | 0.85 / 0.70 |
| Motion | the displacement ratio, a slip-by-friction CONTACT line, and an objective change in (b) | 0.85 |
| Architecture | the displacement ratio at 1 s and at the end; (b) with a full-3D anchor termination | 0.9 / 0.8 |

**Decision (D-184):** the panel median, 0.90 / 0.80, with experiment design's instrument check, motion's CONTACT line and RL's LAFAN control for the sub-route.

## Round 54 (2026-10-31): route D's H0 fine-tune

**Inputs:** results/footwork-round54-brief.md, with the travel check at TRAVEL-GAP / OBJECTIVE.

**Correction checks**
- D-184 stands (all five).
- Experiment design: the brief's 5-point stroke guard was a loosening; H0's is 3 points (D-079).
- Architecture: s5c-03b stopped on the wall cap at 2,783 iterations; the merge_motions clip_source trap.
- Motion: the stance-slip measure is not the import's skate measure. Robot slip is about 4x the tennis reference (a gait habit).
- RL: the actor sees the lag only through ±0.25 m noise.

**Votes**

| reviewer | objective | data | iterations | bridge |
|---|---|---|---|---|
| RL | O1 | hold out | 3,000 | first (≤ 1.2 m/s p95 = cap) |
| Motion | O1 | hold out | 5,000 | first |
| Coach | O1 | add | about 2,000 | first |
| Experiment design | O1 | add (freeze the share) | 10,000 | in parallel (ratio to the specialist ≤ 0.65 / ≥ 0.85) |
| Architecture | O1 (O2 fallback) | add, tennis 0.5 | 3,000 | 22b fast-move read now; a zero-shot H1′ swap later |

**Decision:** D-185.
