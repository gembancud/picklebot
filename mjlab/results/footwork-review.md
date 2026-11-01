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
