# Stage 5H: the Stage 5F executor with a keep-alive landing reward (D-129)

The plan and its budget are in `stage5h-review.md` (round 17): at most 4 runs; pair-mode P(4+) is the primary readout.

| Run | Name | One change | Parent | Endpoint | Result |
|---|---|---|---|---|---|
| 1 | s5h-01-keepalive | Run 4's recipe (court mix 0.4, seed 73, 12,288 envs) with the pace term replaced by keep_alive_landing (`Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-G1`) | s5d-01-rally/model_1800 | iteration 2600, or the last checkpoint before the 7,000 s cap | **Not a kill.** Endpoint model_2599: every stage rule passes (court main 77.6 %, falls 6.7 % per episode), drill v2 0.846. R2 (development seeds) 10.0 % [9.5, 10.4]; R4 P(4+) 0.0004. See below. |

### Run 1 early check (model_2100; seeds 4217000-4217002, parent read on the same seeds): **pass**

| Item | Parent | Run 1 | Kill line |
|---|---|---|---|
| Drill v2 p (0/0) | 0.724 | 0.747 (+2.3) | more than 5 points below |
| Court main | 0.781 | 0.771 [0.753, 0.788] (-1.0) | more than 5 points below |
| Court falls per episode | | 5.8 % | > 7.4 % |
| Move arrival, minimum | | 99.1 % | < 90 % |
| Keep-alive box share of legal landings | 7.3 % [6.1, 8.6] (123/1,694) | **9.0 % [7.7, 10.5]** (148/1,640) | not above the parent |

- **Report only:** mean flight 0.97 -> 1.02 s; ball out 10.72 -> 10.72 m/s.
- **The box share passes as a point estimate,** but the intervals overlap.

### Run 1 at its endpoint (model_2599; battery seeds 4217010-4217025; R2 on 4217030 / 4217031, R4 on 4217032)

| Item | Run 1 | Run 4 (pace term) | Parent s5d-01/1800 | Bar |
|---|---|---|---|---|
| Drill v2 p (0/0) | **0.846** [0.843, 0.850] | 0.843 | 0.753 (D-113 read) | R1 >= 0.80 |
| Groups: neutral / moderate / extreme (Wilson low) | 0.890 / 0.782 / 0.724 | 0.890 / 0.772 / 0.716 | | |
| Court main | **77.6 %** | 75.9 % | | stage rule >= 76.8 % (pass) |
| Court falls per episode | 6.7 % | 6.4 % | | stage <= 7.4 % (pass); R3 <= 4.0 % (**fail**) |
| Move arrival, minimum | 99.5 % | 99.2 % | | >= 90 % |
| R2 own-ball legal (development seeds) | **10.0 %** [9.5, 10.4] (17,918 balls) | 8.2 % (readiness seeds) | 6.9 % | >= 70 % |
| R2 falls per shot | 5.5 % | | | report |
| R4 pairs: P(4+ consecutive legal shots) | 0.0004 (38,250 rallies) | 0.0002 | 0.000 | >= 25 % (video bar 10 %) |
| R4 own-ball legal per side, A / B | 6.1 % / 6.5 % | | | sides within 3 points (pass) |

**Shots, from the R2 recording (the rally protocol):**

| Measure | Run 1 | Parent |
|---|---|---|
| Legal returns | 84 % | |
| Ball out | 11.2 m/s | 10.7 m/s at the early check |
| Mean landing x | 4.46 m | |
| Net clearance | 0.84 m | |
| Mean flight | 1.08 s | 0.97 s |
| Landings in the keep-alive box | **10.7 %** | 7.3 % |

**Findings:**
- **Run 1 is the best Stage 5 policy on every readiness item but R3,** and R1 is met: drill v2 >= 0.80 and every stage rule passes.
- **The keep-alive reward moved the shots only a little.** Flight +0.1 s, box share +3 points; ball speed unchanged (11 m/s).
- **R2 rose 8.2 -> 10.0 %, but the gap is unchanged:** about 56 % per shot is needed for the video, and P(4+) is 0.04 %.
- **Stage 5H:** 1 of 4 runs used, no kill. The panel picks run 2.

| 2 | s5h-02-own | Run 1's task with 40 % of feeds one of run 1's own mirrored legal returns (court feeds 0.4 of the rest, so 24 %; `...-KeepAlive-Own-G1`) | s5h-01-keepalive/model_2599 | iteration 3399 | **Killed at the early check: court main -6.0 points.** Own-ball legal rose 10.0 -> 16.6 %. See below. |

### Run 2 early check (model_2900; seeds 4217100-4217104, parent model_2599 read on the same seeds): **KILL** (1 of 5 lines)

| Item | Parent (run 1's endpoint) | Run 2 at 37 % | Kill line |
|---|---|---|---|
| Drill v2 p (0/0) | 0.815 | 0.786 (-3.0) | more than 5 points below (pass) |
| Court main | 0.789 | **0.729** [0.710, 0.748] (-6.0) | more than 5 points below (**kill**) |
| Court falls per episode | | **4.4 %** | > 7.4 % (pass) |
| Move arrival, minimum | | 98.6 % | < 90 % (pass) |
| Own-ball legal (R2 protocol, 512 envs, 6,206 balls) | 10.0 % [9.5, 10.4] (run 1's endpoint R2, 1,024 envs) | **16.6 % [15.6, 17.5]** | <= 10.4 % (pass) |

- **Report only:** keep-alive box share 10.5 -> 11.0 %; flight 1.03 -> 1.08 s; ball out 10.6 -> 10.3 m/s.
- **Training on its own returns worked on the target.** Own-ball legal went from 10.0 to 16.6 % in 300 iterations (intervals far apart), and falls dropped toward R3 (4.4 % per episode).
- **The cost was court skill:** court main fell 6.0 points. The replay draw comes first, so court feeds dropped from 40 % to 24 % of the mix (round 18's choice).
- **The kill counts.** Stage 5H: 2 of 4 runs used, 1 kill in a row. The D-130 stop rule (R2 < 20 % at run 2's endpoint) has no endpoint to read; the panel meets.

| 3 | s5h-03-own-c40 | Run 2 with the court share restored: 40 % replay / 40 % court / 20 % drill v2 (`...-Own-Court40-G1`) | s5h-01-keepalive/model_2599 | iteration 3399 | **Killed by the stage rules at the endpoint: court main 75.1 % (< 76.8 %).** R2 (development seeds) **29.8 % [29.1, 30.6]**; R4 P(4+) 0.0033. See below. |

### Run 3 early check (model_2900; seeds 4217200-4217204, parent read on the same seeds): **pass**

| Item | Parent | Run 3 at 37 % | Kill line |
|---|---|---|---|
| Drill v2 p (0/0) | 0.820 | 0.793 (-2.7) | more than 5 points below |
| Court main | 0.775 | 0.752 [0.733, 0.770] (-2.3) | more than 5 points below |
| Court falls per episode | | 6.6 % | > 7.4 % |
| Move arrival, minimum | | 99.1 % | < 90 % |
| Own-ball legal (R2 protocol, 512 envs, 6,247 balls) | 10.0 % [9.5, 10.4] | **17.9 % [16.9, 18.8]** | <= 10.4 % |

- **Report only:** box share 11.6 -> 11.4 %; flight 1.03 -> 1.07 s; ball out 10.6 -> 10.3 m/s.
- **Keeping the court share at 40 % removed run 2's court loss** (-6.0 -> -2.3), and own-ball legal is higher than run 2's (17.9 % against 16.6 %).
- **Falls are back at run 1's level** (6.6 %, against run 2's 4.4 %).

### Run 3 at its endpoint (model_3398; battery seeds 4217210-4217225; R2 on 4217230 / 4217231, R4 on 4217232)

| Item | Run 3 | Run 1 | Bar |
|---|---|---|---|
| Drill v2 p (0/0) | 0.836 | 0.846 | R1 >= 0.80 |
| Court main | **75.1 %** | 77.6 % | stage rule >= 76.8 % (**fail: killed by the stage rules**, as Stage 5F run 4 was) |
| Court falls per episode | 6.1 % | 6.7 % | stage <= 7.4 %; R3 <= 4.0 % (fail) |
| **R2 own-ball legal** | **29.8 % [29.1, 30.6]** (15,757 balls) | 10.0 % [9.5, 10.4] | >= 70 %; D-130 stop rule >= 20 % (**pass**) |
| R2 contact / falls per shot | 43.7 % / **0.8 %** | 25.4 % / 5.5 % | report |
| R4 pairs: P(4+) | **0.0033** (35,325 rallies) | 0.0004 | >= 25 % (video bar 10 %) |
| R4 own-ball legal per side, A / B | 11.8 % / 11.5 % | 6.1 % / 6.5 % | sides within 3 points (pass) |
| R4 mean rally length | 0.82 | 0.69 | report |

**Shots** (R2 recording): legal 82 %, ball out 10.9 m/s, landing x 4.61 m, flight 1.17 s, keep-alive box share 16.1 % (run 1: 10.7 %).

**Findings:**
- **Training on its own returns tripled R2** (10.0 -> 29.8 %), and falls on own balls almost vanished (5.5 -> 0.8 % per shot). It also made the shots easier: box share 10.7 -> 16.1 %, flight +0.09 s.
- **The cost is court main: 75.1 %,** 1.7 points under the stage line, so the stage rules kill the run.
- **In two-robot pairs, own-ball legal is only about 12 %, against 30 % on replays.** In a rally the receiver has just hit its own shot and is out of position. The replays start it from the rally protocol's start spot, so **positioning and recovery in a live rally** are now the gap. P(4+) rose 8x to 0.33 %, still far from 10 %.
- **Counters:** Stage 5H has used 3 of 4 runs, with 2 kills in a row (runs 2 and 3). The D-130 stop rule does not fire (R2 >= 20 %). The end-of-stage rule (P(4+) < 1 % ends the stage) applies after run 4.

| 4 | s5h-04-pairs | Run 1's task in pair mode: shared-policy self-play on mirrored env pairs, a feeder ball starts each rally, feeder court share 0.678 (`...-KeepAlive-Pairs-G1`) | s5h-01-keepalive/model_2599 | iteration 3399 | **Killed by the stage rules at the endpoint: court main 76.3 % (< 76.8 %).** R4 P(4+) **0.0065**, own-ball legal in pairs 12.7 %, falls **3.85 %** per episode (R3 met). See below. |

### Run 4 early check (model_2900; seeds 4217300-4217303, parent read on the same seeds): **pass**

| Item | Parent | Run 4 at 37 % | Kill line |
|---|---|---|---|
| Drill v2 p (0/0) | 0.822 | 0.792 (-3.0) | more than 5 points below |
| Court main | 0.765 | **0.768** [0.749, 0.786] (+0.4) | more than 5 points below |
| Court falls per episode | | **2.6 %** | > 7.4 % (R3 bar 4.0 %) |
| Move arrival, minimum | | 93.3 % | < 90 % |
| Own-ball legal per shot in pairs (1,024 envs, 60 s) | 5.9 % | **10.7 % [10.0, 11.4]** (7,285 shots) | <= 6.5 % |
| P(4+) in pairs | 0.000 | 0.0038 (8,899 rallies) | report |

- **Report only:** box share 9.8 -> 13.8 %; flight 1.04 -> 1.09 s; ball out 10.6 -> 10.2 m/s.
- **Self-play is the first change that raises own-ball legal in pairs while holding court main** (+0.4), and falls fell to 2.6 % per episode. Run 3's endpoint had 11.7 % own-ball in pairs, but with court main at 75.1 %.

### Run 4 at its endpoint (model_3398; battery seeds 4217310-4217325; R2 on 4217330 / 4217331, R4 on 4217332)

| Item | Run 4 (pair-mode self-play) | Run 3 (own-return replays) | Run 1 (keep-alive) | Bar |
|---|---|---|---|---|
| Drill v2 p (0/0) | 0.820 | 0.836 | 0.846 | R1 >= 0.80 |
| Court main | 76.3 % | 75.1 % | 77.6 % | stage rule >= 76.8 % (**fail by 0.5 points**) |
| Court falls per episode | **3.85 %** | 6.1 % | 6.7 % | R3 <= 4.0 % (**met, for the first time**) |
| R2 own-ball legal (replays) | 19.7 % [19.1, 20.3] | 29.8 % | 10.0 % | >= 70 % |
| **R4 P(4+) in pairs** | **0.0065** (34,422 rallies) | 0.0033 | 0.0004 | >= 25 % (video bar 10 %) |
| R4 own-ball legal per side, A / B | **12.8 % / 12.6 %** | 11.8 % / 11.5 % | 6.1 % / 6.5 % | sides within 3 points (pass) |
| R4 mean rally length | 0.88 | 0.82 | 0.69 | report |

**Shots** (R2 recording): ball out 10.8 m/s; landing x 4.57 m; flight 1.17 s; keep-alive box share 13.6 %.

**Stage 5H at its end:** 4 of 4 runs used; runs 2, 3 and 4 were killed (stage rules or the early check), 3 in a row.

**Findings:**
- **Self-play (run 4) is the best two-robot result in the project.** P(4+) is 16x run 1's and 2x run 3's. Falls met R3 for the first time, and court main held within 1.3 points of run 1.
- **The gap to the video bar is still about 15x** (0.65 % against 10 %). Per shot in pairs, legal is about 13 %; about 56 % is needed.
- **D-129's stop fires:** the stage ended with P(4+) under 1 %. Back to the user with the interim video (D-132).
