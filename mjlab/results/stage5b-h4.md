# Stage 5B H4: the Drill 3 executor over the latent controller (D-050, D-056)

**Task** `Picklebot-Latent-Drill3-G1` (`picklebot_mj/tasks/__init__.py`):
- **Base:** S-D3b's Drill 3 task (gentle reach curriculum; 60 % real balls over all 14 families with an adaptive mix, 15 % move-to-spot, 25 % ghost swings). This is the task of the S-D3-style-c baseline, without its style reward.
- **Action:** H3's latent action space, a = [a_lat 32, a_wrist 3] through the frozen latent-07/latent_10651 (λ 1.0, wrist residual ±0.3 rad).
- **Rewards:**
  - removed: `pose`, `ready_stance`;
  - added: `latent_l2` −0.01;
  - `action_rate_l2` set to H3's −0.01. The inherited −0.1 on the raw latent action gave −5.5 per episode in the smoke run and swamped the task terms.
- **Network:** the student's 1024-512-256 actor and critic, plain PPO (mjlab G1 defaults).
- **Speed:** about 5.2 s per iteration at 4096 envs, about 1,350 iterations per 2 h run.

**Evaluation** (`scripts/h4_eval.sh`, `scripts/h4_summary.py`): the Stage 5 gate protocol on each fixed endpoint, on fresh dev seeds:
- 2048 envs × 16 s;
- every family, target A/B, with and without the hint;
- retention vs model_7600;
- style score.

**Main metric** (D-056 plateau rule): the no-hint legal-return rate pooled over all 14 families. Baseline S-D3-style-c: 78.7 %, style 4.84.

**Evaluation scripts now reset before the first step** (`stage2_eval.py`, `style_score.py`, as in reach_eval.py). Check on S-D3-style-c (dev seed 4200418, no hint, target A):
- legal 78.5 % → 78.9 %;
- robot falls 4.3 → 4.8 % per episode;
- recovery 0.975 m in both;
- every family within noise.

So the earlier Stage 5 numbers stand. The final gate re-evaluates S-D3-style-c with the same script and seeds as the H4 candidate.

## Runs (budget: 15 under D-056)
| # | Run | Change (written before launch) | From | Endpoint | Main metric | Style |
|---|---|---|---|---|---|---|
| 1 | h4-01 | the plan as written: fresh PPO, settings above | scratch | | | |
