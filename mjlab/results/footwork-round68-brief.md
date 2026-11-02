# Panel round 68 brief: d1s7 (restart state as an input) reads NO-DOSE; the feeder premise ends, 2026-11-02

Read first:
- D-203 and its result in docs/DECISIONS.md;
- round 67 in mjlab/results/footwork-review.md;
- mjlab/results/d1s7-summary.txt (and .json);
- mjlab/results/rally-target.md.

## Result

d1s7 = the d1s3 child (model_31399) widened with 5 trailing restart inputs (parked, partner parked, court dead, next receiver, countdown), trained 1,200 iterations on d1s3's task with no reward change. Endpoint model_32598. Verdict **NO-DOSE**, which also gives NO-USE (no DOSE dimension passed).

**The run was clean:**
- INVALID ok;
- smoke falls 1.20, with gradient on the new columns;
- +360: falls 1.14, legal_return 0.849, rally length 3.80 vs 3.26, speed kept (left / back 1.63 / 1.79).
- New-column weight norms at +360: actor 0.67, critic 7.83. The critic leans heavily on the inputs.

**Endpoint vs parent:**

| measure | child | parent (4220326) | parent retest (4220330) | line / result |
|---|---|---|---|---|
| DOSE: pelvis speed p50 at the fire | 0.261 | 0.278 | 0.288 | need -0.05: fail |
| DOSE: recovery distance p50 | 0.851 | 0.893 | 0.855 | need -0.10: fail; the retest equals the child |
| F-UP: feeder legal | 0.619 | 0.629 | | fail |
| F-BIN: 0-1 launch bin | 0.725 | 0.751 | | fail |
| F-BAND | 0.901 | 0.905 | | fail |
| P5-KEPT: P(5+) | 0.396 | 0.387 | | kept |
| REFEED3 | 0.755 | 0.756 | | kept |
| K3-KEPT | 0.967 | 0.959 | | kept |
| AGILE-KEPT: R_LB | 0.832 | 0.824 | | kept |
| h5f court falls | 6.5 % | 6.2 % | | target 4 % |

**GUARDS: breached.**
- backhand contact 0.586 vs 0.675 (-8.9);
- fast contact 0.453 vs 0.514 (-6.1);
- left + back -2.1 (ok); cross_forehand +4.9.

**Failure rate by shot position, ball 0-4:**

| | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| parent | 0.382 | 0.287 | 0.082 | 0.028 | 0.010 |
| child | 0.387 | 0.296 | 0.063 | 0.008 | 0.011 |

## Standing facts

- **Stop rule (D-203, set before launch):** NO-DOSE or NO-USE ends the feeder premise, with no fourth feeder lever. Four levers failed: d1s4 (readiness at events), d1s5 (rally cap 5), d1s6 (parked readiness), d1s7 (restart observation).
- **A pattern, not yet tested:** every d1s3 continuation (d1s4, d1s6, d1s7), whatever the change, breaches backhand and/or fast contact by 6-12 points. No pure continuation control has been run (it runs only on F-UP). It could be drift from 1,200 more iterations on d1s3's task, not the changes.
- **P(5+) is set by the opening exchange:** feeder 0.38 and first handed ball 0.29 account for about 87 % of the log shortfall; after ball 3, about 0.003 per shot.
- **Court falls are 6.2-6.5 %**, against the target's 4 %. The target also needs P(5+) >= 0.80 and sides within 3; M1 feeder 85 %.
- **Raised with the user (no answer yet):** the frozen target read refeeds 0.5 s after a rally ends. A 3-s refeed gives feeder 0.76 and P(5+) 0.55. The panel does not change the target.
- **Queued:**
  - the first handed ball (29 % hazard; the receiver's state is not logged by handed-ball index; `--audit-fixes` volley counting off in reads);
  - the falls lever;
  - coach's FIRST-STEP read;
  - d1 + --recover; d1b; the Fast4 floor test (dev 4220248); H1''.
- The GPU is idle.

## Questions

1. **Correction check.** Is NO-DOSE robust? Look at the retest numbers and the critic norm. Is there anything about d1s7 the brief gets wrong?
2. **The guard pattern.** Should a pure d1s3 continuation (no change, training seed 197 as in D-203's control) run first, so every later child has a drift reference? Is the guard against the static parent the right reference for a 1,200-iteration child?
3. **Next step.** Vote, with coded lines and seeds:
   - **(i) The first handed ball:** a diagnostic read first (log miss rate and incoming-ball / receiver state by handed-ball index; CPU-cheap code, one GPU read), then a lever.
   - **(ii) The falls lever** (court falls 6.2 % -> 4 %).
   - **(iii) The drift control** (a pure continuation), as a reference for everything after.
   - **(iv) The agility queue:** Fast4 floor test, d1 + --recover, d1b, H1''.
   - **(v) Other.**

Seeds: dev free 4220328-4220329 and from 4220331; training from 199.
