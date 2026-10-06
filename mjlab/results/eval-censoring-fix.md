# Evaluation fix: feeds cut off by the robot-episode time limit were counted as misses (D-043)

Date: 2026-10-06. Found while scoring the hitting teacher.

## The bug
- In every evaluation since the feeding machine (Stage 4 run A3), each robot episode ends at a fixed time limit (8 s).
- At that reset, the feed then in progress was tallied as a finished feed. A ball still in flight, not yet hit, counted as **no contact and no legal return**.
- The robot never had a chance at those balls, so contact and legal-return rates for every checkpoint since A3 are **biased low**.
- The bias depends on the policy's timing: more feeds per episode and longer rallies mean more cut-off feeds.
- Training is unaffected: rewards never used these tallies.

## Evidence (dev seed 4,200,141; Stage 4 families; target A; 1024 envs × 16 s; `artifacts/eval/censor_check.py`)
| Policy | Feeds | Contact (old) | Untouched feeds cut off by the time limit | Contact, completed feeds | Legal, completed feeds |
|---|---:|---:|---:|---:|---:|
| Hitting teacher `teacher-hit-01/model_14200` | 7,715 | 79.5 % | 1,568 (20.3 %) | 99.7 % | 97.2 % |
| Stage 4 `aim-all-c01/model_7600` | 6,885 | 88.9 % | 742 (10.8 %) | 99.6 % | 91.6 % |

The "contact ceiling of 85–90 %" reported since Stage 4 run A3 was mostly this artefact.

## The fix
- At a reset, a feed that is still open (not tallied) and not ended by a fall is counted as **censored** and excluded from every rate. A feed ended by a fall still counts.
- `stage2_eval.py` reports `censored_feeds`.
- Test: `test_feed_cut_off_by_time_limit_is_censored_not_missed`. Suite 168 pass + 13 xfails.

## Consequences
- **History is not relabelled.** The committed JSON and reports keep their original numbers.
- New evaluations use the corrected metric. Where a gate compares against an old checkpoint, the old checkpoint is **re-evaluated with the corrected metric on the same feeds**, as the hitting-teacher retention comparison already does.
- **Earlier gate outcomes may have been affected:**
  - the Stage 4 gate (missed by < 1 point on three families);
  - Stage 5 F1 and F2;
  - the Drill 1 retention checks.

  These are not re-litigated automatically. A corrected re-score of the Stage 4 candidate is the recommended first check if the user wants to revisit D-040.
- **The thresholds are unchanged.** They now measure what they were meant to.

## Hitting teacher with the corrected metric (dev seed 4,200,140)
- **Legal return:** 98.4–100 % on 10 of 11 families; backspin 83.6 %.
- **Contact:** 98.9–100 %.
- **A/B gain:** +0.820 [0.815, 0.825], every family > 0 (backspin +0.12).
- **Retention vs `model_7600`** (both corrected, fixed start): 95.9 % vs 97.4 %. Backspin −13.6 and backhand −4.9; the others within ±3.2.
- **Gate:** only backspin fails, on legal (< 85 %) and retention (> 5 points).
