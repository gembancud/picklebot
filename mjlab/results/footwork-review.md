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

## Round 55 (2026-10-31): h0-fw-01 killed at +900

**Correction checks** (all five): the kill is valid, and model_64199 is the 900th update.
- Experiment design and RL: the parent's D_lafan is 0.741, not 0.736.
- Motion and architecture: LAFAN1 exposure was halved.
- Architecture: the sampler collapses onto one serve bin (pre-existing).

**Votes**

| reviewer | change | parent | other |
|---|---|---|---|
| Coach | (a) weight 2.0 | 63300 | D-185 lines unchanged |
| Experiment design | (a) | 63300 | + a held-out footwork gate, + a dose line |
| Motion | (a) | 64199 | kill at D_lafan 0.83, an anti-lunge line |
| RL | (a) | 63300 | D_lafan 0.82, a +300 log line, a 5-point stroke kill |
| Architecture | (b) O2 at 0.5 m | 64199 | — |

The LAFAN1 endpoint is kept, 5 of 5.

**Decision:** D-186.

## Round 56 (2026-10-31): h0-fw-02 endpoint H0F-FAIL

**Correction checks**
- Coach: one-seed serve SE is about ±4 points, but both seeds dropped.
- Experiment design:
  - endpoint() labels FAIL before RETENTION;
  - the fwHO read was child-only (allowed);
  - LAFAN1 slip rose from 0.26 to 0.30.
- Architecture: 66298 is the 3,000th update; the sampler collapses onto one serve window (about 94 % of tennis samples) and resets on resume.
- RL: entropy_coef 0.005 against 0.001; action std 0.33 -> 0.40.

**Votes**

| reviewer | vote | notes |
|---|---|---|
| Coach | (d) | ΔR / R lines |
| Experiment design | (d) | paired ΔR, a fidelity guard, no promotion; then O2 unless NO-MOVE |
| Architecture | (d) | `--decoder-only` is required; the sampler floor is the real stroke protection |
| RL | (d) | the decoder check D ≥ 0.85; R ≥ 0.85 / ≤ 0.70; reject O2 and the share change |
| Motion | (d) (arrived after launch) | refutes the reference-skate hypothesis (it explains ≤ 0.03); the stroke loss is real; R ≥ 0.75 / ≤ 0.65; O2 next if triggered |

(d) carried 5 of 5, and (c) was rejected 5 of 5.

**Decision:** D-187.

## Round 57 (2026-10-31): the H1' diagnostic

**Correction checks** (all five): the bridge rule had no falls or arrival line, a pre-registration gap; nothing is relabelled.
- Experiment design: a post-hoc INVALID-READ qualifier; the slip of distilling on the collapsed sampler.
- Motion: H1' cannot stand still or brake.
- RL: the z-support mismatch.
- Architecture: the wiring is correct; PICKLEBOT_CONTROLLER is evaluation-only.

**Votes**

| reviewer | first | then |
|---|---|---|
| Coach | (a) | (b) |
| Motion | (a), with stillness / braking lines | (b) not first; (c) and (d) no |
| Experiment design | (b) P1 + the validity rule | (a); (c) gated on a P(5+) bound |
| RL | (b) | (a) if it adapts, (d) if not |
| Architecture | (b), after a cheap pre-read | (a), then (c) |

**Decision:** D-188.

## Round 58 (2026-10-31): P1 NO-ADAPT

**Correction checks**
- Architecture: P1's kill line watched falls only; hitting collapsed (legal_return 0.64 -> 0.001), so the fall drop came from giving up the ball.
- RL: the rally composite was never trained with a working speed reward, so the cap premise is confounded.
- Experiment design: the scope is H1' only; the (c) gate has failed.
- Motion: adaptation moved, but found no braking latent.

**Votes**

| reviewer | route | first action |
|---|---|---|
| Coach | (d) route C | a kickstart with the floor-check gate; the bound in parallel |
| Motion | (d) via the leg residual + kickstart | the CPU bound first (switch to (e) if < 0.5) |
| RL | (d) | the P2 capacity screen (the fixed speed reward); the bound in parallel |
| Experiment design | (e) | the bound + a direction x ball-index read |
| Architecture | (d) route C, cheapest variant | the bound, then the floor test (d1 if legs >= 0.85, else d2) |

**Decision:** D-189 — the floor test first.

## Round 59 (2026-10-31): design d1

Brief: footwork-round59-brief.md.

**Correction checks** (RL, motion, experiment design, architecture): the brief was wrong that s5c-18 copied the walking teacher "after the hit".
- Its args have `recover: False`, and `recover_share` is 0.0 in every logged row.
- So the walking teacher was copied only in move-to-spot episodes (about 50 %). Ball-episode approach and recovery copy s5c-17, which descends from the 1-m/s walker.
- d1 therefore changes footwork in rally play only indirectly. This is recorded as a known limit.
- Also: s5c-18 ran on seed 1, and its endpoint was the wall cap (1,199 iterations).
- Coach: Fast4 is read only on 4-6 m spots; court moves are 1-3 m.

**Votes**

| reviewer | teacher | notes |
|---|---|---|
| Coach | fw1b-S now | Fast4 only after its own floor and settle checks (d1b); base gate R_LB >= 0.85 |
| RL | fw1b-S now | Fast4 trains on 2-6 m, so the kickstart's 0.5-3 m spots are off its range; kill on mse_hit / mse_move; fallback d1 + `--recover` |
| Motion | fw1b-S now | Fast4's settling is unchecked (training settled about 3 %); watch the wrist, whose variance is 34.7 |
| Experiment design | conditional | Fast4 if CEILING-RAISED, valid and floor >= 0.85; else fw1b-S. Pre-launch teacher check on the kickstart geometry; base gate and re-climb lines |
| Architecture | fw1b-S now | exact command; the teacher sees only the spot, so the cap and v_req don't matter; L3Base measure task; PICKLEBOT_RES_BASE for the re-climb |

fw1b-S carried 4 of 5 votes, and the recipe is exact s5c-18 5 of 5.

**Adopted lines (coded in picklebot_mj/d1_rule.py)**
- Experiment design's teacher check, base gate and retention battery.
- The kickstart kill combines motion's mse_move line (anchored to the floor test) with RL's mse_hit multiplier (2x), applied to the 0.00085 actually logged over s5c-18's rows 300-360.

**Decision:** D-192.

## Round 60 (2026-10-31): the d1 teacher check read TEACHER-SLOW

Brief: footwork-round60-brief.md.

**Correction checks**
- All five: the code ran as specified. The 1.6 m/s line was set from long-spot reads (3-6 m) and never bounded for 0.5-3 m spots, where a best-1-s window is mostly acceleration and braking.
- Experiment design takes the error as its own.
  - Its framing, that the drill "asks for speed", was a category error, as RL also noted: the kickstart is pure supervised DAgger and the teacher sees only the spot.
  - The bodyspeed router's "VERDICT: VOID" lines in d1-teacher-*.log don't apply to this read and must not be quoted.
- Motion:
  - fw1b-S's speed histogram is flat (limited by distance); the walker's piles up at 1.0-1.2 m/s (its own cap);
  - total arrival is only slightly quicker (left 2.14 vs 2.33 s), with 5-6 cm of overshoot and a longer settle.
- Coach: falls are about 11x the walker's (0.090 vs 0.008 per 1,000 env-s), both tiny.
- Architecture: the base gate reads R_LB on 3-5 m Fast25 spots, which the kickstart never trains. CAP-HELD is therefore close to built in.

**Votes**

| reviewer | vote | lines |
|---|---|---|
| Coach | C, then A | first step <= walker - 0.25 s; settled >= walker + 0.10; falls <= 0.5 |
| Motion | C, then A | first step <= walker - 0.25 s; peak >= walker + 0.30; falls <= 0.15 |
| RL | C, then A | first step <= walker - 0.25 s; D-188 validity. If CAP-HELD with first step <= parent, next is d1b = drill geometry only (seed 188) |
| Experiment design | A | any new line now would be chosen knowing the answer; the base gate predates the data |
| Architecture | B, fallback A | B is feasible on L3: about 40 lines, a ball-episodes test, an import, and `task` added to the smoke's free set |

C then A carried 3 of 5.

**Coded line.** The line shared by all three C votes (first step <= walker - 0.25 s in left and back), plus D-188's existing validity numbers. Coach's and motion's extra lines had no majority. The shared line was set after the 0.35-0.41 s gap had been seen, and is recorded as such.

**Stage 2 (all who ruled):**
- r19-gate and the D-160 guards against run 14 stay computed and reported, with their expected FAIL stated before launch. No M1 or target claim may come from them.
- The run verdict uses the same guard slacks against 22b model_30200 on the same seeds: a `ref` argument to r19_guards, default run 14.
- KILL-NO-ARRIVE comes from an early read of a checkpoint saved at +360 (D-188 validity: worst untimed arrival < 0.80). No logging hook.

**Decision:** D-193.

## Round 61 (2026-10-31): d1 BASE-PASS; review of stage 2

Brief: footwork-round61-brief.md.

**Correction checks**
- **Experiment design.** The brief's reason for the same-age kill reference was wrong.
  - 22b's resume transient was over by about +241 (legal 0.601 at +241-260, 0.602 at +341-360).
  - The rise to 0.755 was learning from the weaker model_29000.
  - 22b's own continuation from model_30200 (30201-30600) reads 0.73-0.84 legal and 1.39-1.89 falls in every 20-iteration window, so the literal line never kills a replicate of the child's start.
  - The draft's replay test was tautological.
- **Architecture.** The same-age falls reference loosened KILL-UNSTABLE from 3.14 to 4.70. Falls per env-s are length-independent (D-170). It also found:
  - the half-written-block race;
  - no training exit check;
  - the smoke checks only config;
  - an unpinned base;
  - a gate crash read as "not met".
- **RL.**
  - The one-change claim is false against model_30200: the child gets 1,200 more updates.
  - The smoke dropped 22b's falls / std / config checks.
- **Coach.** Same confound. Worst arrival 0.830 only just clears 0.80.
- **Motion.**
  - Constant LR matches what model_30200 trained under.
  - The base's R_LB shortfall is all on the left (0.73 of the specialist; back 0.87).
  - Expect a composite R_LB of about 0.80, i.e. MIXED.

**Votes**

| reviewer | stage 2 or d1b | kill reference | other |
|---|---|---|---|
| Coach | stage 2 | accept | report the confound; first-ball and left/back legal |
| Motion | stage 2 | accept | report R_LB at zero-shot / endpoint and falls by sector; d1 + `--recover` before d1b |
| RL | stage 2 | accept (lenient) | control arm A1; critic warm-up 30; restore smoke checks |
| Experiment design | stage 2 | **reject**; literal line with pinned window | falls in KILL-NO-ARRIVE; zero-shot both arms; model_30600 reported; warm-up 0 |
| Architecture | stage 2 | accept for legal, **reject for falls** | fixes 1-7 |

Stage 2 carried 5 of 5.

**Kill reference: literal line kept.** The three accepting votes rested on the brief's premise, which experiment design's correction check refuted with the log. Keeping a loosened line on a refuted premise would break the never-loosen rule. Falls were also rejected on their own grounds (architecture). New tests show the literal line never kills 22b's own continuation.

**Also adopted**
- Critic warm-up 0: experiment design and architecture; motion matched 22b. RL's 30 had no majority.
- model_30600 read, reported (experiment design), instead of the control arm (RL only), which is costlier.
- From RL and architecture: 22b's smoke checks restored; the pinned base; the exit and endpoint checks; the half-block guard; GATE-CRASH; falls added to KILL-NO-ARRIVE with 22b's own-base read as reference.

**Decision:** D-194.

## Round 62 (2026-11-01): d1 stage 2 reads PANEL

Brief: footwork-round62-brief.md.

**Correction checks**
- **The speed loss is real, not seed noise** (all five). 22b's Measure60 reads on dev 4220257, 4220258 and 4220262 agree within 0.01 m/s. Back sustained fell steadily: 1.89 (zero-shot) -> 1.62 (+360) -> 1.43 (endpoint), with every sector slower.
- **The mechanism is not settled.**
  - Experiment design: "speed trained out" is a post-hoc story. The child settles at 1.36-1.53 m/s, not 1 m/s, and the loss sits where the zero-shot fell most (back falls 248 -> 52 -> 10).
  - RL: the 1 m/s cap with a std 0.5 kernel pays 0.04 at 1.9 m/s, an active penalty. Logged move_track_lin_vel drifted back toward 22b's (0.441 -> 0.482 against 22b's 0.498). P2 cut falls without slowing.
- **The zero-shot was not "safer" where it matters** (experiment design). Left falls 108 against 22b's 38-46; back 248 against 138-170.
- **The feeder loss is mostly the stated training-time confound** (RL, experiment design). 22b's own +400 already reads 0.628.
- **Court falls were unpaired** (RL, experiment design): 22b has no h5f read. Future gates read the parent on the same h5f seeds.
- **Option (d) as briefed was a no-op** (RL, architecture). fw_track_lin_vel under MoveDrill's 1.0 m/s command keeps std 0.5. The cap must rise too.

**Votes**

| reviewer | vote |
|---|---|
| Coach | (a) adopt the zero-shot if non-inferior on fresh seeds, then (e) |
| Motion | (d) with the cap raised; (a) h5f as a reported reference; KILL-SLOWED and AGILE-KEPT lines |
| RL | (a) ZS read, then (d) with the cap + kernel; KILL-SLOWED on R_LB; a rally gain not expected; (e) next |
| Experiment design | (b) d1 + `--recover` with a zero-shot gate before any stage 2; against (a), as post-hoc |
| Architecture | (d) corrected (cap 2.5 + kernel, move episodes only), with (a)'s reads as the reference |

**(d) carried 3 of 5.** Adopting (a) was rejected 3 to 2, so (a)'s reads are a reference only.

**Variant.** Architecture's least-code form, decided by the least-code rule since no variant had a majority. Instead of FastMoveDrill, which re-implements spot sampling and has never run in pair mode, only the reward changes. In move episodes it scores the 2.5-m/s-capped command with the widened kernel. Elsewhere it is 22b's exactly; a test checks both.

**Kill and endpoint lines.** Merged from motion and RL, paired with Z (22b on the d1 base, untrained) on the same seed:
- KILL-SLOWED if left or back sustained < Z - 0.15;
- KILL-NO-ARRIVE if D-188 validity against Z fails;
- AGILE-KEPT if R_LB >= Z - 0.03 and first step <= Z + 0.05.

**Decision:** D-196.

## Round 63 (2026-11-01): d1s3 reads SPEED-KEPT; the next step toward the target

Brief: footwork-round63-brief.md.

**Chair's correction, sent mid-round** (from the coach, confirmed in rally-target.md): the first good shot is the return of the feeder ball.
- So P(5+) <= feeder legal, which is about 0.65 for every player.
- The feeder ball is the first gate and a hard ceiling below 0.80, not "the other half".
- Motion, RL, experiment design and architecture voted after the correction (motion and experiment design revised).

**Correction checks**
- **D-197 under-reports the guards** (experiment design, architecture). Three family guards broke against 22b: easy_forehand -6.4, backhand -5.6 and deep -6.9.
- **"No worse at rallies" overstates it** (experiment design). Feeder -1.7, court falls +0.55 against 22b.
- **The brief quoted ballidx52 selectively** (experiment design, architecture, RL, motion):
  - Only pelvis_speed fired.
  - k = 1 receivers are slower than k >= 3 receivers (p50 0.157 vs 0.382).
  - The stillest k = 1 tercile still fails 0.086, against k >= 3's fastest at 0.042.
  - State explains about 9 % of k = 1 failures.
  - At k = 1 the receiver has not hit yet.
  - D-177's spot_progress paid moving, not being set.
- **Motion:** D-171's manipulation on 22b, refeed 3 s against 0.5 s: feeder 0.778 vs 0.656, P(5+) 0.548 vs 0.390. Readiness at rally start matters.
- **Experiment design, from existing JSONs:** feeder legal is the same for players whose agility differs widely (0.649-0.654). 76 % of feeder failures are no-contact; easy_forehand contact is only 0.72-0.75, against k >= 3 contact of 0.968.
- **RL:** the feeder share of training balls fell 0.29 -> 0.15 (D-171), so feeder skill is being forgotten.

**Votes**

| reviewer | vote |
|---|---|
| Coach | a read: ball-index split plus a feeder-failure split |
| Motion (revised) | (e3) `ready_at_handoff` at fire or receive, feeder-primary, with an (e1) baseline arm |
| RL | (e4) `pair_rally_cap` = 5 on the d1s3 task |
| Experiment design (revised) | (e4) as a read first: a feeder-ball split (a k = 0 bin), arms C / P / C2, FEED-STATE / FEED-SHOT / FEED-OTHER |
| Architecture | (e4) refeed read + (e1), about 1 GPU-h; then (e3) with fire or receive if readiness dominates |

**A read first carried 3 of 5** (coach, experiment design, architecture). Its lines are experiment design's (the tie-breaker), plus architecture's refeed 0.5 s vs 3 s read, reported. Parent from here on: the d1s3 child (4 of 5).

**Decision:** D-198.

## Round 64 (2026-11-01): review of the readiness run (D-199 draft)

Brief: footwork-round64-brief.md.

**Correction checks**
- **FEED-STATE was reached faithfully** (all five), with experiment design's caveats:
  - pelvis speed and recovery distance are correlated, so they count as one finding;
  - the tercile split is correlational; the refeed manipulation is the causal support;
  - report yaw (p50 17.3 deg; failure 0.219 / 0.165 / 0.217) and idle (p50 2.22 s; failure 0.162 / 0.201 / 0.244) in full; the brief's table showed mojibake there;
  - C trails 22b in matched-band contact (0.882 vs 0.904).
- **Blocking bug in the draft** (RL, experiment design, architecture, motion): `ready_at_event` read `recover_xy` at reward time, after `_refeed` had drawn the next ball's spot. The registered config has recovery random and court_feed_prob 0.8, so the term would have scored distance to a spot the robot cannot see. The draft's test used a static stub and missed it. **Fixed:** the value is computed inside the PairCourts.step wrapper at the event substep, before `_refeed`. The new test moves `recover_xy` after the event and checks the paid value does not change.
- **d_std 0.5 -> 1.0** (motion, RL, architecture; experiment design flagged it). At the medians (0.28 m/s, 0.94 m) the term paid about 0.01 per event; at 1.0 it pays about 0.17. Weight 50 is kept (all five).
- **Coach:** events within 1 s of an episode start are excluded, since the robot is still on its spawn spot.

**Amendments adopted**
- **RL:**
  - KILL-NO-DOSE on the per-event mean (logged sum, count and sum of squares), which must rise by more than 2 SE of the +1-20 window;
  - KILL-EVENTS: feeder fires within 1.10 x of d1s3's own run.
- **Experiment design:**
  - a control arm (d1s3 continued without the term, training seed 191), run only if the child is F-UP; otherwise READY-TIME;
  - ABS-F (feeder >= 0.80) required for READY-PASS, as D-198 said;
  - K3-KEPT as its own line;
  - verdict precedence;
  - seeds 4220325-4220327 ledgered.
- **Dose line:** RL's draft line (k = 0 pelvis-speed p50 at least 0.05 below the parent). Motion's recovery-distance alternative is reported.

**Not coded** (reported reads deferred, stated here): motion's FROZEN guard (pelvis displacement in the 0.5 s after the fire) and coach's time-to-first-step after the fire. They need a new tally field. The Measure60 first step is reported instead.

**Decision:** D-199.

## Round 65 (2026-11-02): d1s4 reads NO-DOSE

Brief: footwork-round65-brief.md.

**Correction checks**
- **The D-199 design was wrong** (coach, motion, RL). It paid readiness at partner contacts, which outnumber fires 3.5:1 in this run's own log (830,874 hand-offs vs 235,820 fires). That rewarded planted feet at the moment a split-step should load the first step, and fits the left / back loss. Read it as NO-DOSE with harm: no later term pays readiness at partner contacts.
- **D-200 omits two guard breaches** (experiment design): backhand -10.4 and fast -6.0.
- **The "22b" label in d1s2_gate is wrong:** the reference is the parent. The code label is now fixed.
- **"The gain came from hand-offs" is inferred, not measured.** The ready log does not split by event type.
- **The policy does not observe parked, court_dead, the refeed timer or the next receiver** (RL, architecture). The brief's "the robot sees itself parked" was wrong. The fire comes exactly 0.5 s after the later robot parks.
- **recovery_reward pays only after the robot's own legal hit** (architecture). A robot that just missed is paid nothing to recover.
- **Feeder share in d1s4 training was 22 %** overall (pair courts 11 %, drill courts 81 %).
- **The D-199 addendum-2 lesson was not yet coded** (experiment design). It is now: windows use the first rows at or after their edges, keep their length, and need at least 1,000 events, otherwise NO-DATA, never a kill. Replaying d1s4's logs reproduces the aligned values.

**Votes**

| reviewer | vote |
|---|---|
| Coach | (c) `pair_rally_cap` = 5 |
| Motion | (b) parked readiness while the court is dead |
| Experiment design | (c), with lines and seeds |
| RL | (d) observe parked / countdown / next receiver |
| Architecture | (b), with busy and young exclusions |

**No majority:** (c) 2, (b) 2, (d) 1. By the tie rule, the least new code wins: **(c)**, which needs no new task code. Experiment design's lines are used.
- KILL-EVENTS is dropped, since it would fire by design. KILL-NO-SHARE replaces it.
- D-172's per-bin premise is added as F-BIN.

**Caveats on record:**
- RL and architecture: D-172 found the cap's earlier gain was launch mix.
- RL: the robot cannot see the restart.
- These keep (b) and (d) queued.

**Decision:** D-201.


## Round 66 (2026-11-02): d1s5 smoke reads SMOKE-FAIL

Brief: footwork-round66-brief.md.

**Correction checks** (all five reviewers)
- **The falls line is valid under the cap.** Cap restarts are not resets: the cap only ends the rally in PairCourts and feeds a new ball (pairs.py). The terminations, the 120 s episode and the per-env-second estimator (D-170) are unchanged. No instrument defect, so the stop stands.
- **The smoke cannot settle 4.40 against 4.157 alone:** about 86 falls against about 82 at the line, Poisson SD about 9. Bootstrap ranges over iterations are wide (RL 95 %: d1s3 1.92-4.82, d1s5 2.24-7.18).
- **The half-split points to the cap, not noise.** Falls per 1,000 env-s, iterations 1-20 / 21-40:

| smoke | first half | second half |
|---|---|---|
| d1s2 | 4.15 | 1.69 |
| d1s3 | 4.40 | 2.26 |
| d1s4 | 3.66 | 1.67 |
| d1s5 | 4.16 | 4.64 |

  Every parent smoke falls to about 2 after the resume transient; d1s5 does not. This fits the mechanism: the cap feeds a new ball about 0.5 s after a successful rally, while the robots are still at rally tempo (motion).
- **(ii) is a re-roll** (experiment design, RL, motion): it was proposed only after the failure and would give a failed gate more chances to pass.
- **Process** (architecture): the (b) task was drafted under the D-202 label before the vote. Nothing was launched before the vote.
- **Lesson** (RL, descriptive only): about 1 parent smoke in 8 would cross the 1.5x line, so smoke summaries now report the half-split next to the line. The threshold is unchanged.

**Votes**

| reviewer | vote |
|---|---|
| Coach | (i) -> (b); withdraws (c): no coach feeds before the player is set |
| Motion | (i) -> (b), with the mask, value and weight restated for coding |
| Experiment design | (i) -> (b); record d1s5 as SMOKE-FAIL plainly; adds GUARDS |
| RL | (i) -> (b); adds KILL-FARM and the both-idle condition; (d) stays queued |
| Architecture | (i) -> (b), with code fixes 1-4 and a dose line |

**5 of 5 for (i): option (b), parked readiness, run d1s6.** The lines below were folded in before launch:
- **Mask:** `court_dead & parked & partner parked & not busy & age >= 1.0 s`.
  - The both-idle term is RL's: the paid window is the refeed countdown, so it cannot be stretched by ending rallies early.
  - RL's 2-s young window is not adopted; motion's and architecture's 1.0 s (READY_MIN_AGE_S) is kept.
- **Tests:** young alone; a real PairCourts rally (paid only from the rally's end to the fire; not on the fire step, hand-off steps, or within 1 s of a reset); both idle.
  - Motion's "moving recover_xy at the fire must not change the paid sum" holds, because the mask is false on the fire step.
- **Dose log** (report only): PICKLEBOT_READY_LOG, `parked` = [paid sum, paid steps, dead-court env steps, sum of squares], in the smoke and in training.
- **DOSE at the endpoint** (architecture): on the paired dose runs' k = 0 feeder tally, pelvis-speed p50 at the fire <= parent - 0.05 m/s, or recovery-distance p50 <= parent - 0.10 m.
  - The feeder tally holds the same quantities as the launch log and is already read.
- **GUARDS** (experiment design): rally_check.r19_guards against the parent's reads. It covers reach_deep, backhand, fast and left + back, plus the other families at D-160's slacks.
- **KILL-FARM** (RL): mean rally length over iterations 100-300 < 0.9 x the parent d1s3 run's (3.258, 59,624 rallies; kill below 2.93).
  - RL's second clause (dead-court fraction > parent + 0.05) is not coded: the parent's training log never recorded it. The child's fraction is reported from the dose log.
- **Seeds:** training 195, smoke 196.
  - Reads use the paired D-199 dev seeds 4220306-4220327 against the reused parent references, as in D-201 (experiment design). RL proposed fresh dev seeds for the child, but paired seeds are the practice here.
  - Dev 4220328-4220335 is reserved for any new read.

**Queued:**
- (d), observing parked / countdown / next receiver: first if (b) reads NO-DOSE or NO-ARRIVE (RL);
- the falls lever;
- coach's time-to-first-step-after-fire read;
- d1 + --recover; d1b; Fast4 floor test; H1''.

**Decision:** D-202.


## Round 67 (2026-11-02): d1s6 reads NO-DOSE

Brief: footwork-round67-brief.md.

**Correction checks**
- **The brief misread the dose log** (experiment design, RL, motion). PICKLEBOT_READY_LOG keeps running totals.
  - Taken window by window, the value per paid step is 0.27-0.29 from the first 10 iterations and flat to the end. The 0.10 was the resume transient.
  - The paid share falls 13.4 % -> 8.1 % and then stays flat.
  - The term was never climbed. Future logs record windowed values.
- **The DOSE and GUARDS reads are valid** (all five).
  - The parent dose file is byte-identical to d1s5's: same task, seed and base, and the dose-tally code is unchanged since 11-01.
  - The fire state is read before `_refeed`, against the same recover_xy that was paid.
  - The parent's two dose reads on 4220326 (D-200: 0.296 / 0.866; d1s5: 0.278 / 0.893) differ by about 0.02 m/s and 0.03 m. That is test-retest noise, smaller than the 0.05 / 0.10 lines, and the child is worse than both reads.
- **No code defect** (architecture). Rewards run after the decimation loop, so the fire step is not paid.
- **Design flaw** (architecture, coach). The value is sharp in speed and soft in distance, so inside a 0.5 s window stopping where you are pays more than moving to the spot. Training launch bins, previous rally 0-1:
  - d < 0.3 m at the fire: d1s3 20.4 %, d1s6 15.1 %;
  - v < 0.25 m/s: 52.0 % -> 53.8 %.
- **Unobservable state** (RL). To the robot, "parked on a dead court" looks the same as "parked, waiting for the partner's shot", where the right move is to load the first step. Paying stillness there likely cost the fast / left / back contact.
- **The guard breach may be partly drift** (motion). The control only runs on F-UP.
- **Coach's arithmetic gap, diagnosed** (CPU, read-only). Feeder 0.63 x partner 0.99^4 = 0.61, yet P(5+) is 0.39.
  - No accounting bug: PairCourts alone with fixed per-ball rates reproduces 0.596.
  - The 0.99 own-ball rate is shot-weighted: 974 of 1,024 courts are still open at the 64-shot cap.
  - Failure rate by shot position (parent): feeder 0.383, first handed ball 0.287, second 0.082, third 0.028, fourth 0.010, later about 0.003. Their product gives exactly 0.387.
  - On a log scale, the feeder ball is 51 % of the P(5+) shortfall and the first handed ball 36 %.
  - The read ran without `--audit-fixes`: about 900 early-volley returns are not counted. That is small.

**Votes**

| reviewer | vote |
|---|---|
| Coach | (i), smallest form (time-to-fire, receive-next); keep the feeder premise |
| Motion | (i), observation only |
| Experiment design | (i), (d) alone; adds NO-USE and a stop rule |
| RL | (i), (d) alone |
| Architecture | (i) on d1s3's task, no parked_ready; code given |

**5 of 5 for (i): run d1s7, the restart state as an input, with no reward change.** Taken into the code:
- **Inputs:** architecture's / RL's five trailing columns in actor and critic: parked, partner parked, court dead, next receiver (+1 / -1 on a dead court, PairCourts' parity with its busy override), refeed countdown 1 -> 0.
  - Switched by PICKLEBOT_RESTART_OBS=1 in `_residualize`. Tested: last term in every stage and h5f task, and absent when off.
- **Warm-start:** expand_checkpoint.py on model_31399, giving zero columns, a (0, 1) normalizer prior and zero Adam moments.
  - INVALID: before training, the widened checkpoint equals the parent on the old columns (verified on CPU).
  - Smoke: the new columns get a gradient in both networks.
- **NO-USE** (experiment design's form; others proposed variants): the child's dose read with the inputs frozen at live-court values must take back >= half of the DOSE gain.
  - It is paired on 4220326, not ED's proposed 4220329, because the measured test-retest noise between seeds (0.02 / 0.03) is half the size of the line.
- **Stop rule** (experiment design): NO-DOSE or NO-USE ends the feeder premise, with no fourth feeder lever.
- **Reported only:** the parent dose retest on 4220330; failure rates at each opening position (round 67 diagnosis).
- **Not adopted:**
  - coach's FIRST-STEP line, which needs new measurement code (queued);
  - motion's always-on control (one vote; D-202's control-only-if-F-UP kept).
- **Seeds:** training 197, smoke 198; paired reads 4220306-4220327 as before; dev 4220330 for the parent retest.

**For the user** (coach): the frozen target read refeeds 0.5 s after a rally ends, which no real rally does. A 3-s refeed lifts feeder legal 0.63 -> 0.76 and P(5+) 0.39 -> 0.55. The panel does not change the target. This is raised with the user.

**Queued:**
- the first handed ball (29 % hazard) as its own lever, if (d) does not cover it;
- the falls lever;
- FIRST-STEP;
- d1 + --recover; d1b; Fast4 floor; H1''.

**Decision:** D-203.


## Round 68 (2026-11-02): d1s7 reads NO-DOSE; the feeder premise ends

Brief: footwork-round68-brief.md.

**Correction checks**
- **NO-DOSE is robust** (all five). Against the parent retest on 4220330, the child moved -0.027 m/s and -0.004 m, against required changes of -0.05 and -0.10.
- **No code defect** (architecture). The flag, the term in both networks, and the freeze were confirmed in each run's params and .env files. The indexing matches PairCourts.
- **The actor barely uses the input.** Its new-column norms are 0.29-0.76, against an old-column median of 3.75. The critic's are 3.0-5.8.
  - Raw norms across networks are not comparable (RL).
  - The actor's use grew from 0.11 to 0.67 while dose did not move, so information was not the limit (RL).
- **Brief errors:**
  - NO-USE is "not applicable" (it applies only after DOSE), not "also holds" (experiment design).
  - d1s5 never trained (SMOKE-FAIL), so three levers were tested and the rally cap is untested. The stop stands on d1s7's own NO-DOSE (RL, experiment design).
  - Ball 4 fails at 0.010; 0.003 is ball 5 on (coach, experiment design).
  - The rally length 3.80 is a training window, not a read (coach).
  - d1s7's gains were at balls 2-3 (0.082 -> 0.063, 0.028 -> 0.008), not at the opening (coach).
  - The receiver state by handed-ball index was already logged (ballidx52 / 63, the dose logs). It needs no new code (architecture).
- **Restart share** (motion, CPU). At a 3-s refeed the first handed ball fails 0.191 (parent) and 0.162 (child), against 0.287 / 0.296. So about a third to a half of the ball-1 excess is the restart state.
- **Guards** (experiment design).
  - Each family has n of about 150-225, so the SE of a difference is about 5 points, the size of the slack. With 16 families, the worst one lands near -8.5 points by chance.
  - The same parent read on two seed sets fails its own fast guard (-5.6). RL: fast 0.457 vs 0.514.
  - d1s7's backhand -8.9 (z -1.8, mean shift -1.0) looks like noise. d1s4 (mean -3.3) and d1s6 (mean -2.65) look like real erosion.
  - The static parent stays the promotion reference (never loosened). Attribution needs more seeds and a control.

**Votes**

| reviewer | vote |
|---|---|
| Coach | (i) diagnostic (ball vs body), then (iii) |
| RL | (i) plus a guard retest, then a lever with an unconditional control |
| Motion | (i) diagnostic (state / ball / restart), then (iii) |
| Experiment design | (iii) modified (pooled 4-seed guard reads), then (i); no lever until both |
| Architecture | (iii) on the GPU now, (i) CPU-built alongside |

**All five want (i) and (iii) before any new lever; 3 of 5 want (i) first.** Run D-204 (scripts/diag/diag68.sh): (i) then (iii) in one driver.
- **(i)** One parent LR-0 read with the existing split tally per refeed delay: 0.5 s (dev 4220332) and 3.0 s (dev 4220333, the RESTART report).
- **Lines (d1_rule.diag68_route), set before the read:**
  - **INVALID:** fewer than 1,000 k = 1 balls.
  - **STATE** (motion): pelvis speed or recovery distance, with k = 1 failure top - bottom tercile >= 0.10 while k >= 3 stays <= 0.05.
  - **BALL** (coach's matching, as a share): a shot variable whose reweighting of k = 1 to k >= 3's bins removes >= half the k = 1 excess.
  - **Route:** STATE only -> recovery to ready at rally start / after misses (motion's untested mechanism: recovery_reward pays only after the robot's own hit); BALL only -> feed-return quality or pair-court mix; BOTH -> panel; NEITHER -> the falls lever (RL).
  - Architecture's miss / fault split is not coded (least code). The existing tally already separates contact from legal.
- **(iii) rally-d1s3ctl** (experiment design's form): the parent continued 1,200 iterations with no change, training seed 197, no smoke, D-194 kill lines only.
  - Guard reads are pooled over 4 seeds per checkpoint.
  - **GUARD-N:** the parent's single read breaches against its pooled read -> later guard reads use >= 4 seeds.
  - **DRIFT:** the control breaches r19_guards against the pooled parent, or its mean family shift <= -2.0 points -> later children are also reported against the control. Otherwise **NO-DRIFT**.
- **RL's alternative** (an unconditional control inside the next lever) is kept for the lever after this.

**Decision:** D-204.


## Round 69 (2026-11-02): diag68 routes STATE; the lever

Brief: footwork-round69-brief.md.

**diag68 (D-204 (i)):** STATE, on the 0.5-s read with seeds 4220332 + 4220337 summed (1,917 k = 1 balls in the band).
- **STATE fires on both state variables.** k = 1 top - bottom tercile failure gap: pelvis speed 0.179, recovery distance 0.138. The same gaps at k >= 3: 0.016 and 0.023.
- **BALL does not fire.** The share of the k = 1 excess removed by reweighting: bounce_depth 0.327, angle 0.138, net_clear 0.082, spin -0.055.
- **Each seed fires STATE on its own** (architecture). So does the 3.0-s read (reported, one seed).

**Correction checks**
- **The INVALID extension was legitimate** (experiment design, RL, architecture). It was added blind to the outcome, with the rule unchanged and the seed named beforehand.
  - Lesson, coded from now on: INVALID -> add pre-named seeds in one block, then the panel.
- **STATE is a correlation** (experiment design, RL). The k >= 3 flatness test is close to automatic at a 0.02-0.04 base rate, and bounce_depth alone removes 33 % of the excess. The lever run is the causal test.
- **The brief misstated the reward** (all five):
  - std is 1.5 m, not 0.5.
  - hit_done is cleared only at the env's next feed or a reset (return_stand.py:661, :517). So a robot whose last ball was its own legal hit is already paid while it waits.
  - Only robots after a no-contact miss, or a reset, are unpaid: about half of the k = 1 receivers.
- **The brief omitted D-177 idlerec53** (RL, motion, architecture): spot_progress while parked, k = 1 +0.79 pt, a non-test with no dose line. RL: at the same weight, (a)'s incentive is no larger than that lever's. This run has a dose line and a climb kill.
- **The 3.0-s read** (motion): k = 1 pelvis-speed p90 falls 0.75 -> 0.44 m/s, but recovery distance barely moves (p50 0.70 -> 0.59). Robots settle where they stand; they do not walk back. So pay distance, not stillness.
  - It contradicts round 68's restart share: 2.5 s more removes only about 10 % of the excess here, against "a third to a half" there. The two instruments must be reconciled before restart time is cited again (experiment design, coach).
- **Ceiling** (architecture): the bottom tercile still fails 0.115-0.13. At best the lever removes about a third of the k = 1 excess, about 5 points.
- **diag68-summary.txt** kept the superseded first block. A note now says so; the .json is authoritative.

**Votes:** 5 of 5 for (a).

| reviewer | vote |
|---|---|
| Coach | mask hit_done or parked; stop at the partner's contact; no stillness pay |
| Experiment design | (a); KILL-NO-CLIMB; DOSE and HAZARD against the parent and the control; training 197 to match the control |
| RL | (a), with a NO-GAP gate read before training (paid vs unpaid k = 1 receivers) |
| Motion | (a), one change; DOSE 0.10 m; if NO-DOSE, the next change is std 0.5 |
| Architecture | (a); code given; a new task, return_stand.py untouched |

**Run D-205 d1s8** (scripts/diag/d1_stage8.sh).
- **Task** Picklebot-Rally22b-FastMove-IdleRec-G1: recovery_reward also pays while parked on a pair court and not busy. Distance only, std 1.5, weight 1.0; one change. Tested on a real PairCourts.
- **Training seed:** 199, smoke 200 (3 of 4 who named one). rally-d1s3ctlb (seed 197) serves as the unconditional control.
- **Kill at +360:** D-194's lines, KILL-FARM, KILL-NO-CLIMB (newly paid value +0.05 from iterations 0-60 to 300-360), KILL-SLOWED / NO-ARRIVE.
- **DOSE:** k = 1 recover_dist p50 at the hand-off (all bands) <= parent - 0.10 and <= control - 0.10. The parent reads 0.705 m.
- **HAZARD, primary:** matched-band k = 1 failure <= parent - 0.03 and <= control - 0.03, with k >= 3 <= parent + 0.01. The parent reads 0.1805 / 0.0213.
  - Threshold: RL and motion said 0.03, experiment design 0.04, coach 0.05. Majority: 0.03.
- **GUARDS:** pooled 4-seed reads against the static parent; the control's breaches are reported for attribution. P5-KEPT; F-UP reported.
- **Order:** KILL -> INVALID -> NO-DOSE -> NO-HAZARD -> GUARD-BREACH -> P5-LOSS -> REC-PASS.
  - NO-DOSE -> panel: std 0.5 (motion, architecture) or end readiness rewards (experiment design).
  - NO-HAZARD -> STATE falsified -> the falls lever.
- **Not adopted:** RL's NO-GAP gate (1 vote; it needs new tally code). It waits for the drift control and is recorded as a risk: the unpaid stratum may be too small to move the k = 1 median.

**Decision:** D-205.


## Round 70 (2026-11-02): the drift control reads DRIFT; d1s8 reads SMOKE-FAIL

Brief: footwork-round70-brief.md.

**Correction checks**
- **DRIFT is valid as pre-registered** (all five). It fires on the breach branch: reach_backhand -6.6, reach_deep -5.1, cross_forehand -3.9. The -1.93 mean plays no part.
  - Each breach is about 2.5 SE (pooled n of about 640-750 per family). 13 of 17 families moved down, and the control is below the parent on all 4 seeds for the three breached families (experiment design, architecture).
  - Caveat: one training seed (197).
- **The brief overstated the P(5+) effect.** Pooled over 4 seeds, P(5+) is 0.381 for the parent and 0.375 for the control (-0.6 points, overlapping CIs), so "does not improve", not "erodes".
  - The feeder loss is real: -3.1 points pooled, -2.7 to -4.1 on every seed (experiment design).
  - Coach: grooved later shots held (positions 3-4 slightly better) while the rare, hard families faded.
- **SMOKE-FAIL is valid; no instrument defect** (all five).
  - falls_by_length reads only termination counts. All smokes log the same terms; episode length and env count match.
  - Architecture: d1s8's time_out reads 1.2 / 1.4 in iterations 0-1; at 1.0 the smoke is still 4.385.
- **The resume-shock reading was wrong.**
  - The value-loss spike is in every smoke (RL, motion). d1s8's early KL is inside d1s4-d1s7's range (architecture).
  - By quarter, d1s8 reads 11.5 / 3.9 / 3.5 / 1.4 falls per 1,000 env-s, against d1s7's 1.1 / 1.5 / 0.9 / 0.8 from the same parent (RL). In iterations 0-9 that is about 56 falls against about 5.
  - Motion: the front-loaded new reward pays robots about 1.5 m off their spot. A distance-only pull speeds them up, which is the state diag68 found hazardous.
- **New finding** (architecture): at 1,024 envs the KL guard trips on every update. In 12,288-env training it never trips (KL 0.013 mean), so "KL 0.05" is no constraint in training, and the smoke tests another optimizer regime. Recorded only; nothing is loosened.
- **Why the control drifts** (RL): KL is flat at 0.013 and the guard never trips. Nothing anchors the policy to the parent, so 1,200 steps go to the frequent rewarded events and the rarely rewarded families erode.
  - A lower LR or shorter run also cuts any lever's dose by the same factor.
- **The critic warm-up is a second change against the control, not a re-roll** (experiment design, architecture). The knob lives in CriticWarmupRunner (tasks/__init__.py), not sched_ppo.py.
- **Ledger:** training seed 199 was never trained; it is retired unused.
- **Process:** RL reported writing and at once deleting a scratch file F:\dev\q.py, despite read-only instructions. Confirmed absent.

**Votes:** 5 of 5 for (iii).

| reviewer | vote |
|---|---|
| Coach | (iii) onset read, then COURT_MIX_WEAK; then (a) with a warm-up |
| Motion | (iii) onset read, then LR 5e-5 or 600 iterations; (a) closed in this form |
| Experiment design | (iii): onset read (EARLY / LATE), then LR 3e-5 if LATE; (a) parked |
| RL | (iii): onset read, then a reference anchor (new code); LR 5e-5 fallback |
| Architecture | (iii): LR 3e-5 now; the anchor if it still drifts |

**Run D-206** (scripts/diag/drift70.sh).
- **Stage A (4 of 5):** read the control's model_31800 / model_32200 on the pooled seeds.
  - EARLY-DRIFT (experiment design's rule) at +400 -> panel (the anchor is new code). Otherwise LATE -> stage B.
- **Stage B:** rally-d1s3lr, LR_PEAK 3e-5 (experiment design and architecture; motion and RL said 5e-5; experiment design's position breaks the tie), 1,200 iterations, seed 201, no smoke (a knob only).
  - Read on the same pooled seeds (paired reuse, architecture and RL; experiment design proposed fresh seeds).
  - **FIXED:** no breach, mean shift >= -1.0, pooled feeder and P(5+) >= parent - 0.01.
  - **STILL-DRIFT:** a breach or mean <= -2.0 -> the anchor next.
  - **PARTIAL** -> panel.
- **(a) is parked**, not closed (experiment design, architecture, coach). It is re-tested on whichever recipe passes; motion's speed-hazard objection is recorded for that design.
- **Not adopted:** COURT_MIX_WEAK (coach only); the warm-up (a second change).

**Decision:** D-206.


## Round 71 (2026-11-03): rally-d1s3lr (LR 3e-5) reads STILL-DRIFT, with a P(5+) gain

Brief: footwork-round71-brief.md.

**Correction checks**
- **STILL-DRIFT is valid as pre-registered** (all five). Both branches fire.
  - The backhand breach (-5.6) is below the parent on all 4 seeds: -6.2, -6.8, -3.1, -6.5.
  - The mean shift is -2.21 (SE 0.54); 16 of 17 families are down.
  - RL: with 17 families at SE 1.5-2.7, some family falls below -5 about 20-25 % of the time even with no true drift, so FIXED can fail with a working anchor. Recorded only; the line is not loosened.
- **The P(5+) gain is real for this checkpoint across eval seeds.**
  - Per seed: +2.7, +1.6, +1.5, +2.8 (4 of 4). Pooled +2.12, SE 0.66, 95 % CI +0.8 to +3.4. Against the control: +1.4 to +4.3 per seed.
  - Experiment design: one training seed, a non-pre-registered metric, and seeds reused five times make it a hypothesis, not a result.
  - Motion: about 1,020 of 1,024 courts per seed end in an open rally of 64+, so the unit of independence is the court. The gain is about 15 % fewer failed rallies per court before lock-in.
- **Brief errors:**
  - n is 10,353 (d1s3lr) / 11,421 (parent), not about 11,000.
  - "Paired" is by seed only.
- **What 3e-5 changed in play** (motion, pooled pairs, parent -> lr):
  - falls per 1,000 shots 1.63 -> 0.92;
  - WRONG_SIDE endings -27 %;
  - ready stance 0.153 -> 0.318;
  - a more cautious mover: fast -4.6, topspin -4.2, paddle speed 5.73 -> 5.56.
  - Against the control, lr held reach_backhand / reach_deep / cross_forehand.
- **The backhand fade is rally-only** (coach). Feeder-drill backhand held: lr 0.639 vs parent 0.633. The 1e-4 control also loses pairs backhand (-4.8, 4 of 4 seeds), so it is the task, not the LR. Coach withdraws COURT_MIX_WEAK.
- **LR does not limit the drift** (RL): mean shift -2.21 at 3e-5 vs -1.95 at 1e-4, with per-update KL 2.4x smaller. The objective pulls it, so (iii) is out.
- **No code defects** in drift70.sh / pool_reads / pooled_pairs / drift_verdict (architecture). The pooled parent files recompute exactly.

**Votes:** 5 of 5 for (i), the anchor on the LR 3e-5 base.

| reviewer | vote |
|---|---|
| Coach | (i) on 3e-5; KL to the parent actor, coef 1.0 constant |
| Motion | (i) on 3e-5; coef 1.0 constant; KEPT-GAIN reported |
| RL | (i) on 3e-5; mean-KL with the reference std; coef 1.0 constant; against (ii) a moving baseline, against (iii) |
| Experiment design | (i) on 3e-5, reference rally-d1s3lr; FIXED -> confirmation on fresh seeds |
| Architecture | (i) on 3e-5; code given; coef 0.1 |

Coefficient: 1.0 (4 of 5).

**Run D-207** (scripts/diag/anchor71.sh): rally-d1s3anc.
- **Change:** AnchoredScheduledPPO (a new subclass in sched_ppo.py, reusing RegPPO's _RefRegulariser; tests in tests/test_anchored_ppo.py).
  - The reference is the parent model_31399's actor. The coefficient is held constant at 1.0, with no warm-up.
  - LR 3e-5; training seed 202, smoke 203.
- **Smoke:** the D-170 line, plus the pull-back wired (first update <= 0.01, nonzero by update 10).
- **Kill at +360:** D-194's lines.
- **Endpoint:** drift_verdict against the pooled parent, lines unchanged; reported against rally-d1s3lr (the one-change effect) and the control.
- **If FIXED:** a confirmation read on fresh dev 4220338 / 4220339. A breach, or P(5+) below the parent -> panel, no promotion.

**Decision:** D-207.


## Round 72 (2026-11-03): rally-d1s3anc reads FIXED pooled, then CONFIRM-FAIL

Brief: footwork-round72-brief.md.

**Correction checks**
- **FIXED and CONFIRM-FAIL are valid as pre-registered** (all five). No promotion.
- **The single-seed confirmation was a weak design** (experiment design: its own round-71 design).
  - With a family SE of about 5 points on one seed and about 17 families, a child with no true drift breaches about 90 % of the time. The strict P(5+) >= parent test fails about half the time.
  - The -5.7 backhand breach is likely noise: about 1.2 SE; pooled over all 5 seeds it is about -1.8. On the same confirmation, the feeder read has the anchor's backhand higher (0.686 vs 0.660) (motion).
  - Fixed from now on: pool confirmations over 4 fresh seeds, plus a calibration read of the parent.
- **The brief misstated the anchor's strength** (all five). The pull-back (0.011, the distance from the parent) and the per-update KL (a step size) are different quantities.
  - The pull-back was 0.0023 at update 1, 0.0099 at update 10, and flat at 0.011 from about update 20 to 1200. The policy hit the leash at once and practised in place (coach, RL).
- **Design gap** (experiment design, RL, architecture): FIXED has no learning requirement, so a policy that barely moves passes. A GAIN line is added (a tightening).
- **What the anchor erased** (motion, pooled pairs):

  | measure | parent | d1s3lr | anchor |
  |---|---|---|---|
  | ready stance | 0.153 | 0.318 | 0.151 |
  | falls per 1,000 hits | 1.68 | 0.94 | 1.74 |
  | WRONG_SIDE share | 0.259 | 0.220 | 0.253 |
  | recovery median | 0.375 m | 0.325 m | 0.375 m |

  d1s3lr's P(5+) gain came with a whole-body posture change, and the anchor kept none of it.
- **Where the anchor binds** (RL): it weights outputs by 1/sigma_ref^2. The parent's lowest-std outputs (14, 25, 30) are also PPO's top KL-share outputs, so it holds hardest where learning happens. A CPU proxy puts d1s3lr hundreds of times further from the parent than the anchored run.
- **Partial correction** (motion): "the backhand fade is rally-only" is not quite right. d1s3lr's pooled feeder reach_backhand also fell (0.661 vs 0.699).
- **(iii) has no knob** (architecture): hand-offs are already 78 % of training balls, and the feed mix reaches only feeder balls.

**Votes:** 5 of 5 for (i).

| reviewer | coefficient |
|---|---|
| Coach | 0.3 |
| Experiment design | 0.3, plus GAIN and routes |
| Motion | 0.3; the mechanism read; next an arms-only anchor if 0.3 drifts |
| RL | 0.1 (the settled distance scales about 1/coef^2) |
| Architecture | probe-calibrated, default 0.5 |

**Run D-208** (scripts/diag/anchor72.sh): rally-d1s3anc03, coef 0.3 (3 of 5), training seed 204.
- No smoke: a knob on code already smoked in D-207 (experiment design and architecture).
- The pull-back is reported at the first 10 updates, +100, +360 and the end.
- **Endpoint:** drift_verdict (unchanged) + GAIN (pooled P(5+) >= parent + 1.0 point, lower 95 % CI of the per-seed paired difference > 0).
- **Routes:** CONFIRM / HELD-NO-GAIN / TRADE-OFF / STILL-DRIFT / PARTIAL.
- **The mechanism read**, reported (motion's ready-stance bar of 0.23 noted, not gating).
- **Confirmation** pooled over 4 fresh seeds (4220341-44 pairs, 4220345-48 direction) with a parent calibration read. CONFIRM-FAIL on a breach or child P(5+) < parent (as D-207).
- **Queued:** the arms-only anchor (motion) if 0.3 drifts; RL's 0.1 if 0.3 still binds.

**Decision:** D-208.


## Round 73 (2026-11-03): rally-d1s3anc03 (anchor coef 0.3) reads HELD-NO-GAIN

Brief: footwork-round73-brief.md.

**Correction checks**
- **HELD-NO-GAIN is valid as pre-registered** (all five). Architecture re-ran gain_line: d1s3lr passes as a positive control (+2.12, CI +1.01).
- **The coefficient model was wrong** (all five).
  - The logged pull-back is the raw KL, and its plateau scales about 1/coef (0.011 -> 0.035, 3.2x), not 1/coef^2. That fits a noise-driven equilibrium: the anchored policy jitters around the parent rather than being pulled part-way toward d1s3lr.
  - Coef 0.1 predicts about 0.11. A CPU proxy puts d1s3lr at KL about 28.5 from the parent, against 0.25 for anchor 0.3, so (ii) would pin the posture again.
  - Ready stance did not move between coef 1.0 and 0.3, so posture is not a smooth function of the KL (experiment design).
- **The brief misstated the action layout** (all five). The actor has 35 outputs: 0-31 latent dims through the frozen whole-body decoder, 32-34 right-wrist residuals; leg_r is 0, so there are no leg outputs.
  - A clean arms-only mask is not defined. Decoder-Jacobian probes:
    - motion: no latent dim is more than 0.89 legs; the median is 0.38;
    - architecture: 12 dims mostly arms, 6 mostly legs, 14 mixed.
  - The posture change and the backhand drift share outputs 14 / 25 / 30, and the wrist outputs carry about 2 % of d1s3lr's deviation (RL).
- **Unstated:** legal_return fell 0.888 (+241-260) -> 0.759 (+360), inside the kill line (experiment design). The brief's falls units were mixed: +360 is per 1,000 env-s, the table per 1,000 hits (coach).
- **The bigger issue** (experiment design, RL): d1s3lr's gain rests on one training seed, and two anchor runs have now been spent protecting it.
- **Process:** RL and motion each wrote throwaway CPU scripts in the session scratchpad despite the write-no-files instruction. The repo was untouched.

**Votes**

| reviewer | vote |
|---|---|
| Experiment design | (iv) replicate d1s3lr, training seed 205; second (ii) |
| RL | (iv) replicate d1s3lr |
| Motion | (i) a hard approximate arm mask (12 outputs) at coef 0.3; second (iii) |
| Architecture | (i) a soft arm-share mask at coef 0.3 |
| Coach | (iii) d1s3lr's recipe with backhand-family feeder weights 2.0 |

**No majority:** (iv) 2, (i) 2, (iii) 1. By the tie rule, the least-new-code options are (iv) and (iii) (none each). They tie, so experiment design's position decides: **(iv)**.

**Run D-209** (scripts/diag/rep73.sh): rally-d1s3lr2, rally-d1s3lr's recipe with one change, training seed 201 -> 205.
- No smoke; kill at +360 on D-194's lines.
- **Endpoint:** D-208's lines (drift_verdict + GAIN + routes) plus **REPLICATED** = GAIN, pooled ready stance >= 0.25 and falls per 1,000 hits <= 1.3.
  - Not replicated -> NOT-REPLICATED: d1s3lr's gain was a seed effect and the anchor line closes (panel).
  - Replicated -> D-208's routes; a TRADE-OFF goes to the panel with a base proven on two seeds.
- **Confirmation** (CONFIRM only): pooled on dev 4220341-4220348. These were reserved in D-208, never read, and released by a ledger note.
- **Queued:** the arm-share anchor (motion / architecture, new code); the backhand-weight run (coach).

**Decision:** D-209.


## Round 74 (2026-11-04): rally-d1s3lr2 (the d1s3lr replicate) reads NOT-REPLICATED

Brief: footwork-round74-brief.md.

**Correction checks**
- **NOT-REPLICATED and PARTIAL are valid as pre-registered** (all five recomputed them).
- **The GAIN CI was the wrong replication test** (all five; experiment design: its own design).
  - About 2,600 rallies per seed give a binomial SD of about 1.3 points per per-seed difference, which is the whole observed spread (1.24).
  - The t-3df interval re-estimates a known variance and pays t = 3.18. Its power at a true +1.5-1.8 point effect is about 10-40 %. It also never measures training-seed variance.
  - So the result reads "gain not shown (test underpowered)", not "a seed effect".
- **"8 of 8 positive" is inflated** (coach, motion, experiment design, architecture). Both children are compared with the same parent reads; the parent's low seed 4220331 gives both children their largest differences.
- **"The posture replicates closely" overstates it** (motion).
  - Falls (0.94 / 0.94), recovery (0.325 m) and the WRONG_SIDE drop replicate.
  - The replicate widened its stance (ready 0.259) but lost the loading dip (dip 0.157 vs d1s3lr 0.26, parent 0.32; ready-and-dip 0.052 vs 0.097).
  - It is not an agility gain: feeder direction contact and peak feeder speed are unchanged or slightly lower; right side about -2.5.
- **Post hoc** (architecture): against the LR-1e-4 control, the lower CI is +0.61 (d1s3lr) and +0.07 (d1s3lr2). The static-parent comparison mixes "more training" with "LR".
- **Labels:** falls units are mixed (+360 per 1,000 env-s, tables per 1,000 hits). The rep73 files are named `anc-` but hold the replicate. Recovery "median" is a mean of per-seed medians.

**Votes:** 5 of 5 for (ii), LR 3e-5 as the recipe base with no promotion.

| reviewer | lever | control seed |
|---|---|---|
| Coach | lever (a) | 205 (reuse lr2) |
| RL | backhand weights | 206 (C doubles as a 3rd replicate) |
| Architecture | backhand weights | 205 (reuse) |
| Motion | lever (a) | 206 |
| Experiment design | leans backhand weights | 206 |

Lever: backhand weights, 3 to 2. Control: fresh seed 206, 3 to 2.

**Run D-210** (scripts/diag/lev74.sh), training seed 206, no smoke (knobs only):
- **C** = rally-d1s3lr3: d1s3lr's recipe.
- **L** = rally-d1s3bh: C + backhand / reach-backhand / cross-backhand feeder weights 2.0.
- **New GAIN2 statistic** (experiment design, prospective only): pooled difference >= +1 point and pooled difference - 1.96 x max(binomial SE, per-seed SE) > 0.
- **RECIPE (C vs parent):** GAIN2 + ready >= 0.25 + falls <= 1.3. Confirmatory on seed-206 data only.
- **LEVER (L vs C):** GAIN2 + r19_guards against the parent. A pass -> CONFIRM (pooled, fresh dev 4220341-48, parent / C / L re-read); else panel.
- **Reported, never a verdict:** the 3-training-seed estimate. The 8 historical comparisons stay as history (no re-reads of the parent, d1s3lr or lr2).
- **Calibration note:** on the historical reads, GAIN2 gives d1s3lr +0.82 and lr2 +0.15 lower bounds. It is used prospectively only.
- **Queued:** lever (a) (coach, motion) on the same base.

**Decision:** D-210.


## Round 75 (2026-11-04): D-210 reads RECIPE pass, LEVER-FAIL

Brief: footwork-round75-brief.md.

**Correction checks**
- **RECIPE PASS and LEVER-FAIL are valid as pre-registered** (all five recomputed them). The 3-training-seed estimate checks out (+2.12 / +1.45 / +3.03, SD 0.79).
- **GAIN2's per-seed SE measures eval noise only** (all five). It tests "this checkpoint beats the parent", not "the recipe works". Here the binomial SE (0.67) set the bound, so max() should stay. The training-seed SD (about 0.8 points per run) is in neither term.
- **"C is a matched control at no extra cost" overstates it** (experiment design, RL, architecture). L and C diverge from update 1, so L vs C carries about 1.1 points of training-seed SD. Cost-free, yes; matched, no.
- **LEVER-FAIL is "no gain over C", not harm** (experiment design, coach, architecture). L against the parent alone would pass GAIN2 (+2.57). The cross_forehand breach (-3.4) is about 1.3-1.4 sigma among 17 families; it stands as pre-registered. L's falls rise (418 vs 328 on about 370k hits, z about 3.3) looks real (coach).
- **Left out of the brief** (motion): C's ready 0.291 is a wide stance without the loading dip (dip 0.139 vs parent 0.321). C is slightly slower (feeder peak p99 2.71 vs 2.77 m/s; right contact 0.777 vs 0.795). Recovery p90 improved, 0.675 to 0.525 m. C's gain is steadier positioning and fewer falls, not agility.

**Backhand weights:** they reached cross_backhand (+6 points, about 2 sigma) but act only on the feeder ball, a zero-sum share of reps. By arithmetic, +6 on three of 17 feeder families is at most about +0.6 points of P(5+) (architecture). Close or park; do not re-dose (all five).

**Votes:** 5 of 5 for (i), CONFIRM C on fresh dev 4220341-4220348 (reads only).

| reviewer | gain line | mechanism bars | extra |
|---|---|---|---|
| Experiment design | GAIN2 | yes | prospective training-seed term for lever reads |
| RL | GAIN2 | yes | later guards stay on the original parent's reads |
| Coach | GAIN2 | yes | feeder >= parent - 0.01 |
| Motion | P(5+) >= parent | yes | Fast4 floor test next |
| Architecture | P(5+) >= parent | no | after CONFIRMED, pair C-continued with C + lever on seed 207 |

Lines: GAIN2 (3 of 5) + r19_guards + mechanism bars (4 of 5). Coach's feeder line is reported only.

**Next if CONFIRMED** (for round 76): C becomes the parent. Two proposals are on the table: C continued plus C + one lever on seed 207 (RL, architecture, coach), and the Fast4 floor test for the speed ceiling (motion).

**Decision:** D-211.


## Round 76 (2026-11-04): D-211 CONFIRMED; next step after promotion

Brief: footwork-round76-brief.md.

**Correction checks**
- **CONFIRMED is valid as pre-registered** (all five recomputed it).
  - Pooled P(5+) from the summed histograms is 0.4115 vs 0.3805 (coach); the brief's 0.4117 / 0.3818 are rally-weighted per-seed figures. The difference is immaterial; it is labelled from now on.
- **Guard reference** (RL, experiment design): round 75's "stricter" original-parent reference holds only on the same seeds. On other seeds it measures the seed change (parent low -5.3 against itself). RL withdrew its own round-75 claim. Guards now use same-seed references.
- **The brief's misstatements:**
  - the Fast4 floor test was not coded (motion, experiment design, architecture);
  - the hazards were from older parents (coach: on C, k = 3 is about 0.02);
  - court falls cannot come from the pairs reads, because robot_episodes equals robot_falls (motion, coach, RL).
- **A defect** (experiment design, architecture): lev74's +360 kill hard-coded start 31399, so a resume from C would never fire it.
- **Missing** (motion, reported): an agility read on C. C is slower in every direction on the fresh direction reads (peak p90 back 2.09 -> 1.97, right 2.16 -> 2.06 m/s).
- **Risk** (architecture): C sits at fast -4.6 against the original parent, about a 40 % chance of a noise breach on any child.

**Votes**

| reviewer | vote | lever / note |
|---|---|---|
| Motion | (ii) | approach_far paid before the bounce (new code); Fast4 deferred |
| Coach | (ii) | pair_rally_cap 5 (coded), smoke 208; OPEN / K3-KEPT / FEEDER lines |
| RL | (ii) | IdleRec with a critic warm-up; Fast4 floor read first |
| Experiment design | (i) | C2 only; the Fast4 floor read alongside |
| Architecture | (i) | C2 only; the Fast4 floor read as a tail; IdleRec needs new watcher code |

(ii) wins 3 of 5. The lever has no majority (1 / 1 / 1); least new code: the cap. Three of five want the Fast4 floor read, so it runs first (reads only).

**The larger lever (all five):**
- P(5+) is bounded by the opening: roughly (1 - h0)(1 - h1). Reaching 0.80 needs h0 of about 0.10 and h1 of about 0.08. Compounding alone needs about 13 steps, and the guards would stop it sooner.
- The feeder-ball limit is reach on the left / back and deep / fast / low families. Motion and coach read it as first-step commitment, not top speed.
- 97 % of pair-court experience is past the opening (architecture), so the k = 1 ball is starved of practice. That is the cap's premise.
- Next routes named: the pre-bounce intercept (motion), restart-state starts (coach, if the cap fails twice), and Fast4 -> d1b if the floor passes (RL, experiment design).

**Decision:** D-212.


## Round 77 (2026-11-04): D-212 NO-CANDIDATE

Brief: footwork-round77-brief.md.

**Correction checks**
- **NO-CANDIDATE is valid** (all five recomputed it). K fails on ready (0.211) alone.
- **K3-KEPT as coded mixed two things** (all five; coach owned the loose wording).
  - Endings at shots 3-4: K 0.0296 vs C2 0.0265, which would pass.
  - Endings past shot 5: 6.6 % of K's rallies that reached 5, vs C2 1.3 % and C 1.2 %. Most are past shot 10.
  - Re-scoring now would be a loosening (experiment design), so it is not done. Both splits are reported from now on.
- **Misstated by omission** (all five): the opening gain is measured against C2, which regressed. Against C, h0 and h1 move about -1.2 points each, OPEN is +0.016 (< 0.02), and GAIN2 is +0.87 (lower bound -0.48).
- **The cap's extra feeder balls were mostly easy restarts** (RL): legal 0.911 after a capped end vs 0.703 after a long rally.
- **"Does not compound" rests on one seed** (motion, architecture). Close the plain continuation; don't call it exhausted.
- **The Fast4 floor was read on 2-6 m spots**, not the kickstart's 0.5-3 m (motion).

**Motion's direction table** (contact / peak p90 / miss distance): no arm moved speed by more than 0.06 m/s. The rally policy uses about 2 m/s of a body that reaches 2.6-2.8 m/s.

**Votes**

| reviewer | vote | stage A lines |
|---|---|---|
| Coach | (ii) | ARRIVE >= 0.90; SETTLE >= fw - 0.03; SPEED L/B sustained +0.2 |
| Experiment design | (ii) | ARRIVE >= 0.95 and >= fw - 0.02; SETTLE L/B >= fw - 0.03; FASTER min(L,B) +0.10, falls <= fw |
| Motion | (ii) | ARRIVAL >= 0.90; SETTLE L/B >= fw; FIRST-STEP <= fw; DOSE peak L/B +0.10 |
| RL | (ii) | ARRIVE >= fw; SETTLE L/B >= fw; FIRST-STEP <= fw; stop rule gain2 vs C |
| Architecture | (iii) IdleRec on C | reported tail: SETTLE >= fw; FIRST-STEP <= fw + 0.05 |

(ii) wins 4 of 5. The lines were taken by majority per line, using experiment design's form where the forms differed:
- SETTLE (5 of 5) with no slack (3 of 5);
- FIRST-STEP (3 of 5) with no slack (2 of 3);
- FASTER (3 of 5);
- ARRIVE (4 of 4 who named it).

Stage B and the base gate are D-192's, unchanged (4 of 4).

**Decision:** D-213.


## Round 78 (2026-11-04): D-213 TEACHER-NOT-READY

Brief: footwork-round78-brief.md.

**Correction checks**
- **TEACHER-NOT-READY is valid** (all five recomputed it). FASTER decides it alone.
  - FIRST-STEP's left miss (0.012 s) is inside one 0.05-s bin: a tie at the instrument's resolution (experiment design, coach, motion).
  - "Fast4 falls less" is 0 falls against 3, not a measurable difference (experiment design).
  - "Settles more" holds only in sectors 2-6 (RL).
- **The instrument answered D-213's question** (does the kickstart's copy get faster on its own spots), not "is Fast4 faster" (all five).
- **Labels** (coach, motion): "first step" is the time to close 1.5 m. It is a short-distance speed measure, not a reaction time. "VERDICT: VOID" in the log comes from bodyspeed_rule and is not cited.
- **The brief's "IdleRec coded"** (architecture): d1s8_watch.py hard-codes run, start and checkpoint, so the run needs lev76's inline watcher from 32598.

**What we learned**
- **The court-scale limit is the task and acceleration** (all five).
  - Both teachers match an effective acceleration of about 1.0-1.5 m/s^2 (motion's point-mass fit). The time to 1.5 m stays at 1.3-1.4 s in every geometry.
  - 3-4 m/s needs more than 5 m to reach and stop. At court scale, agility is acceleration, braking and an earlier start.
- **Motion withdrew its round-77 under-use claim.** The rally policy's peak p90 (about 2.0 m/s) matches the teachers' court-scale p90 (1.85-2.05).
- **The feeder ball is a scramble ball** (coach): 52 % launch with the robot more than 1.2 m off its spot, legal 0.60. The first return is the STATE ball (D-204), the "get set while your partner hits" cue.
- **R3** (experiment design, architecture): pairs episodes reset only on falls, so the per-episode rate reads 1.0.
  - On falls / (falls + envs), C reads about 5 %, which fails 4.0 % on that unit.
  - The target's R3 is the h5f court read, which has not been read on C.
  - Architecture: do not change the field (hitting() gates on it); add reporting.

**Votes**

| reviewer | vote | lines |
|---|---|---|
| RL | (i) | gain2 vs C, guards, bars, H1 <= C - 0.03, K3-KEPT + FEEDER vs C; withdraws (ii) |
| Experiment design | (i) | split reads 4220365-66 for DOSE / HAZARD, guards, bars, GAIN2; R3 reporting line |
| Coach | (i) | H1 <= C - 0.03 and h0 <= C + 0.01, LATE two splits, GAIN2, guards, bars, FEEDER; approach_far next |
| Architecture | (i) | lev76 copy, climb + farm kills from 32598, lever_lines vs lev74-C, bars; R3 court read on 4220365 |
| Motion | (iii) | pre-bounce horizontal approach_far, LEFT +0.05, BACK guard |

(i) wins 4 of 5. Lines by majority among the four:
- gain2, guards and bars (3-4 of 4);
- H1 (3 of 4; the pooled form 2 of 3);
- FEEDER (3 of 4);
- K3-KEPT in lever_lines' form (2 of 4), with both splits reported.

Experiment design's split reads (1 of 4) are not adopted.

**Decision:** D-214.


## Round 79 (2026-11-05): D-214 IdleRec on C reads KILL-NO-CLIMB

Brief: footwork-round79-brief.md.

**Correction checks**
- **KILL-NO-CLIMB is valid** (all five recomputed it).
  - The "0-60" window began at +22, and its first segment is a reset transient (0.549). The steady climb was about +0.005-0.008, so the verdict holds on any baseline.
  - Experiment design: starting at iteration 0 would have read 0.43, a spurious +0.08 "climb" (CONTINUE). From now on, windows start at a logged row at least 30 iterations in.
- **The line was fair** (all five): hit_done steps sit at 0.73-0.74, so there was headroom.
- **The dose was small:** about 7 % of recovery-paid steps (RL, experiment design, coach, motion).
- **The brief's "four levers on C" was wrong** (RL, experiment design): K and R only.
- **R3 is a second open gate** (architecture): every h5f read on this lineage fails 4.0 % on falls_court (5.2-6.5 %).

**The finding of the round: the stale stance target** (motion; verified by architecture, by the agent in code and C's params, and by a GPU test).
- With the planner off, stance_xy stays (0, 0), the net centre.
- stance_progress (weight 1.0) has paid pelvis speed toward the net on every live ball: walking forward is rewarded and backing up penalised.
- Its pay is about 3x approach_far's.
- It fits C's back 0.40 / left 0.31 vs forward 0.87 direction legal, and the late start found in round 78.

**What we learned:**
- Reward levers paid on a small slice of steps have failed five times.
- The LR 3e-5 recipe holds C near itself (KL about 0.006, std at its floor).
- Only K (a change in state distribution) moved the opening.

**Votes**

| reviewer | vote | form |
|---|---|---|
| RL | (i) pre-bounce approach_far | dose-climb kill; OPEN / FEEDER / K3 / gain2 |
| Coach | (i) pre-bounce approach_far | H0 <= C - 0.02, LEFT, BACK; then restart-state starts; then STOP to shared-policy self-play |
| Experiment design | (v) the cap on half the courts | lever_lines vs lev74-C, share / farm kills |
| Motion | (v) BallStance: stance_xy retargeted on every fire (launcher and hand-off) | BACK +0.05, FWD guard; withdrew (i) (pre-bounce paddle-ball pulls toward the net too) |
| Architecture | (v) court_feed_stance with the planner off (launcher only) | H0 <= C - 0.03, FEEDER, K3; R3 court read first |

No majority (2 / 2 / 1). Least new code: the stance fix in architecture's form (an opt-in flag, about 3 lines).
- Motion's hand-off extension is the next step if the feeder ball moves.
- Motion's BACK / FWD lines are reported.

**Decision:** D-215.


## Round 80 and 80b (2026-11-05): D-215 NO-CANDIDATE; a correction before launch

Brief: footwork-round80-brief.md; correction footwork-round80b-brief.md.

**Correction checks (round 80)**
- **NO-CANDIDATE is valid** (all five). GAIN2 and H0 fail on their own.
  - The backspin breach is about 2 SE of noise (coach, experiment design). Children's worst family moves each time (C fast -4.6, C2 low -4.2, K backspin -3.4, F backspin -5.1).
- **"Std at its 0.1 floor" was wrong** (RL, motion, architecture): 3 of 35 outputs are at the floor; mean action std is 0.20.
- **"Five changes on C" was wrong again** (experiment design, coach): only K, R and F were levers on C.
- **Labels:** cfs79 labels F as "R" (RL, coach, experiment design, architecture).
- **F's loss sits at h1 +1.6, not h0** (coach).

**What we learned (round 80)**
- **Optimizer:** KL is 0.0054 and flat; value loss is flat; training reward plateaus by +300; entropy falls (RL, architecture). C is the best of three recipe seeds, so resumes regress about 1 point (RL, architecture).
- **F cut stance_progress pay to about 0** and P(5+) did not move. F cut pair-play falls 20 % (motion).
- **Opening states:** about 96 % of feeder balls follow a 0-1-shot rally; legal 0.59-0.60 in every arm; 51-53 % of receivers more than 1.2 m off spot (experiment design).
- **Practice is easier than the read:** 28 % off-spot in training vs 51 % at read; feeder legal 0.72 vs 0.60-0.64 (coach).
- **R3:** falls are torso tilt above 70 deg; 69 % happen during long-move feeds on the court battery; C's task has no fall term (motion).

**Votes (round 80):** (iii) 2 (coach: pair_drill_court_frac 0; RL: random rally ends); (i) std floor 0.2 (architecture); (vi) launch-distance read (experiment design); (iv) the D-063 fall penalty (motion).

**Round 80b correction (the agent):**
- Coach's zero-code form spreads drills over every court (D-162 reversed), not "every court live".
- The launch log already counts only the live courts.
- All five confirmed this; coach withdrew the form.

**Re-votes (round 80b):** (vi) 2 (coach, experiment design, the latter amended with a noise-on read); (i) 1 (architecture); (iii-RL) 1 (RL, plus KILL-NO-DOSE); (iv) 1 (motion, accepting (vi) as a first step).
- No majority. Least code ((i)) and fewest moving parts ((vi)) disagree, so experiment design's position decides: (vi).
- Routes are experiment design's lines; coach's route is reported.

**Decision:** D-216.


## Round 81 (2026-11-05): D-217 killed at +360; the dose did not arrive

Brief: footwork-round81-brief.md.

**Correction checks**
- **The KILL is valid as coded** (all five).
  - Both firing lines are built into the lever: cut balls log as misses, and cuts shorten rallies.
  - The proposer (RL) and architecture own the error, as does the agent, which adopted the list without checking it against the lever.
- **KILL-NO-DOSE could never read at +360:** the pair log writes every 100 iterations (all five). From now on, kills must be readable at smoke.
- **The dose failure closes this lever** (all five). The per-window off-spot share fell 0.356 -> 0.259 -> 0.224: the policy recovered closer as feeder balls became 3x as common.

**What we learned**
- **The far state is already practised:** about 18,000 far launches in training, legal 0.48-0.51 (coach).
- **The read's receiver is still moving:** > 0.5 m/s at launch 48 % at read vs 28 % in training (RL, coach).
- **The spawn ball:** about 31 % of the read's feeder-type balls vs 6 % in training (architecture). It does not enter len_hist, so it moves the FEEDER line, not P(5+) (RL). It may be the known pair-reset leak (motion).
- **Unfrozen base is costed:** 80-400 lines and about 6 GPU h, with a high risk of hitting collapse (architecture).

**Votes**

| reviewer | vote |
|---|---|
| Coach | (iii) STOP: unfrozen-base rally fine-tune; far-bin legal >= 0.52 gate |
| Experiment design | (iv) 120 s / 240 s read -> SPAWN-BINDS (episode length 30) / MID-BINDS (post-bounce cut) |
| RL | (i) feed the robot furthest off spot (about 3 lines), dose >= 0.40 at smoke; else STOP |
| Architecture | (ii) episode length 24 s, reset-bucket dose >= 0.18 |
| Motion | (iv) --audit-fixes re-read (pair-reset leak) -> LEAK-BINDS / feed the chaser |

No majority. Fewest moving parts: (iv), reads only. Experiment design's form routes; motion's read is reported.

**Decision:** D-218.


## Round 82 (2026-11-05): D-218 INVALID-SPLIT; the first feeder ball is the loss

Brief: footwork-round82-brief.md.

**Correction checks**
- **INVALID-SPLIT is valid** (all five). The guard is a validity condition written before the pooled verdict.
  - Experiment design: the `or s_k < 0` clause came after the verdict (immaterial, labelled), and the split itself was its design error.
  - Coach: dist80b's open_len_hist already showed 1,016 of 1,024 courts rallying at the end, so the split could never work.
- **"Run to the timeout" is wrong** (architecture): --rally sets the episode to the read length + 1 s, so there is no time-out.
- **"About 1,024" is exact:** one spawn feeder ball per court (architecture).
- **The first feeder ball counts in P(5+) and H0** (RL, architecture). Round 81's "FEEDER only" held for the leak ball.
- **The instrument can split the first ball** (coach, motion, architecture): court_counts column 2 gives q0 0.25-0.29 and q1 about 0.51.
- **Motion withdrew its round-81 leak hypothesis.** The audit-fixes drop in feeder legal is on different seeds, so it is not attributed.

**What we learned**
- **P(5+) is about 1 / (1 + (1 - q0) / q1) = 0.41**, so the whole gap is the opening. Within-rally legal is 0.98-0.99.
- **The spawn feeder ball converts 0.26.** About 80 % of spawns sit more than 1.2 m from the spot, and the ball comes 0.5 s after start.
- **Ceiling:** P(5+) <= 0.57 at today's q0. The target needs q0 >= 0.75 (architecture).
- **Training sees episode starts about 5x less often than the read weights them.**
- **The target and read stay unchanged.** The spawn-start scramble is a legitimate footwork skill; loosening is defined in D-219.

**Votes**

| reviewer | vote |
|---|---|
| RL | (i) first-ball tally (about 15 lines), FIRST-BINDS -> 24-s episodes |
| Experiment design | (i) first-ball tally, SPAWN-BINDS -> 24-s episodes |
| Coach | (ii) 24-s episodes; withdraws STOP |
| Motion | (ii) 24-s episodes; court_counts already shows the premise |
| Architecture | (ii) 24-s episodes; q0 >= C + 0.08 as a mechanism line |

(ii) wins 3 of 5.
- Kills: D-194's lines and KILL-NO-DOSE at smoke and at +360; KILL-FARM reported only (2 of 3 of the (ii) voters).
- Endpoint lines unchanged; q0 / q1 reported.

**Decision:** D-219.


## Round 83 (2026-11-05): D-219 SMOKE-FAIL; the dose line measured the wrong ball

Brief: footwork-round83-brief.md.

**Correction checks**
- **SMOKE-FAIL is valid as coded** (all five). The window error is the agent's.
- **The dose line measured the leak-ball bucket, not the spawn feeder ball** (all five). Experiment design owns the D-218 line. Architecture traced why only about 1 in 5 resets reaches the bucket.
- **The spawn exposure did arrive:** 0.43 vs C2's 0.26 post-reset share; resets per live env-s 4.7x (architecture).
- **The brief's "6 %" and "large majority" were misstated** (RL, architecture).
- **The pair log writes each step 4 times;** _row_from takes the first copy, so no number changes (experiment design).

**What we learned**
- The spawn box reaches 4.1 m (median 2.1 m) and the ball arrives 1.6-2.2 s after spawn (motion). q0 >= 0.75 needs moving contact at about 2 m/s; the frozen base plausibly reaches q0 about 0.4-0.5.
- Far-ball legal is 0.44 in training vs 0.42 at read (coach): a capability limit, unless the spawn state itself is the gap (RL, architecture).
- Ceiling: 0.80 needs (1 - q0) / q1 <= 0.25 (experiment design).

**Votes**

| reviewer | vote |
|---|---|
| RL | (ii) reset both envs of odd live courts at rally end (p 0.5), fresh-ball tally; STOP if q0 < C + 0.08 |
| Motion | (ii) spawn restart after every rally on odd live courts; STOP to a base-agility retrain if q0 < C + 0.10 |
| Experiment design | (i) 12-s episodes with a first-ball counter, q0 >= C + 0.08 gate; any failure -> STOP |
| Coach | (iii) STOP to court-scale quickness (Fast4 on 0.5-3 m spots, fast4_check gate) |
| Architecture | (iv) relaunch 24 s with a corrected dose line; STOP to a distil-then-PPO joint fine-tune if q0 does not move |

No majority. Least new code / fewest moving parts: (iv). All five agree that a q0 miss after the dose arrives means STOP.

**Decision:** D-220.

## Round 84 (2026-11-05): D-220 NO-CANDIDATE; the STOP fires; name the footwork-base phase

Brief: footwork-round84-brief.md.

**Correction checks**
- NO-CANDIDATE is valid and the pre-registered STOP fired (all five).
- The brief's "K3-KEPT 0.028 vs 0.012" is the reported 5+ split; the coded line is 0.0495 vs 0.0331 (all five).
- "Far legal 0.42 -> 0.45" compares unpaired reads (dist80b vs D-204's seeds); not a measured move (RL, motion, coach, experiment design).
- "Five times the practice" overstates it: resets per env-s 4.7x, post-reset share 1.8x (RL).
- "Within-rally legal 0.98-0.99" is false for shots 1-2: h0 0.374, h1 0.259; the product matches P(5+) (experiment design).
- First-step time and time to 1.5 m are one instrument (architecture, coach).
- (c) d1 + --recover was withdrawn in round 78; --recover copies the walker only after the first contact, so it cannot reach the spawn ball (RL, architecture).
- Kickstart ball episodes copy s5c-17's footwork, not the walker's (RL).

**Votes:** (a) stage 1 only, 5 of 5. Parents: fw1b-S 4 (architecture, motion, coach, experiment design), Fast4 1 (RL). Forms: deadlines tightened (architecture, motion), Fast4 on court spots (RL), spots only (experiment design), first-step bonus (coach). Architecture withdrew (d).

**Round 84b (form re-vote):** the agent verified the coach's fact (Fast4's training first step flat at 1.325-1.375 s over 1,500 iterations) and asked all five again. F2 (court spots, pay settled, deadlines unchanged, plus a first-step bonus) 5 of 5. QUICK margin -0.25 (RL, experiment design) / -0.20 (coach, architecture) / -0.15 (motion): experiment design's. Kill +0.10 s (4 of 5). Fail reading split (D-221).

**Decision:** D-221.

## Round 85 (2026-11-05): D-221 KILL-NO-START at +470; the start moved 0.074 / 0.086 s

Brief: footwork-round85-brief.md.

**Correction checks:** KILL-NO-START valid as coded (all five). The early window held start-up adaptation that made the line generous (coach, experiment design, motion, RL, architecture). Left levelled off near 1.305 s; back still falling (RL, motion, architecture, experiment design). The dose rise also reflects the new task (coach). "Flat" had no number (experiment design). Stochastic vs mean actions (RL, architecture, experiment design).

**Reading:** moving -> recipe limit (5 of 5).

**Votes**

| reviewer | vote |
|---|---|
| RL | (ii) read model_17000 at mean actions, then (i) or (iii) by rule |
| Motion | (i) span 0.5; kill from 60-100 |
| Coach | (i) span 0.5; kill unchanged |
| Experiment design | (i) span 0.5; kill unchanged; flat = < 0.05 s |
| Architecture | (i) span 0.5, gated on a premise read (>= 0.05 s faster at mean actions) |

Form (i) 5 of 5; no premise read 3 of 5; kill unchanged 3 of 5. A fail closes the start-reward sub-route (4 of 5).

**Decision:** D-222.

## Round 86 (2026-11-05): D-222 KILL-NO-START; the start-reward sub-route closes; name the next phase

Brief: footwork-round86-brief.md.

**Correction checks:** the kill and the closure are valid (all five). The heading reading was confounded by the drill's 1-m yaw lock and its midpoint sampling (all five). Fast4 turned laterally on long spots without a faster start; back never turned (experiment design, RL). Forward first step is no faster than back (motion). h1 levers had been tried (coach, experiment design, RL).

**Votes**

| reviewer | vote |
|---|---|
| RL | (ii) h1 attribution read on C (BALL / POSITION / MIXED) |
| Motion | (iii) distil-then-PPO joint fine-tune |
| Coach | (i) heading free to 0.3 m (drop step) on Q2's task |
| Experiment design | (iii) distil-then-PPO joint fine-tune, FIDELITY gate first |
| Architecture | (i) heading free to 0 on Q2's task, KILL-NO-TURN |

No majority (2 / 2 / 1). Least new code and fewest moving parts: (ii).

**Estimates:** best reachable P(5+) about 0.45-0.55 (all five); 0.80 not shown reachable on this stack.

**Decision:** D-223.

## Round 87 (2026-11-05): D-223 INVALID (first hand-off tally over-counts about 2 %)

Brief: footwork-round87-brief.md.

**Correction checks:** INVALID right (all five). The over-count is the reset env's own leak ball carrying a stale `handed` / class after the court restarts (architecture traced the exact path; motion, coach, RL, experiment design concur). The arithmetic closes exactly once the 35 / 31 are removed (motion, architecture). A leak-ball miss also ends about 1 % of live rallies (coach, architecture, experiment design); reported, not re-scored. A second, untested path: early volley faults (RL).

**Votes:** (i) fix and re-read, 5 of 5. Fix form: a separate ho_live flag, `handed` untouched (all five). Read size: 4 seeds (coach, RL), 3 (motion), 2 (architecture), re-read 4220375 plus 1 (experiment design). No majority; tie rule -> experiment design's.

**Estimates:** unchanged at 0.45-0.55; if the split holds, the perfect-reach ceiling falls to about 0.65-0.69.

**Decision:** D-224.

## Round 88 (2026-11-05): D-224 BALL; design the hitter-side lever

Brief: footwork-round88-brief.md.

**Correction checks:** BALL valid as coded (all five). The early-volley feeds cannot flip it (all). BALL controls distance only, not the receiver's motion (motion, coach, architecture). (i) and (ii) re-weight terms C already pays (RL, architecture). Position is the larger share of h1: 64 % of first hand-off misses are beyond 1.2 m (experiment design).

**Votes**

| reviewer | vote |
|---|---|
| RL | (i) partner credit x2 on the first hand-off |
| Motion | (iii) read: ball descriptors + receiver speed / ready flag, route on set vs moving receivers |
| Coach | (iii) read: ball descriptors + receiver speed, diag68-style reweighting route |
| Experiment design | (i) partner_first_return 150; one dose only |
| Architecture | (iii) read: keep_alive / |v| / |spin| by class + receiver speed; medians route |

(iii) 3 of 5. Form: least new code, architecture's.

**Estimates:** h1 about 0.19-0.21 under the best lever; P(5+) about 0.45; overall 0.45-0.55.

**Decision:** D-225.

## Round 89 (2026-11-05): D-225 NEITHER; STOP the footwork phase

Brief: footwork-round89-brief.md.

**Correction checks:** NEITHER valid; the multi-count is confirmed in code (substep booking), so the counts are void and the quantiles are near unbiased (all five). The keep_alive instrument is blind (experiment design, RL, motion). The receiver tally over-books faulted hand-offs by 12 %, but the tail survives (experiment design). The first-hand-off ball is off the groove: 3x the speed spread, 6x the spin spread (coach).

**Votes:** (v) STOP 4 (architecture, motion, coach, RL); (i) then STOP 1 (experiment design).

**Estimates:** best reachable P(5+) about 0.45-0.55; 0.80 not shown reachable on this stack.

**Asks for the user:** a set start (architecture, motion); a body or controller rebuild (coach: agile reference motion; RL: actuation review; experiment design: from-scratch controller).

**Decision:** D-226. Next phase named in round 90.

## Round 90 (2026-11-05): name the next phase after the footwork STOP

Brief: footwork-round90-brief.md.

**Corrections to D-226:** specialist count double-counted; mixed instruments in "1.26-1.41 s"; 1.1 s is an estimate; within-rally 0.98-0.99 holds only from shot 3; the set-start projection is about 0.71 (plan 0.65-0.75); a set start is a loosening and is reported only (experiment design); D-006 must be superseded for a from-scratch controller (architecture).

**Votes:** (b) from-scratch controller, opened with a premise run (Q2's task from a random init), 5 of 5; (a) set-start read first, 5 of 5. Iterations 6,000 (coach, architecture, experiment design) vs 4,000 (motion, RL). Kill windows differed; experiment design's form.

**User brief:** stopped at 0.41 (best 0.45-0.55); first ask the set start (measured now), then the body or controller.

**Decision:** D-227.

## Round 91 (2026-11-06): the user's answers (D-228)

Brief: footwork-round91-brief.md.

**Correction checks:**
- 0.607 is a 3-s pause, not a set start, and it was unpaired (all five; RL on the seeds).
- Velocity limits are not enforced (motion, architecture, experiment design).
- The action scale is tied to effort / stiffness at import (motion, architecture, experiment design).
- Damping may be the brake (motion).
- No saturation evidence yet (RL).
- "Humanlike" stays a requirement (experiment design).

**Set start:** a drill reset (place both robots on their spots at every rally start; feeder after 0.5 s), 5 of 5. Read C as the new baseline (all five), on new pooled seeds with the old read alongside (experiment design).

**Actuation:** a saturation / zero-shot premise read first (motion, architecture, RL; coach and experiment design: a zero-shot read); then effort x2 on legs, waist and ankles with the action scale kept, as Q2 from fw1b-S (all five; motion's damping alternative recorded).

**Reference:** ask for the SMPL-X registration now; pilot on the session on disk; a named subset after (all five). Clips go into the AMP style reward (all five). Coach: extract the footwork between strokes.

**Order:** fw-scratch-01's kill read, then the premise read, the set-start baseline, then the effort run (all five).

**Decision:** D-229.

## Round 92 (2026-11-06): effort ruled out; C's set-start baseline 0.5645; name the next step

Brief: footwork-round92-brief.md.

**Correction checks:**
- The bar on the new read needs (1-h0)(1-h1) >= about 0.87 (RL, experiment design, architecture).
- A placed robot's feeder legal is 0.762 against the old near-spot 0.90: an unpractised start state (motion, coach, experiment design).
- Effort is ruled out only for the clamp; actions are unclipped and the policy never asks (RL, experiment design, coach).
- The actuator routes act under the frozen decoder and base (architecture, RL).
- fw-scratch-01 does not settle the lineage question (motion, coach, RL).

**Votes:** (d) practise the new read, 5 of 5.
- Architecture added a required guard: never place drill-court or busy robots.
- Kill and gate forms differed; experiment design's form was used.

**Order:**
1. (d).
2. The damping zero-shot premise read (reported).
3. The reference pilot once SMPL arrives.

**Estimates:** (d) +3-8 points; 0.80 still needs the actuator and reference routes.

**Decision:** D-231.

## Round 93 (2026-11-06): D-231 P(5+) 0.7236 on the set-start read; NO-CANDIDATE on R3 alone

Brief: footwork-round93-brief.md.

**Correction checks:**
- NO-CANDIDATE valid; R3's read is right (all five).
- R vs C R3 was unpaired (RL, experiment design, coach).
- D-063's fall penalty is the precedent (RL, motion, experiment design, coach).
- The rally lineage raised falls from the d1 base's 0.032 (architecture).
- Falls split: 264 in feeds, 93 between feeds (coach, architecture).

**Votes:** (i) fall penalty on R, 5 of 5.
- Term: D-063's -50 (4) vs -250 (architecture).
- R as an unpromoted warm start, gated in full against C (5 of 5).
- R-KEPT (4 of 5).
- A mid-run court read kill (5 of 5; experiment design's form).
- KILL-LOST-OPEN (3 of 5).

**Estimates:** R3 fixable; P(5+) about 0.74-0.80 with one more opening lever; 0.80 not yet shown.

**Decision:** D-232.

## Round 94 (2026-11-06): D-232 KILL-NO-FALLS; the R3 route

Brief: footwork-round94-brief.md.

**Correction checks:**
- KILL-NO-FALLS valid (all five).
- Rally training's recovery is fixed by the run's CLI (experiment design); architecture read the task default.
- No solo launcher courts in training (all five).
- The court read has about 15x the cold spawns (architecture).
- The base's 0.032 is from another instrument (coach, motion).
- R's falls are diffuse, easy families included, and between-feed falls tripled (motion, RL, experiment design).

**Votes**

| reviewer | vote |
|---|---|
| RL | (i) R continued on the court read's task (zero task code) |
| Motion | (i) court-read episodes on half the drill courts |
| Coach | (ii) premise read (time since reset, phase, distance, family) on R and the base |
| Experiment design | (i) random recovery on the drill courts only |
| Architecture | (ii) premise read with a SPAWN / RECOVERY / FEED route |

(i) 3 of 5. Forms differed; least new code: RL's.

**Asking the user (iv):** not warranted now (experiment design, RL, motion).

**Decision:** D-233.

## Round 95 (2026-11-06): D-233 KILL-NO-SAFER; the R3 premise read

Brief: footwork-round95-brief.md.

**Correction checks:**
- KILL-NO-SAFER valid (all five); the manual stop at +217 follows the coded kill and nothing after +125 is used.
- The base's 0.0318 is from another instrument; it needs a read on R3's own (RL, architecture, coach).

**Votes**

| reviewer | vote |
|---|---|
| RL | (ii) the d1 base as a zero-residual checkpoint (residual_init.py) beside R, paired dev 4220394-4220395 |
| Motion | (ii) the premise read first; the mixed form if FEED |
| Coach | (iii) a longer court practice plus the fall penalty |
| Experiment design | (ii) with pre-registered routes; random recovery on drill courts if RECOVERY |
| Architecture | (ii) a fall log: time since reset (0.5-s bins), phase, distance from the recovery spot, family |

(ii) 4 of 5. Routes (d1_rule.r3_route): INVALID (booked falls != robot_falls); BASE-FAILS (base R3 > 0.04 on R3's
instrument) -> put the facts to the user (iv); SPAWN (>= 50 % of R's excess within 1.0 s of the episode start) -> the
user (iv); RECOVERY (>= 50 % between feeds after 1 s) -> random recovery on drill courts only, warm start R, full gate;
FEED (>= 50 % in feeds after 1 s) -> the mixed form (court-read episodes on drill courts); else MIXED -> panel.

**Asking the user (iv):** only on BASE-FAILS or SPAWN.

**Decision:** D-234.

**Result (D-234):** FEED (R 63 % of the excess in feeds after 1 s; base 0.0345 passes R3 on R3's instrument). The excess
sits mostly in the first feed after the spawn and the recovery after it. Route -> D-235 (launcher courts in the
drill-reset rally training, motion's mixed form), D-232's lines.

## Round 96 (2026-11-06): D-235 killed on a defective line; continue

Brief: footwork-round96-brief.md.

**Correction checks:**
- KILL right as coded (all five).
- "Defective line" is honest (all five). Architecture: mjlab logs the mean episode reward sum / 120 s, so 8-s launcher episodes count at about 1/15 and dominate the resets. L's line rose 0.03 -> 0.53. Experiment design: mean episode length 5,791 -> 2,367 steps while legal_return per step rose 1.71e-4 -> 2.06e-4.
- **Withdrawn (RL, architecture): the agent's "rally length 6.97 vs 4.75" is a mix artefact too.** Pair-court rallying is flat-to-up: L 14.29 vs R 12.84 vs D-232's 14.23 mean length over +241-360.
- launch.outcome_feeds_legal and outcome_by_d include launcher feeds; never use them for lines (experiment design, architecture).
- The 4.157 smoke line is ~10x loose on the exact count. Experiment design wants a new D-entry (0.64); the others say leave it as a sanity check.
- The D-194 falls estimator is biased by the synchronised time-outs (motion, RL).
- The heading "works on R3" overclaims: one seed, a non-endpoint checkpoint. "Promising" (experiment design, RL).
- The watcher stops at the first kill; read every line before stopping (experiment design).

**Votes**

| reviewer | vote |
|---|---|
| RL | (i) rerun from R; pair-court P(5+) line and exact falls |
| Motion | (ii) continue from model_34160; exact counts |
| Coach | (ii) continue, if a corrected line passes on the +360 logs first |
| Experiment design | (i) rerun; continuing after the hand read is a rescue |
| Architecture | (ii) continue; pair-court mean rally length >= 0.9 x R's (about 3 lines of code) |

(ii) 3 of 5. Line forms: architecture's (least code, within the winning bloc) for KILL-NO-HIT; RL's / motion's exact off-launcher falls with D-194's value 3.14 for KILL-UNSTABLE.

**Estimates:**
- R3 <= 0.04 at the endpoint: 45-60 %.
- R-KEPT: about 65-75 %.
- P(5+) >= 0.80 with Wilson low >= 0.78 from this run: 5-15 %. The opening (1-h0)(1-h1) of about 0.66 is still the gap.

**Decision:** D-236.

## Round 97 (2026-11-06): D-236 NO-CANDIDATE on the left + back guard; left/back move-drill emphasis

Brief: footwork-round97-brief.md.

**Correction checks:**
- NO-CANDIDATE right as coded (all five). Unrounded: 0.40514 vs 0.40573; the miss is 0.06 points. The guard stays.
- **The cause in D-236's result is wrong (RL, motion, experiment design).** Most of the left loss came with R, which had the full drill dose: left C 0.407 -> R 0.364 -> M 0.346. D-235 adds about 1.8 points (about 1.2 SE). Fair wording: "the drill-reset line of runs wears away left contact; the dose cut may add to it."
- **The feed count was wrong (experiment design):** left + back pools 2,982 feeds for M and 2,971 for the reference, not about 1.5k. The SE of the difference from R is about 1.3 points.
- **Labels (coach, experiment design):** lc98-summary prints M under "R"; its R3 comparison quotes R's pooled value. The same-seed value is 0.0596.
- **Not footwork loss (motion):** M's left p90 peak speed rose (C 2.04, R 2.06, M 2.15 m/s). What changed is lower effort on misses (median miss peak speed down about 0.1 m/s) and a larger recovery error (R 0.325 -> M 0.475 m).
- **The dose did halve by construction (architecture).** (i) cannot restore it without halving the pair courts or dropping swing episodes.
- launch.outcome_feeds_legal / outcome_by_d include launcher feeds; logging only (architecture).
- With the guard at the line on the same seeds, a pass by noise is likely; CONFIRM must re-read the guard (RL, experiment design).

**Votes:** (ii) 5 of 5. Forms:
- weights x2 on sectors 2-4 (RL, motion, experiment design; coach left x2 / back x1.5; architecture x3);
- kill at +180 (coach, motion, experiment design);
- a direction kill (coach, RL, motion; RL's -1-point form, the median);
- M-KEPT (all); R3 on fresh dev 4220403 (coach, experiment design, architecture);
- a smoke check of the sector share (RL, architecture).

**What would count as selecting on noise (experiment design):**
- re-reading M on other seeds or checkpoints;
- calling -5.06 "-5";
- treating a -4.9 child as fixed before CONFIRM;
- claiming a gain over M under about 2.6 points (2 SE).

**Estimates:**
- Guard passes: 55-65 %.
- Target from this run: under 5 %.
- Target within 3-5 runs: 20-50 %.
- **Next binding lever: the opening** (h0 0.128 -> about 0.08, h1 0.096 -> about 0.06).

**Decision:** D-237.

## Round 98 (2026-11-06, narrow): D-237 SMOKE-FAIL on the sector share

Brief: footwork-round98-brief.md.

**Correction check (all five):** SMOKE-FAIL right as coded. The issued counter books the sector after the flip, which is what the policy practises. The agent set the 0.45 line from the 0.545 pre-flip share without allowing for flips; architecture flagged flips in round 97 but gave no figure. Flip rates from the counts: left about 15-21 %, back-left about 25 %, back about 16-17 %; front sectors almost never.

**Votes:** (a) 5 of 5. Weights (1,1,3,3,3,1,1,1), every line unchanged including >= 0.45. Predicted share about 0.51 (about 10 SE above the line).

**Additions:**
- Reported only: the right feeder contact N vs M (the right sector falls to about 7-11 % of spots).
- Per-sector shares.
- If x3 also fails the line, stop for a new round; no automatic x4 and no re-derived line (RL).
- Fresh run name and output directory (experiment design).

**Decision:** D-238.

## Round 99 (2026-11-06): D-238 KILL-NO-HIT on a restart-censored line; continue

Brief: footwork-round99-brief.md.

**The brief had factual errors (motion, RL, experiment design, architecture):**
- N did not stop at +185. The kill watcher's dev reads shared the GPU for about 30 minutes while training continued, and pkill landed near +349-364.
- Checkpoints exist up to model_35320 (+324), not 35160.
- The "+180" dev reads were taken on model_35200 (+204).

**Correction check:**
- The KILL is right as coded (all five).
- **The dip is a measurement artefact (architecture, RL):** after a restart every court begins at once, so long rallies are not yet finished. The 64+ bin is 0.000 in every +61-180 window and 0.031-0.035 afterwards, worth about 2 shots of the mean.
- **The line defect is the panel's:** D-236 used D-236's paired form ("at the same offsets"); D-237 dropped it and rounds 97-98 approved that (coach, experiment design).
- **Paired, read after the kill (labelled as such):** N +181-300 14.054 vs M 14.289 (0.98x); N +241-360 14.19 vs 14.26.

**Votes:**

| option | votes |
|---|---|
| (i) continue N from model_35320 | 4 of 5 (motion, architecture, RL, experiment design) |
| (ii) rerun from M | coach |

**Form (experiment design / RL):**
- The paired line is frozen now: N +181-300 >= 0.9 x M's +181-300 (12.86). It passes.
- Resume to the fixed endpoint model_35595 as rally-d1s3drl6, seed 241, with a fresh share log.
- No later rally-length line: the remaining 275 iterations are shorter than one post-restart window.
- Gate and CONFIRM unchanged.

**Standing rule:** any rally-length line is paired at the same offsets after a (re)start and starts at +181 or later. Kill watchers record the actual stop iteration.

**Estimates:**
- Guard passes: 60-70 %.
- P(5+) 0.74-0.77 from this run.
- Target from this run: under 5 %. Within 3-6 runs: 20-40 %, via the opening (h0, h1).

**Decision:** D-239.

## Round 100 (2026-11-07): D-239 NO-CANDIDATE on K3-KEPT

Brief: results/footwork-round100-brief.md.

**Correction check (all five):**
- D-239 ran as registered. NO-CANDIDATE stands.
- **The K3 fail is real.** N has 168 late failures of 4,261 rallies that reached shot 3 (0.0394); M has 116 of 4,210 (0.0276): +1.18 points, SE 0.39, and all four seeds rise. It costs about 0.5 points of P(5+); the "5+ ended" half does not touch P(5+).
- **Brief corrections:** there was one left / back dose (N, 600 iterations in two legs), not three runs (experiment design). The left 0.34 is a direction-probe read; nothing yet shows how much of h0 / h1 it accounts for (coach, architecture). On the gate's own feeder ball, reach_deep went 0.241 -> 0.342 and cross_backhand 0.525 -> 0.610 against M (motion).
- **Implementation defect, the second time (experiment design):** the kill watcher let training run past a coded KILL (D-233, D-238). From D-240, training-log lines are read first and stop training at once; the watcher records the actual stop iteration.
- **Body-level cause of the K3 rise (motion):** recovery error median 0.475 -> 0.525 m, paddle speed 5.36 -> 5.21 m/s; the move dose pulls the robot off its spot.

**Votes:** (i) 5 of 5, parent M.

| member | lever |
|---|---|
| RL | training-only pair_rally_cap 8, all courts (no new code) |
| experiment design | pair_rally_cap 20, all courts; revised to 8 after the agent's correction (below) |
| architecture | pair_rally_cap 8 on half the pair courts (about 15 lines) |
| coach | pair_rally_cap 5 on half the pair courts (about 15 lines) |
| motion | FeedMix x3 on reach_deep, cross_backhand, reach_backhand |

**Agent correction to experiment design's premise:** experiment design assumed pair-court rallies run about 70 shots. M's training log says 15.75 balls per rally (feeder share 0.0667). From M's length histogram the predicted feeder share is 0.247 at cap 5, 0.185 at cap 8 and 0.107 at cap 20 (about 1.6x). Experiment design revised its vote to cap 8 with a smoke line of 2.0 x M's share.

**Decision (majority and the tie rule):** the training-only pair_rally_cap, value 8 (RL, experiment design, architecture), on all courts (the least-new-code form). Kill and smoke lines in experiment design's form; OPEN as a gate line (RL, coach, architecture).

**Rejected (ii) (all five):** effort is not binding (D-229); any actuator change sits under the frozen decoder and d1 base (15-20 GPU h). The simpler first step, the damping / action-scale premise read queued since round 92, should run first.

**Risks named:** M itself read -5.1 on the left + back guard, so a child of M without the dose may fail it again (motion, coach: about 50 % pass). Cap 8 removes shots 8+ from training, which K3 catches (experiment design).

**Estimates:** P(5+) 0.75-0.79 from this run; target from this run 5-10 %; within 3-6 runs 15-35 %. Motion: 0.80 likely needs the human-footwork reference route.

**Decision:** D-240.

## Round 101 (2026-11-07): D-240 CONFIRM-FAIL on the left + back guard

Brief: results/footwork-round101-brief.md.

**Correction check (all five):**
- D-240 ran as registered; CONFIRM-FAIL stands. No third read of N and no pooling after the fact.
- **The crossing is noise, the deficit is real.** -5.2 +/- 1.3 against a -5 line; pooled over both seed sets N is about -4.4 (SE 0.9), so N sits on the line and passes gate plus CONFIRM only about 45 % of the time. Left alone is -5.8 at the gate and -6.6 at CONFIRM, below C on all 8 seeds; back is level.
- **The panel's error (architecture, experiment design):** round 100 knew M read -5.1 on this guard and added no lever for left; its "about 50 %" risk was for one read, and two were required.
- **K3 on the fresh seeds read +0.0088** (line +0.005), reported only; the brief left it out. From D-241, H0, FEEDER and K3-KEPT gate in CONFIRM too (a tightening).
- **Left misses are not speed-limited (motion, coach, RL):** they end about 0.85 m from the ball at p90 1.6-1.8 m/s, against 2.1 m/s on left balls the robot hits.
- **Instrument finding (architecture, verified by the agent):** the direction read (scripts/diag/feeder_speed_envelope.py) runs pair mode with feed_anchor "start" and no drill reset. Left fell exactly when drill-reset training began (C 0.407 -> R 0.364). On the set-start read N beats C on reach_backhand (0.81 / 0.74) and cross_backhand (0.64 / 0.52). RL: N's left losses are on wide_forehand, easy_forehand and topspin, not the backhand families.

**First votes:** (i) 5 of 5, parent N, cap 8 kept. Lever: backhand-family feed weights (motion x4, coach x2, experiment design x3) against the drill reset on half the pair courts (RL, architecture).

**Facts check (the agent, before the tally):** the three feed-weight voters were sent RL's and architecture's findings, and told that lc102.sh's training override already holds those weights at 1.0 and that no training-log counter of issued families exists. All three switched to the half-court drill reset.

**Decision (5 of 5):** the set start on half the live pair courts (odd court index, D-217's split), cap 8 kept, parent N. Lines in experiment design's form: smoke checks each half's dose; kill at +240 with KILL-LOST-OPEN, KILL-UNSTABLE, config, KILL-NO-FALLS and KILL-DIR (left contact); gate adds N-KEPT; a new CONFIRM block.

**Rejected (ii) (all five):** reads only; left is not speed- or effort-limited.

**Estimates:** guard pass about 50 %; P(5+) 0.76-0.79 from this run; target from this run under 5-10 %; within 3-6 runs 15-35 %.

**Decision:** D-241.

## Round 102 (2026-11-07): D-241 NO-CANDIDATE on K3-KEPT alone

Brief: results/footwork-round102-brief.md.

**Correction check (all five):**
- D-241 ran as registered; NO-CANDIDATE stands. The summary's "N" labels are a template slip (the arms are right).
- **The K3 fail is real:** 181 of 4,275 (0.0423, SE 0.0031) against C's 113 of 4,207: +1.54 points, about 3.9 SE; every child seed is above the line.
- **The panel's error (coach, experiment design):** round 101 knew K3 read +0.0041 at the gate and +0.0088 on fresh seeds and added no lever for it.
- **The brief's premise is only partly right (motion, RL, architecture, experiment design):** against N most of the extra late endings are at shots 3-4 (inside the cap's practised range), not 8+; D-239's N' had no cap and still raised K3. RL reads it as fine-tuning drift down the continuation chain (K3 0.0243 -> 0.0276 -> 0.0310 -> 0.0394 / 0.0423). Motion: the ready share fell 0.77 (M) -> 0.57 (N) -> 0.40 (child) as the robot hurries back to its spot. Training-log hazards at shots 3-7 are flat, so only a read catches K3 (architecture).

**Votes:**

| member | vote |
|---|---|
| coach | cap 8 on the set-start half only, parent the child |
| motion | cap 8 on the set-start half only, parent the child |
| architecture | cap 8 on the set-start half only, parent N (a sibling for clean attribution), plus a KILL-LATE read |
| experiment design | pair_rally_cap 16 on all courts, parent the child |
| RL | (iii) no training: read the child's model_35840 |

**Decision:** the lever by majority (3 of 5): pair_rally_cap 8 on the set-start half only. The parent by majority (3 of 5): the child, model_36194. Lines in experiment design's form; architecture's KILL-LATE had one vote and is not added.

**Estimates:** K3 pass about 40-50 %; P(5+) 0.77-0.80 from this run; target from this run about 5-10 %; within 3-6 runs 15-35 %. Motion: h2 (0.039) has not moved across M, N and the child and now binds; the human-footwork route is probably still needed.

**Decision:** D-242.

## Round 103 (2026-11-07): D-242 SMOKE-FAIL on the cap-split line

Brief: results/footwork-round103-brief.md.

**Correction check (all who reported):**
- SMOKE-FAIL is right as coded: 1,885 feeder balls of 12,122 (0.15550) against a band of 0.124 +/- 25 % (top 0.155); the miss is 0.0005, about 0.15 binomial SE. Seed 247 is spent.
- The cap mask works: the reset half's longest rally was 8; 63 free-half rallies ended at 9-15 and 18.3 % passed 8.
- **The agent's error, unchecked by the panel:** the prediction assumed the free half would average about 12 balls per rally once uncapped; D-241's own log already showed the free half's (1-h0)(1-h1) at 0.59. It averaged 5.74 (reset half 5.43). The same fault as D-237's smoke.
- **What the free half does (motion, RL, coach):** h1 0.41 means robots that start where the last rally ended return the feeder ball but cannot recover for ball two; 58 % of free-half rallies end by shot 1. Rallies past 8 still add about 20 % of pair-court shots past shot 8. The free half practises recovery from bad positions.

**Votes:** (a) re-run D-242 unchanged with the share re-predicted: coach, motion, RL (3). (b) pair_rally_cap 16 on all courts, reset-only off: experiment design (the free half's late practice starts from collapsed states, not the set start K3 reads). Architecture had not reported when the decision was recorded.

**Experiment design's conditions for a re-prediction (adopted):** a D-entry naming the changed premise; the band stays +/- 25 %; the new prediction recorded before the run; a fresh smoke seed, never seed 247.

**Decision:** D-243.

**Round 103 addendum (architecture, received after the decision was recorded):** (b), pair_rally_cap 16 on all courts. The smoke shows (a) cutting free-half practice where K3 fails: free-half (1-h0)(1-h1) fell from 0.60 at the end of D-241 to 0.42, and the share of free-half rallies reaching shot 3 from 0.54 to 0.42; a few very long rallies (87 past 15 shots) use up the extra balls. Final tally (a) 3, (b) 2; D-243 stands. Architecture's KILL-LATE line (a K3 read at +240 against P on dev 4220421) had one vote and is not added.

## Round 104 (2026-11-08): D-243 CONFIRMED; the next run toward the target

Brief: results/footwork-round104-brief.md.

**Correction check (all five):**
- D-243 ran as registered; CONFIRMED stands (gate 4,134 of 5,328, 0.7759; CONFIRM 4,132 of 5,324, 0.7761; sides 0.997 / 0.996).
- **The agent's h0 arithmetic was wrong (all five).** A pooled four-seed read has about 5,300 rallies, so the Wilson bar does not bind: at P(5+) 0.80 its low is about 0.789. With Q's h1-h4, the target needs h0 <= about 0.089 on the gate seeds (0.091 on the CONFIRM hazards), not 0.085 / 0.075. P's h0 (0.091) with Q's late hazards would sit at about 0.80.
- **The cause of Q's h0 rise is not shown (experiment design):** one training seed per arm; training-seed variance on this line has never been measured. Motion: Q's extra feeder misses sit in reach_deep (contact 0.48 -> 0.37), cross_backhand, backspin and fast; reach_deep, cross_backhand and reach_backhand hold 424 of Q's 616 feeder misses (coach, motion). Reset-half training h0 stays at 0.134 through Q's run.
- **Labels (architecture, RL):** the lc105 summary prints "N" and a "D-242:" header for the child; fixed in lc106.

**Votes:**

| member | lever |
|---|---|
| RL | pair_rally_cap 8 -> 5 on the set-start half (no new code) |
| experiment design | pair_rally_cap 8 -> 5 on the set-start half (no new code) |
| coach | feed-mix weights x3 on reach-deep, cross-backhand, reach-backhand (no new code) |
| motion | the same families x2 (no new code) |
| architecture | free-half cap 16, set-start cap 8 kept (about 10 lines) |

Human-footwork reference: later (all five); motion asks for a CPU-only count of GVHMR segments with >= 2 m backward travel or a left crossover, and for the reference only if reach_deep stays below 0.5 under a feed dose.

**Decision (no majority; the tie rule):** both two-vote options need no new code and have one moving part, so experiment design's position decides: pair_rally_cap 5 on the set-start half, parent Q, lines in experiment design's form. Experiment design also registers the target read (below).

**Estimates:** P(5+) 0.77-0.80 from this run; target from this run about 10-35 % (RL 35 %); within 3-6 runs 20-40 %.

**Decision:** D-244.

## Round 105 (2026-11-08): D-244 NO-CANDIDATE on K3-KEPT and OPEN

Brief: results/footwork-round105-brief.md.

**Correction check (all five):**
- D-244 ran as registered; NO-CANDIDATE stands. Both lines were right and are not loosened. OPEN against Q + 0.02 (0.8372) is looser than the target itself, which needs about 0.845 at the child's h2-h4 (experiment design, RL, architecture). The child's +0.0165 is about 2.3 SE above Q, but about 0.5 SE short of +0.02. Experiment design: no predicted effect was registered and the line had about 50 % power.
- **The K3 cost is real (about 4.6 SE on shots past 8):** at level shot exposure (383,698 vs 375,107 hand-offs), endings past 8 rose 33 -> 83, 68 of them past shot 30 and 35 at the 64-shot clamp; the per-shot hazard in long rallies about doubled to quadrupled. All four seeds read 0.033-0.037. Redefining K3 to shots 3-7 now would be post-hoc loosening (rejected).
- **The body signal (motion, coach):** receiver within 0.1 m of its spot at the partner's hand-off 12.1 % -> 3.7 %; recovery median 0.225 -> 0.275 m; paddle speed 5.55 -> 5.32 m/s; BODY_CONTACT endings 65 -> 98; left contact 0.328, the lowest in the chain.
- **When it happened (architecture, RL):** the reset-half training opening stops improving by +61-120; the +240 KILL-LATE read had about Q's count of late endings, so the cost came after +240. The cap route is used up (RL withdraws its round-104 vote; architecture withdraws its free-half cap-16 vote).

**Votes:** all five vote the weak-family feed dose (reach_deep, cross_backhand, reach_backhand), which held 424 of Q's 616 feeder misses and leaves rally lengths alone. Dose: x2 (RL, experiment design, motion, architecture), x3 (coach). Base recipe: Q's cap 8 (RL, experiment design, motion, coach), D-244's cap 5 with 248 iterations (architecture). Parent Q (all five).

**Decision (majorities):** parent Q, Q's cap-8 recipe, feed-mix weights 2.0 on the three families; lines in experiment design's form, with D244-KEPT added; the target read carried over on the unread block 4220425-4220433.

**Estimates:** gate pass 35-45 % (motion); target from this run 10-25 %; within 3-6 runs 20-45 %. Motion: if reach_deep stays below 0.5 under this dose, the human-footwork (backpedal) reference comes next.

**Decision:** D-245.

## Round 106 (2026-11-08): D-245 SMOKE-FAIL on the cap-split share

Brief: results/footwork-round106-brief.md.

**Correction check:**
- SMOKE-FAIL is right as coded: 0.1642 on 12,030 balls against a band top of 0.1633 (about 0.3-0.7 binomial SE). The line stands and is not loosened. Seed 253 is spent.
- **The prediction basis was wrong (the agent's error, shared by the panel):** 0.1306 came from Q's training log (12,288 envs, a late window); a smoke (1,024 envs, +20-140) reads higher. This was on record: D-244's smoke from Q read 0.187 against 0.160 (+17 %), and D-243's smoke 0.1497 against Q's log 0.1297. The dose adds to it (harder feeds end more rallies early). Same-recipe smokes on different seeds agree to about 4 % (D-242 0.1555, D-243 0.1497).
- **Brief correction (experiment design):** D-243's smoke started from P, not Q; the earlier smoke from Q was D-244's.
- **Latent driver bug (architecture):** lc107.sh's +240 config check read `... is not None is not None`, which is always False, so a healthy run would have been killed by KILL-CONFIG at +240. Fixed in lc108.sh (all three weights checked) and tested on D-245's smoke params (True) and Q's (False). lc107.sh is left as committed (historical).
- **Motion flag (reported):** the smoke's launcher-court falls rose from 40 to 103 per about 2,400 episodes and off-court falls from 0.91 to 1.18 per 1,000 env-s against D-243's smoke; KILL-NO-FALLS covers it; launcher-court falls per episode are reported at +240.

**Votes:** (a) re-run D-245 unchanged on a fresh smoke seed with the share re-predicted from D-245's own smoke read (0.1642 +/- 25 %): coach, experiment design, architecture, motion (4 of 5; RL had not reported when recorded). Standing rule from now (experiment design): a smoke's share prediction comes from a smoke read of the same parent and recipe.

**Decision:** D-246.

**Round 106 addendum (RL, received after the decision was recorded):** (a), the same form; final tally 5 of 5. RL's recorded risk: under the dose the smoke's reset-half (1-h0)(1-h1) fell to 0.652 from Q's smoke 0.695; if that gap holds in training, KILL-LOST-OPEN (>= 0.7156) can fire because the ball mix is harder rather than because the policy forgot. The line is unchanged; such a kill would be ambiguous and goes to the next round.

## Round 107 (2026-11-08): D-246 KILLED by KILL-LOST-OPEN on the harder mix

Brief: results/footwork-round107-brief.md.

**Correction check (all five):**
- The KILL is right as coded (0.6869 vs 0.7156 on 5,360 rallies) and stands; no resume or rescue of model_37040.
- **The line was wrong for this lever; the panel's error (RL flagged it in round 106; nobody proposed a fix).** It compared training on Q's mix with training on a harder mix. Mix arithmetic from Q's reads (the three families miss about 45 % of feeder balls, the rest about 4.4 %) predicts training h0 about 0.17 before any learning; the run read 0.166. The gap was flat from the first window (0.055 -> 0.049) and each run rose by about the same (Q +0.042, D-246 +0.048): no sign of forgetting, and no sign of extra learning on the dosed families either (RL).
- **Standing rule (experiment design):** a lever that changes the training input gets its "lost" line on the standard read mix, against the reference read on the same seed.
- **Counter bug (architecture, verified):** fam_feeder counted every refeed including hand-offs (fire |= recv runs first), so D-245/D-246's "three-family share" (0.30) is not a feeder-ball count. Fixed (fire & ~recv); logging only, the dose itself was applied as configured.
- **Motion:** reach_deep (legal 0.25-0.27) looks like a backward-speed limit (body about 2 m/s; human depth p90 1.9, p99 4.0 m/s); if it stays flat, the next dose is cross_backhand and reach_backhand only.

**Votes:** (a) a diagnostic read of model_37040 against Q on the read mix: 5 of 5. Seeds: fresh dev 4220438 for both checkpoints' pairs reads, the child's direction read on 4220435 against Q's stage-0 read (motion, coach, architecture; RL 4220438-39; experiment design: Q's gate seeds for power). Rule: re-run the dose (b) if the child's (1-h0)(1-h1) >= Q's on the same seed - 0.02 (motion, coach, architecture) and the three families' feeder legal is not below Q's (RL, architecture and experiment design each asked for a family condition; the common floor is adopted); otherwise (c).

**Decision:** D-247.

## Round 108 (2026-11-08): the user's direction, train with the pro footwork videos; D-248 NO-CANDIDATE

Brief: results/footwork-round108-brief.md.

**Correction check (all five):** D-248's NO-CANDIDATE is right as coded (OPEN +0.0086 against +0.02); the line stays. **Brief correction (RL, motion, experiment design, architecture):** 41 of the 208 moves are tracking artefacts (duration under 0.5 s or mean speed over 2.9-3 m/s, some up to 6 m/s); 167 remain (left 51, right 52, back 23, forward 41). On the 167, median mean speeds are about 1.0-1.2 m/s, not 1.2-1.6 (motion: left 2.24 m in 2.00 s, right 2.17 m in 1.67 s, back 2.91 m in 3.10 s, forward 4.69 m in 2.93 s).

**Votes:** (a) the pro-move drill, parent Q, Q's cap-8 recipe with every feed weight back to 1.0 (no dose): 5 of 5. (b) rejected by all (no retargeting, noisy tracks, a new motion prior resets rally skill).

**Form (majorities; ties by least new code, then experiment design):**
- One change: in move episodes, each new spot = pelvis + one of the 167 pro displacements drawn uniformly on the drill's own stream; robot (dx, dy) = (pro dy, -pro dx) (toward the net +x, the player's left +y), with a coded sign test (5 of 5). Distances unscaled (5 of 5). Table frozen and sha256-pinned (picklebot_mj/pro_moves_v1.json; source ppa_moves.json b69b3398).
- Time limit: MoveDrill's untimed limit kept (coach, experiment design, architecture); RL (1.5 s + pro duration) and motion (Froude-scaled pro time) recorded, not adopted.
- Box: MoveDrill's SPOT_BOX, flip and shrink kept (RL, motion, experiment design); the flipped / clipped shares are reported. Coach's 1.4 m extension behind the baseline and architecture's depth warning recorded (the 4 m deep box clips many forward moves and flips back moves near the baseline).
- Smoke: the standing rule (same parent and recipe) needs a basis smoke of Q's unchanged recipe (seed 259) to record the share predictions; the child smoke (seed 260) reads D-248's lines against it (+/- 25 %). Sector line: proposals split (CPU replay +/- 25 %: coach, architecture; back share >= half the table's: experiment design; within 3 SE: motion); tie -> least new code: experiment design's back-share line (issued back share after flips >= 0.069, n >= 200).
- Kill at +240: D-248's lines on fresh dev seeds (4 of 5): NO-FALLS 4220439, DIR 4220440, OPEN-DEV + LATE 4220441, Q read at stage 0 on 4220440 and 4220441. Extra kill lines proposed singly (RL back contact >= Q - 0.02; experiment design left + back >= Q - 0.01; motion KILL-NO-DRILL) -> tie -> none; left + back contact vs Q is reported at the DIR read.
- Gate: D-248's lines unchanged; R3 on 4220442. CONFIRM 4220425-4220433, the registered target read, one look. Training seed 258.
- Architecture's fixes: the driver's summary header now names D-249; the nan "legal(d > 1.2)" line prints "not read (n 0)".

**Estimates:** gate pass 15-30 % (RL about 15 % for OPEN, motion 20-30 %); target from this run 3-10 %. What it can show: whether pro-timed spot practice carries into left / back contact on feeder balls and h0. What it cannot: reading the ball, split-step or crossover technique, speed above about 2 m/s (the user's 3-4 m/s needs body or controller work), or what full-body imitation would do.

**Decision:** D-249.

**D-249 result (2026-11-09): NO-CANDIDATE (results/lc110-summary.txt).** CONFIRM (the registered target read) was not run; 4220425-4220433 stay unread.

- Basis smoke of Q's recipe (seed 259): feeder share 0.1498, three-family share 0.183. Child smoke (seed 260): all 9 lines ok (feeder share 0.1546; pro-move back share 0.180 after flips, n 5,236; forward / left / back / right 0.201 / 0.309 / 0.180 / 0.311 against the table's 0.246 / 0.305 / 0.138 / 0.311; flipped 0.320, clipped 0.488, arrived 0.924).
- Kill at +240, all CONTINUE: KILL-UNSTABLE 0.946; config ok; KILL-NO-FALLS 0.0184 (4220439); KILL-DIR left 0.3716 vs Q 0.3504 (4220440; left + back +1.3 reported); KILL-OPEN-DEV 0.7898 vs Q 0.8018 (4220441); KILL-LATE 0.0303. Reported: training-log reset-half opening 0.7415 vs Q's 0.7356.
- Gate (rally-d1s3pro1 model_37392): GAIN2 +18.92 (lower bound +17.32) pass; guards pass (left + back 0.4178 vs parent 0.4557, -3.8); H0 0.128, FEEDER 0.8737, K3-KEPT 0.0213 pass; R3 0.0260 pass; M-KEPT and N-KEPT pass. **OPEN 0.7956 vs Q 0.8172 (-0.0216; needed +0.02) FAIL; P-KEPT, Q-KEPT (P(5+) 0.7537 vs Q 0.7759) and D244-KEPT FAIL.**
- Reported: hazards h0-h4 0.128 / 0.088 / 0.039 / 0.012 / 0.002 (Q 0.117 / 0.075 / 0.036 / 0.012 / 0.003); direction contact forward 0.884, left 0.332, back 0.647, right 0.770; ready 0.451, recovery 0.225 m.

Plain reading: the pro-move drill made the opening worse (h0 +1.1, h1 +1.3 points against Q) and P(5+) fell 2.2 points; left contact on feeder balls rose at +240 on one seed but not at the gate. Since D-243 every child reads P(5+) 0.754-0.788.

## Round 109 (2026-11-09): D-249 (the pro-move drill) NO-CANDIDATE

Brief: results/footwork-round109-brief.md.

**Correction check (all five):** NO-CANDIDATE stands; lines coded and read correctly; no code or driver bug (architecture). Framing corrections: D-249 tested shortened pro directions, not pro moves (49 % of spots clipped, 32 % flipped; back over-issued, forward under-issued), and never pro pace (MoveDrill's untimed limit and capped command; motion, architecture). The opening eroded after the +240 read (h0 even with Q at +240), a slow slide the -0.02 kill line cannot catch (RL, architecture). The +240 left gain was about 1 SE on 549 balls and gone at the gate (coach, RL). **Brief errors (experiment design, motion):** "seven children read 0.754-0.788" is wrong (three were gated: D-244 0.788, D-248 0.785, D-249 0.754); the direction and left + back comparisons were against M and the original parent, not Q (against Q's gate read: left 0.332 vs 0.346, left + back 0.4178 vs 0.4249, -0.7). lc110.sh's stage-0 comment names seed 4220435; the code uses 4220440.

**Votes:** (b) coach, experiment design, architecture (3 of 5); (c) a lower leg / waist damping ratio, read first with no training: motion, RL. Form within (b): the lever pair_rally_cap 5 on the set-start half (experiment design, architecture) against coach's drop of reach_deep from the dose; parent Q (coach, architecture) against D-248's checkpoint (experiment design). Result: Q on D-248's recipe with cap 5 on the set-start half (architecture's form). D248-KEPT (experiment design) not added. The damping premise read (registered round 92, never run) is recorded as the next candidate if (b) fails (motion, RL; architecture: could run in a GPU gap, reported only).

**Estimates:** gate pass 25-35 % (architecture); target from this run 5-15 %; within 3-6 runs 15-30 %. The video route so far: pro directions used as move-drill spots raised the ready share (0.315 -> 0.451) but not contact, and cost 2.2 points of P(5+); it has not tested pro pace, the split step or the GVHMR body tracks.

**Decision:** D-250.

**The user's question (2026-11-09) and the agility read (results/agility249-summary.txt; reads only).** The user: the videos were meant to promote agility, not to move P(5+) at once; was movement measured? It was not: D-249's lines read rally outcomes and feeder contact. D-250 was paused before any of its seeds were read (the user chose the read first), and the D-185 bridge drill (Measure60-RallyLamR2: move-only, spots 3-5 m, deterministic) read Q, D-249's model and D-248's model (the same 600 iterations without the drill) on dev 4220447:

| | first step to 1.5 m, median (all / left-back) | sustained speed p50 (all / left-back) | peak, left-back | arrival | falls per 1,000 env-s |
|---|---|---|---|---|---|
| Q | 1.36 / 1.34 s | 1.69 / 1.69 m/s | 2.07 m/s | 0.986 | 3.55 |
| D-249 (pro-move drill) | 1.36 / 1.34 s | 1.70 / 1.68 m/s | 2.04 m/s | 0.987 | 2.94 |
| D-248 (no drill change) | 1.36 / 1.34 s | 1.69 / 1.67 m/s | 2.04 m/s | 0.989 | 2.90 |

Every direction's first-step median is identical across the three (0.05 s bins) and sustained speeds differ by 0.03 m/s or less. Plain reading: the pro-move drill as built (directions only, mostly shortened, untimed) did not change movement; the small fall drop is shared with D-248, so it comes from the extra training, not the drill.

## Round 110 (2026-11-09): freeze the user's call-and-set footwork test (D-251)

Brief: results/footwork-round110-brief.md.

**Correction check (all five):** the D-250 stop is recorded correctly; dev 4220446 was never read and is retired (RL, experiment design). D-251's example times give one formula, 0.5 s + d / 2.5 m/s (2.5 = 2.9 x 0.85; all five). Q needs 1.36 s for its first 1.5 m, so Q's headline baseline will be near 0 %: a reported pace ladder is needed for a climbable signal (all five); the headline is never loosened. Q cannot see the called side or the time left from a spot: the call is shown as a ball (RL, experiment design, architecture), the ghost ball of ShadowSwing (experiment design, architecture). "Split step" means SET by its outcome, no hop required (motion).

**Frozen (majority, ties by least new code, then experiment design):** see results/footwork-target.md. Distance 1.0-3.0 m (coach, motion, architecture); four call types at 25 % (RL, motion, experiment design); chains of 6 (coach, experiment design); one third early at the previous arrival (tie -> experiment design), the rest 1.5 s later (motion, experiment design, architecture); SET at arrival with speed < 0.3 m/s over 0.1 s, both feet down, tilt < 20 deg (speed and feet all five; tilt coach, motion, experiment design; window by tie -> experiment design); READY = MoveDrill's ready_mask + 0.10 m to the called side (height by tie -> experiment design; side four of five); REACH within 0.8 m horizontally on the called side (tie -> experiment design); >= 4,000 reps / 600 chains (experiment design); pass >= 0.80, Wilson low >= 0.78 (four of five; experiment design's chain bootstrap not adopted), every call type >= 0.70 (RL, experiment design); feeder-ball legal within 5 points of Q for the target read (tie -> experiment design); dev block 4220451-4220499, target block 4220500-4220509 unread (experiment design). The ladder (1.5 / 2.0 / 2.5 m/s) is computed from each rep's first all-hold time, reported only (tie -> experiment design; motion's per-rep drawn paces not adopted). START is reported only.

**Build (majority):** an evaluation-first CallSetDrill on DeadlineMoveDrill (RL, motion, experiment design) with the call sent as ShadowSwing's ghost ball (experiment design, architecture); unit tests: the deadline formula, call shares and the early share, the side sign (forehand / backhand mirror), SET / READY / REACH on scripted states, falls in the count, seed determinism. Baseline: Q zero-shot on dev 4220451 with a prediction written before the read (experiment design). Architecture's size estimate: about 200 lines + 120 of tests + 40 of eval script.

**First lever:** damping first if the running damping read (damp249) shows the first step at least 0.05 s faster with falls no higher than Q's (motion; coach at 0.10 s; architecture unconditional); otherwise a fine-tune of Q with the call drill in training (RL, experiment design; coach: a base retrain with side and time inputs).

**Decision:** D-252.

**Damping premise read (2026-11-09, scripts/diag/damp249.sh, results/damp249-summary.txt; reads only, zero-shot).** Q with the leg, waist and ankle damping halved (mjlab G1 damping ratio 2.0 -> 1.0; stiffness, effort and action scale unchanged):

| | standard | damping x0.5 |
|---|---|---|
| first step to 1.5 m, all / left-back (Measure60, dev 4220447) | 1.36 / 1.34 s | 1.38 / 1.36 s |
| sustained speed p50, all | 1.69 m/s | 1.66 m/s |
| untimed arrival | 0.986 | 0.952 |
| falls per 1,000 env-s | 3.55 | 11.05 |
| set-start pairs P(5+) (dev 4220449) | 0.7623 | 0.1555 (falls 5,061 in 2,048 envs) |

Plain reading: zero-shot, a looser body is not quicker; the frozen movement skill was learned with the heavier damping and loses balance without it. This does not test a skill retrained on the looser body (a later lever). By D-252's rule (damping first only if >= 0.05 s faster with no more falls), the first lever is the call drill in Q's training.

## Round 111 (2026-11-09): call-and-set baseline (Q = 0 %) and the first lever's form

Brief: results/footwork-round111-brief.md.

**Correction check:** no mis-build in the headline (all five). Architecture found a real bug: the ghost ball could still meet the real paddle (the ball simulation's paddle impulse is applied even on a closed rally); fixed before training by moving the paddle out of the ball simulation in call episodes (as ShadowSwing does). The pace ladder is cut at T when the next call is early (about 28 % of calls); the deciding ladder counts normal calls only (experiment design, architecture). The 6x falls come from the drill (chained sideways calls and early reversals: early wide calls about 5.7 % per call, deep 1.3 %; about 1,000 of 2,615 falls fall between calls), not from a bug (RL, motion, coach, architecture); a falls-between-calls counter is added. RL's correction: at 1.5 m/s the ladder is blocked by READY (0.008; paddle 0.64 m high), not by speed. A per-step host sync is removed for training (RL, architecture). The agent found and fixed one more: a call left pending when an episode switched type could be booked twice.

**Votes on the form:** parent Q on Q's recipe, the call drill replacing the move episodes on the drill courts at Q's move share (experiment design, motion, RL, architecture; coach: half the drill courts); the speed reward toward the spot unchanged with its 2.5 m/s cap (four of five; motion 2.0 with a steeper ramp); one event at T with partial credit and a pass bonus (coach, motion, architecture; forms differ) -> tie by least new code: architecture's (SET + READY + REACH + pass) / 4 at move_arrival's weight (experiment design: pass only; RL: REACH x (1 + SET + READY) / 3; motion: also a ready carry in the last 0.3 s, not adopted); fixed 2.5 m/s pace (four of five; RL: U(1.5, 2.5) in training); 600 iterations (four of five; RL 1,200); seeds training 263, smoke 264. The agent keeps MoveDrill's net-facing teacher heading (FootworkDrill's heading-free command would be a second change).
**Lines:** kill at about +180 (experiment design, coach, motion): call-and-set falls <= Q's on the same seed (experiment design, motion, RL), the 1.5 m/s ladder on normal calls >= 0.02 (motion, coach, RL), feeder-ball legal >= Q's - 0.05 (all five). The training-log KILL-UNSTABLE line (3.14, set for move episodes) is reported only under round 107's standing rule (a lever that changes the training input is judged on the read mix against Q on the same seed). Gate (experiment design's form): the headline gain over Q when either arm reads >= 0.05, else the 1.5 m/s ladder gain on normal calls; KEEP if its lower bound > 0, FLAT if its upper bound < +0.02; guards falls <= Q's and feeder legal >= Q's - 0.05.

**Estimates:** 1.5 m/s ladder 0.03-0.35; headline at most 0.02-0.08. All five: a residual on the frozen base can learn the ready carry and the stop, not a faster start; if flat on the ladder or if the headline stays near 0, the next lever is a base retrain on the call drill.

**Decision:** D-253.
