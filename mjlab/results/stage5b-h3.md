# Stage 5B H3: steering the latent controller (paddle reach + root targets) — gate NOT met (2026-10-11)

**Task:** `Picklebot-Latent-Reach-*`. The high-level PPO acts on [a_lat 32, a_wrist 3].
- z = μ_p + λσ_p·tanh(a_lat), using the frozen H1 controller latent-07/10651;
- a ±0.3 rad right-wrist residual;
- a paddle target 0.3–0.7 m from the right shoulder and a root target within 1 m, both resampled every 2 s;
- standing start, 10 s episodes.

**Gate** (D-053): ≥ 80 % of paddle and of root targets reached (within 10 cm at any time in their 2 s window), falls ≤ 5 %. Deterministic evaluation, 1024 envs × 10 s, about 5100 windows.

| Run | Change (one per run) | Paddle | Root | Falls (eval) | Training notes |
|---|---|---:|---:|---:|---|
| reach-01 (5900) | λ 0.5, root reward σ 0.3 m | 61.0 % | 2.3 % | 11.4 % | root reward 0.08; stands and reaches |
| reach-02 (11700) | root reward σ 1.0 m | 62.4 % | 3.2 % | 14.3 % | root reward 0.62 (moves part-way); action std 0.99 |
| reach-03 (17500) | λ 0.5 → 1.0 | **73.2 %** | 8.5 % | **32.0 %** | paddle 1.60, root 0.70; action std 0.89 |
| reach-04 (23200), E1 | + root progress reward (pelvis speed toward target, clamped ±1 m/s, w 1.0) | 77.0 % | 31.9 % | 27.7 % | 25 cm: paddle 78.3 %, root 51.5 %; training falls 0.3/12 episodes; action std 1.00 |
| reach-05 (28900), E2 | + L2 penalty on a_lat (w 0.01) | 76.8 % | 38.5 % | 28.1 % | penalty -606 -> -0.26 per episode (raw a_lat was about ±14, deep in tanh saturation); action std 0.64; training falls 0.08/13.5 episodes |

## Observations
- **Paddle control improves with each change.** The latent can place the paddle.
- **Root targets: the robot moves toward them but rarely ends within 10 cm in 2 s.**
  - The pelvis sways a few cm per step and the walk is slow under the latent.
  - The 10 cm root tolerance is strict for a walking humanoid.
- **Training vs evaluation.** In training (stochastic actions) episodes run nearly full length, with rare falls. The deterministic evaluation falls 11–32 %, worse as λ grows. The policy's mean action through tanh drives z to the barrier edge more often than the noisy samples did, which suggests that steering into the latent's edges is unstable. This matches H2: the controller is fragile away from where the encoder put it.

## Options for the user
1. **Recommended: a bounded H3 extension** (2–3 more ≤ 2 h runs, one change each, same gate unless changed):
   - (a) more training at λ 1.0 (paddle still rising);
   - (b) a root *progress* reward, i.e. velocity toward the target, instead of a distance kernel;
   - (c) an action-magnitude penalty on a_lat, keeping z near the prior to reduce falls.
   - Separately, the user may decide whether the root tolerance should be 25 cm (a stepping robot's pelvis rarely sits within 10 cm on cue).
2. **Go to H4 now** with reach-03 as the starting point: the real test is ball-hitting, judged against S-D3-style-c. Risk: a 32 % fall rate in deterministic control.
3. **Rethink the controller.** A MaskedMimic-style goal-conditioned controller (it takes root and hand targets directly) suits exactly this need. It is a bigger build and a new decision.
4. **Fall back to the flat executor** S-D3-style-c (task-best) for Stage 6 and revisit natural motion later.

## Evaluation correction (2026-10-11): the table above is superseded
`scripts/motion/reach_eval.py` had two bugs, which affected every row above:
1. **No `env.reset()` before the first step.** The first episode ran without the reset events, and over half the envs fell in the first 3 s. Diagnostic `artifacts/eval/reach-fall-diag.json` (reach-05, 20 s, 1024 envs):
   - without the reset, falls per second were 72, 410, 106, 6, 0, …;
   - with the reset, 7 falls in 2,048 episodes, deterministic;
   - stochastic actions gave the same rate.
2. **The tally counted the construction-time command window.** It was measured at the uninitialised spawn and always missed: one window in six, which capped every reach rate at 83.3 %. The tally is now cleared after the reset.

Training was not affected. The tally is evaluation-only, and training resets run normally.

Corrected results: the same checkpoints and the same dev seeds (4200410–4200414), so the fix is the only change. Files `stage5b-h3-reach-0N-v2.json`.

| Run | Paddle 10 cm | Root 10 cm | Paddle 25 cm | Root 25 cm | Falls |
|---|---:|---:|---:|---:|---:|
| reach-01 | 99.8 % | 2.4 % | 99.9 % | 9.9 % | 0.0 % |
| reach-02 | 99.8 % | 2.6 % | 100.0 % | 11.3 % | 0.1 % |
| reach-03 | 100.0 % | 10.6 % | 100.0 % | 34.3 % | 0.0 % |
| reach-04 (E1) | 100.0 % | 45.5 % | 100.0 % | 69.9 % | 0.2 % |
| reach-05 (E2) | 100.0 % | **54.7 %** | 100.0 % | 74.7 % | 0.3 % |

**Gate (≥ 80 / ≥ 80 / ≤ 5 %):** paddle and falls are met by every run. **Root reach is the only miss.** The "training vs evaluation fall gap" in the Observations above was this evaluation bug, not unstable deterministic control.

`scripts/motion/prior_eval.py` (H2) had the same missing reset. Re-run (`stage5b-h2-*-v2.json`, same seeds), falls / style median:
- latent-06: 47.8 % / 3.44;
- latent-07: 39.1 % / 3.58;
- latent-08: 95.9 % / 3.83.

These are essentially unchanged, so the H2 conclusion stands. The tracking evaluations (H0/H1) already reset.

## E3 (2026-10-11): more training, the last extension run
reach-06-more is model_34700 (the cap), trained from reach-05/model_28900 with the same task (E2) and settings. It was evaluated with the corrected script on fresh dev seed 4200416 (`stage5b-h3-reach-06.json`):

| Run | Paddle 10 cm | Root 10 cm | Paddle 25 cm | Root 25 cm | Falls |
|---|---:|---:|---:|---:|---:|
| reach-06 (E3) | 100.0 % | **59.4 %** | 100.0 % | 77.3 % | 0.1 % |

**H3 is missed on root reach only.** Root reach across runs (corrected) was 10.6 → 45.5 (E1) → 54.7 (E2) → 59.4 % (E3). The gains are shrinking, about 5 points per 2 h run. At the end of training the mean root distance is about 16 cm.

## Options for the user (after D-055)
1. **Recommended: H3 is good enough; go to H4.**
   - The executor can place the paddle 100 % of the time, it does not fall (0.1 %), and it moves its body to targets (77 % within 25 cm in 2 s).
   - Body precision matters for H4 only insofar as it gets the paddle to the ball, and H4's own gate tests that: per-family legal returns within 5 points of S-D3-style-c, a style score ≤ 3.86, and videos.
   - Start H4 from reach-06/model_34700's action space and controller.
2. **Revise the root criterion** (for example 25 cm, or a 3 s window) and judge again. On its own this still misses at 25 cm (77.3 % vs 80 %), so it would need more training too.
3. **More H3 training.** At about 5 points per 2 h run, 80 % at 10 cm would take roughly four or more further runs, if the trend holds.
4. **Rethink the controller** (MaskedMimic-style), or **fall back** to the flat executor S-D3-style-c for Stage 6.
