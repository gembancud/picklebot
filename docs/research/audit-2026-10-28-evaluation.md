# Audit 2026-10-28: evaluation and metrics code

Scope: `mjlab/scripts/stage2_eval.py` + `stage2_eval.sh`, `scripts/diag/feeder_speed_envelope.py`, `scripts/rally_check.py` (every mode), `scripts/h5f_clean_eval.sh` -> `h5c_eval.sh` -> `h5f_clean_summary.py`, the pair bookkeeping (`picklebot_mj/pairs.py`, the ball term in `picklebot_mj/tasks/return_stand.py`), `results/rally-target.md`, `results/rally-milestones.md`, and the drivers `rally_run14.sh`, `rally_run18.sh`, `lr_sweep.sh` (plus 15-17 for the env-var check).

Method: read-only code review. I also recomputed metrics on CPU from the raw fields in `mjlab/results/*.json` (no mjlab/warp import, no GPU) and ran a small numpy simulation of the end-of-read censoring. The scratch scripts were not added to the repo.

## Bottom line

- **No miscount found that would have flipped a past kill or accept decision.** Several places look like they could go wrong but check out: the Wilson and bootstrap code, P(k+) from `len_hist`, the own-ball vs feeder split, the kill lines (they match their docstrings and the driver comments), the seed discipline and the env-var settings in drivers 14-18. Recomputing the metrics from raw fields reproduces every JSON value.
- **Three counting problems in the pair bookkeeping all push rally metrics down.** They are small today (about 1-1.5 points of P(5+) combined), but one of them grows to about 6 points at the target level. It could make a policy that truly meets the 80 % target read as "not met".
- **The biggest decision risk is statistical, not a code bug.** Runs 15, 16 and 17 were killed on "engagement" lines whose margins are about one noise SD. Reading the parent and child on the same seed gives no pairing benefit, so those comparisons are as noisy as two independent reads.

---

## Confirmed bugs

### 1. Rallies still in progress at the end of a read are dropped (length-biased), so P(5+) reads low. HIGH for the future target read, low for past decisions
- **Where:** `picklebot_mj/pairs.py:73-79` (`len_hist` is only filled in `_end`), `pairs.py:146-159` (`summary`). Nothing flushes in-progress rallies at the end of `stage2_eval.py`.
- **What:** a rally adds to `len_hist` only when it ends. A rally still running at 120 s is thrown away, even if it already has 5 or more good shots, which is a known success. Long rallies are more likely to be running at the cut-off, so the rallies that remain are biased toward short ones.
- **Evidence:**
  - Every pair read has `started.feeder - rallies` = 896-953 in-progress rallies (about 5 % of rallies; 1,024 courts). For run 14's target read: 926.
  - From the length histogram, about 20-22 % of court time is spent in rallies that already have 5 or more shots. That puts about 190-200 of the 926 dropped rallies at 5+ already. Counting them moves P(5+) from 18.73 % to about 19.6 %.
  - A simulation (geometric rally lengths, 1.7 s per shot, 1.2 s restart, 120 s, 1,024 courts) gives the bias at different per-shot rates:

| Per-shot p | True P(5+) | Read as now | Counting in-progress rallies with 5+ |
|---|---|---|---|
| 0.70 | 0.168 | 0.155 | 0.161 |
| 0.90 | 0.590 | 0.545 | 0.580 |
| **0.96** | **0.815** | **0.750** | 0.805 |
| 0.97 | 0.859 | 0.799 | 0.855 |

  A policy that truly meets the frozen target (P(5+) about 0.81) would read about 0.75: "target not met". M2's P(3+) has the same bias. The per-robot streak count in `stage2_eval.py` (lines 284-297) already does this the right way: it counts a success the moment the streak reaches n.
- **Effect on past decisions:** small. Parent and child are read on the same protocol, and the bias only compresses differences slightly. Run 18's `sched-gate` and `early-sched` lines (P(5+) +2 points) get a little harder.
- **Confidence:** high (code plus data).
- **Cheap check:** add `rally_len` and `court_dead` at the end of the read to `summary()`, then count live courts with `rally_len >= 5` as successes. Or re-read one checkpoint at 240 s and watch P(5+) go up.

### 2. Volleyed-back shots never reach the pair counts. MEDIUM
- **Where:** `return_stand.py:984` calls `pairs.step(over, ...)` before `return_stand.py:987` / `1034-1039` (`_credit_early`). `pairs.py:103-111` only sees `over`.
- **What:** robot A hits and its own copy is still in flight. The partner then volleys it, and A "receives" while its feed is untallied. The term credits A with a legal return (the `_credit_early` docstring: "the ball was in play, so the return is legal"). `pairs.step` has already run for that step, and `_refeed` then replaces A's ball, so that shot is missing everywhere in the pair stats: `rally_len`, `side_stats`, `side_stats_own` and `court_counts`. The rally carries on, so its length is short by one per volley.
- **Evidence:** term `legal_returns - legal_landings` (= early credits) is 880-1,090 per contact-hand-off read and 560-605 per crossing read, which is 1.7-2 % of legal shots. For run 14's target read: 52,564 - 51,663 = 901.
- **Estimated effect for run 14:** P(5+) about -0.3 to -0.4 points (about 70 of the 989 length-4 rallies had a dropped shot), partner-ball legal about -0.4, feeder-ball legal about -0.2, mean length -0.05.
  - Run 14's feeder line (81.93 % vs 81.9 %) would only have risen, so no decision flips.
  - A policy that volleys more is penalized by the metric.
  - `rally-target.md` defines a good shot as "over the net, lands in". A volley-back never lands, so the definition itself is ambiguous.
- **Confidence:** high.
- **Cheap check:** in a short pair read, sum `early` per step and compare it with `sides` legal + `term.legal_returns`. The fix is to pass `early` into the pair counts (or a D-entry that defines a volley-back as not a shot, and then stops crediting it in the term too).

### 3. Reset order brings the "parked" env's ball back to life (phantom feeds). MEDIUM, not yet measured
- **Where:** `return_stand.py:441-470`.
  - In pair mode a reset calls `pairs.on_reset`, then `self.rules.lost(mk)` and `self.tallied |= mk` (lines 449-450), so the env "waits with no ball in play".
  - Then `self.rules.begin_from_feed(env_ids, ...)` at line 462 runs `_reset_common`, which sets the phase to `SERVE_FLIGHT` (not dead). Line 467 does the same for court-wide feeds. Lines 468-470 clear `tallied`.
- **What:** after every reset, the env that `pairs.parked` treats as having no ball actually holds a live feed (the fresh `_feed(env_ids)` ball). That covers all 2,048 envs at the start of a read and every fall during it.
  - If the court restarts while that ball is in flight, its outcome reaches `pairs.step`. A miss ends the new rally (often at length 0). A contact hands the ball to the partner, which replaces the partner's real feeder ball and early-credits it as a legal return in the term stats.
  - The phantom is classified with the stale `handed` flag from before the fall, so it can count as a partner ball.
  - At the start of a read this mostly just swaps one feeder ball for another (it is roughly harmless). After a fall it gives a court a second feed.
- **Size:** bounded by about 1,024 (start) plus about half of the falls (around 340 per read), out of about 70,000 shots. That probably means well under 1 point on any pair metric. The rest of `len_hist[0]` (393 rallies at length 0 in run 14 beyond the counted feeder misses) cannot be pinned on phantoms rather than partner falls from the JSON alone.
- **Out of scope but important:** the same code runs in training. With 30 s episodes, every time-out or fall leaves a phantom ball that the robot is rewarded for playing. A contact on it can pay the partner `legal_return` / `feeder_return_now` for a ball it never hit (`_credit_early`).
- **Confidence:** high that the order is wrong (code reading); the effect size is unmeasured.
- **Cheap check (after the GPU is free):** a 64-env, 10 s pair read that prints `rules.dead`, `tallied` and `pairs.parked` for a reset env over the next 50 steps. Or count `_tally` events on envs with `pairs.parked == True`. The fix is to apply `lost` and `tallied` after the `begin_from_feed` calls and the flag clear.

### 4. With the crossing hand-off, the hitter's out-balls are also counted as the receiver's misses. LOW
- **Where:** `pairs.py:89-99`. The exclusion for "the receiver's copy of a faulted return" exists only in the `contact` branch.
- **What:** with crossing, B receives A's ball when it crosses. If it lands out, both copies end on the same step and both count: A's fault and B's own-ball miss. That deflates own-ball legal in crossing reads. Today crossing is "reported" only (`*-target-crossing.json`). Earlier crossing-era numbers (Stage 5H R4 reads, and the "old R4 read reported alongside") carry this.
- **Confidence:** medium-high (code). It cannot be separated from the real hand-off effect in the JSONs.

### 5. `h5c_eval.sh` hides failed jobs from `h5f_clean_eval.sh`. LOW
- **Where:** `h5c_eval.sh:24-25`. The script's exit status is `h5c_summary.py`'s, not `$FAIL`. So `h5f_clean_eval.sh:35`'s `|| FAIL=1` misses a failed court or move job.
- **Effect:** `h5f_clean_summary.py:52` loads any file that exists, so a stale `stage5c-s5f-TAG-5c-court.json` would be used without warning. Per-run tags make this unlikely. A missing file makes `falls_court` None, and `rally_check m1` then crashes, which fails closed.

### 6. Misleading fall fields in `--rally` reads. LOW
- **Where:** `stage2_eval.py:312`, `345`.
- **What:** `--rally` stretches the episode past the read, so every robot episode ends in a fall and `robot_fall_rate_per_episode` = 1.0 (run 14 target: 675/675). `drill_v2.court_falls_per_episode` copies it. No gate reads these fields (gates use the court drill), but anyone reading the JSON will be misled.

### 7. Two "own" RNG streams share a seed. LOW
- **Where:** `return_stand.py:313` (`gen_court`) and `:322` (`gen_plan`), both `seed + 271829`, despite the "own stream" comment. Planner noise and court-feed draws use identical random sequences. This affects simulator realism, not counts.

### 8. `rally_check.py` exit and crash handling. LOW
- An unknown mode falls through to `target()` (`rally_check.py:424`), and `target` always exits 0.
- In every driver, `rally_check ... && pass || KILL` turns a Python crash (a missing JSON, a KeyError) into a kill. That fails closed, but a crash is reported as "KILL". In runs 14-17, the parent reads (`rally_run14.sh:28-31`, etc.) are not guarded, so a crashed parent read would have killed the child. Run 18 guards them. The early-check logs show this never happened.
- `pair_stats` rebuilds counts as `round(legal * feeds)` from 4-decimal rates. Against the exact `court_counts`, the error is at most 4 counts per read, which does not matter.

---

## Suspicions and design risks (not code bugs)

### A. The kill lines sit inside the read-to-read noise. HIGH decision risk
Four reads of the same checkpoint (run 14 `model_27798`, as the parent in runs 15, 16, 17 and the LR sweep, all on different seeds) give the spread of each metric:

| Metric (kill line) | Four reads | SD | Range |
|---|---|---|---|
| Left + back feeder contact (+2.0 needed, runs 14-17, sweep) | 0.584 0.580 0.557 0.564 | 1.31 pt | 2.7 pt |
| reach_deep + fast feeder contact ("up", runs 12-17) | 0.652 0.669 0.651 0.658 | 0.81 pt | 1.7 pt |
| Left feeder legal (cited in D-154 / D-158) | 0.455 0.408 0.423 0.434 | 1.97 pt | 4.7 pt |
| Court contact (-3 points) | 0.832 0.831 0.848 0.818 | 1.24 pt | 3.0 pt |
| Court main (-5) | 0.773 0.775 0.789 0.764 | 1.03 pt | 2.5 pt |
| Partner-ball legal | 0.697 0.701 0.703 0.704 | 0.34 pt | 0.75 pt |
| Feeder-ball legal | 0.814 0.819 0.816 0.818 | 0.24 pt | 0.56 pt |
| P(5+) | 0.178 0.184 0.187 0.185 | 0.38 pt | 0.9 pt |

What the noise does to each line:
- **"Left + back up by 2.0 points":** the difference between two reads has an SD of about 1.85 points. A child with a true +2 gain passes only 50 % of the time, a true +4 passes 86 %, and a child with no change passes 14 %.
- **"reach_deep + fast up":** a child with no real change is killed 50 % of the time, and one with a true +1 point is still killed 19 % of the time.
- **Guard lines:** "court contact -3" falsely kills about 4 % of children with no change, and "worst family -5" about 5 %.

What happened in the runs:
- Run 14 passed its engagement line by 0.1 point (+2.1 vs +2.0).
- Runs 15, 16 and 17 were killed on these engagement lines:
  - left + back: -3.5, -1.8 and -2.6;
  - reach_deep + fast: -0.7, -1.7 and -1.9.
- Runs 15 and 16 also had P(5+) +1.3 and partner-ball legal +2.2 and +1.2 at the time, which is above the P(5+) noise. These were pre-registered lines, so the kills followed the rules, but lines this tight have about coin-flip power.

**Reading on the same seed does not pair the reads.** `_refeed` draws a candidate feed for every env on every physics step (`return_stand.py:572`). Which feed an env actually gets depends on when it fires, and that differs between policies within the first rally. The data agrees: per-family feeder counts differ more between a same-seed parent and child (rms 74 per family, rally 15) than between two different-seed reads of the same checkpoint (rms 43).

**Run 14's endpoint success was also inside the noise:** feeder-ball legal was 81.93 % against an 81.9 % bar, about 6 balls of margin. The read-to-read SD is 0.24-0.3 points.

**Run 18's `sched-gate` is slightly stricter than intended.** It compares run 18's Wilson low to run 14's single endpoint P(5+), 18.73 %. That read was about 1 SD above the four-read mean of 18.37 %.

Options: common random numbers (a per-env feed stream indexed by feed count, not by step), intervals on the differences, or bigger reads for the engagement lines (the direction split has only about 1,700 left + back feeds).

### B. Silent env-var and protocol dependencies. MEDIUM
- `_residualize` (`tasks/__init__.py:999`) reads `PICKLEBOT_LAM_R`; `PICKLEBOT_TEACHER_GAIN`, `PICKLEBOT_RES_BASE` and `PICKLEBOT_LEG_R` are read the same way. A wrong lam_r or gain changes no tensor shapes, so the checkpoint loads with `strict=True` and the read is just wrong. Only `PICKLEBOT_TEACHER=1` would crash if forgotten, because the obs size changes.
- None of these values are written to the result JSON (only `PICKLEBOT_CONTROLLER` is, at `stage2_eval.py:303`), so a past read cannot be audited afterwards.
- I checked every read line in `rally_run14.sh`-`18.sh` and `lr_sweep.sh`, and all of them set the variables correctly.
- A cheap guard: the run's `params/env.yaml` records `lam_r: 2.0` (checked for run 14). `stage2_eval.py` could assert the active value against it.
- The task default for `pair_handoff` is `"crossing"` (`return_stand.py:193`), and `rally_check` never checks `pairs.handoff`, `envs`, `sim_seconds`, `task` or `families`, although all of them are in the JSON. Every `*-target.json` I found has `handoff: contact` (checked), but a missing `--pair-handoff contact` or `--rally` would go unnoticed. Without `--rally`, the 8 s time-outs would cut every rally.

### C. The eval condition differs from training by design. LOW, for the record
- The R4 / M1 read task (`Picklebot-Latent-Court-Res-G1`) has no ball-state noise. The training task ("Clean") has noise on and no lag.
- The policy is deterministic (the distribution mean; rsl_rl 5.4.2 `MLPModel.forward` with `stochastic_output=False`).
- The actor obs corruption is off.
- The obs normalizer is part of `actor_state_dict` and is loaded strictly. It does not update at inference. **This part is fine.**
- The actor rl config of the eval task matches training (`_s5e_rl_cfg` differs only in gamma).

### D. Smaller measurement notes. LOW
- **Court drill:** about 25 % of feeds are censored at the 8 s time-outs and left out (documented). Long-flight families are more likely to be cut, so the family mix is slightly skewed.
- **`feeder_speed_envelope.py`:** it logs only feeds that end in `pairs.step`. Feeds ended by a fall (`on_reset`) and volleyed-back feeder returns (finding 2) are left out of the direction split.
- **Early credits in the per-family table:** `_credit_early` calls `_tally` after `pairs.step` has set `handed`, so an early-credited feeder-ball return drops out of `per_family` (`return_stand.py:509`).
- **Pair contact:** the "pair contact" in `early_ceiling` divides all first contacts (including copies in dead courts) by the counted feeds, so the numerator and denominator do not match.
- **Run 14's parent read was not its starting policy:** it read rally-10 at lam_r 1, while run 14 started from `lam_r_init.py`'s rescaled copy. `2 tanh(a/2)` is only close to `tanh(a)`, and the init itself was never read (documented as approximate).

### E. Seeds. No contamination
- Every eval script asserts `DEV_EVAL_SEEDS`.
- No final seed (9200000-9200999) appears in the ledger or in any script.
- Rally-run seeds in the ledger are unique, apart from deliberate RETIRED re-entries.
- In `h5f_clean_eval.sh`, the two reported-only delay cells share seed S+4 (`v2-c10`, `v2-b40c20`).
- `train_run.sh` does not check `TRAIN_SEEDS`. The LR sweep (4219953-4219956) and run 18 (4219965, 4219966) trained on dev-range seeds. They are logged in the ledger and never reused for a read, but that breaks the D-038 rule `TRAIN_SEEDS = range(1, 1000)`.

## Checked and correct
- **Wilson:** both copies of the formula are correct. `stage2_eval` returns None for n = 0; `rally_check` returns [0, 0], and nothing can pass on that.
- **`boot_low`:** ratio of sums, courts resampled with replacement, 2,000 resamples, 2.5th percentile, generator seed 0 (as in `rally-milestones.md`). It reproduces run 14 (feeder 0.8194, low 0.8134; partner 0.7052, low 0.7006). The court-cluster design effect is 1.2-1.5.
- **P(k+) from `len_hist`:** the index is the number of good shots, the feeder ball is excluded, and the last bin is clamped at 64. There is no off-by-one, and the JSON values match the recomputation for all 30 reads.
- **Own-ball vs feeder:** `court_counts` agrees with `sides_own_ball` to within 4 counts. D-138 fall-ended feeds count as misses in both.
- **Bars in code vs docs:** `milestone`, `target`, `sched_gate` and `teacher_gate` match the bars in `rally-target.md`, `rally-milestones.md` and the driver headers. Every `early-*` mode matches its docstring and driver comment.
- **No silent "success" paths:** every `max(..., 1)` / default leads to a fail (0 rates, or a crash that kills), not a pass. The one exception: `min(..., default=(0.0, None))` and `if k in f1` let a missing family pass the family-contact guard.
- **`feeder_speed_envelope.py`:** it reproduces the M1 read's config and `pairs.py`'s contact-hand-off exclusion, and its direction binning is correct (0 forward, pi/2 left).
