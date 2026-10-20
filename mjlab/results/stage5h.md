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
