# Stage 5H: the Stage 5F executor with a keep-alive landing reward (D-129)

The plan and its budget are in `stage5h-review.md` (round 17): at most 4 runs; pair-mode P(4+) is the primary readout.

| Run | Name | One change | Parent | Endpoint | Result |
|---|---|---|---|---|---|
| 1 | s5h-01-keepalive | Run 4's recipe (court mix 0.4, seed 73, 12,288 envs) with the pace term replaced by keep_alive_landing (`Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-G1`) | s5d-01-rally/model_1800 | iteration 2600, or the last checkpoint before the 7,000 s cap | running |

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
