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
