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
