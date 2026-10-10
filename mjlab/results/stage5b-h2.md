# Stage 5B H2: prior quality — gate NOT met after the run and both rule-8 follow-ups (2026-10-10)

**Test** (`scripts/motion/prior_eval.py`):
- 1,000 rollouts of 10 s from random clip frames, the reference frozen;
- action = D(s, μ_p + σ_p·ε), with fresh ε each step;
- a fall is the torso below 0.5 m or a tilt above 60°;
- style = median nearest-clip pose distance (S-D3b 4.82, human floor 0.94).

**Gate:** falls ≤ 5 %, style ≤ 2.0.

| Student | Change | Falls (noise) | Falls (no noise, diagnostic) | Style | H1 re-check (tennis / LAFAN1) |
|---|---|---:|---:|---:|---|
| latent-04/5708 (KL 1e-3) | (diagnostic) | 22.9 % | 19.3 % | 3.07–3.25 | 88.4 / 87.1 (missed H1) |
| latent-06/9131 (KL 1e-4) | H1 endpoint | **46.1 %** | 39.8 % | 3.38 | 93.0 / 88.8 |
| latent-07/10651 | + prior imitation loss 0.5 | 40.7 % | 36.5 % | 3.57 | 93.2 / 88.8 |
| latent-08/12140 | + half the rollouts driven by the prior | 96.4 % | 36.6 % | 3.81 | 93.6 / 89.2 |

Follow-up 2 inflated the prior's spread (KL 12 → 54), so random noise became destructive.

## What the evidence says
- **The encoder path is excellent.** Tracking matches the teacher (93–94 % per stroke). The controller can produce the human motion when told precisely what to do.
- **The prior alone is not a usable stand-alone controller.**
  - Its mean latent still falls about 37–40 % of the time from mid-motion starts.
  - The heavier-KL student falls about 20 %.
  - Nothing tested here fixes that: a prior imitation loss, prior-driven rollouts, or a stronger KL (which costs H1).
  - From a mid-sprint or mid-swing frame, a reference-free "continue" is ambiguous, and averaging the possibilities is unstable.
- **The H2 test may be harsher than what H3/H4 need.**
  - In LATENT the high-level policy is *trained* to choose z, and the action barrier keeps it near the prior. It never uses random prior samples.
  - Our starts are also mid-motion frames (sprints, follow-throughs), not a ready stance.

## Options for the user
1. **Recommended:** treat H2 as a diagnostic, not a gate, and go to **H3** with the best encoder-quality student (latent-07/10651: H1 93.2 / 88.8; prior imitation trained; KL 12.6).
   - The high level steers z = μ_p + λσ_p·tanh(a), with λ in the plan; a small λ (e.g. 0.5) is the first H3 setting.
   - H3's controllability gate (paddle reach and root targets, falls ≤ 5 %) and H4's style score (≤ 3.86) then judge the controller on what it is used for.
2. **Re-architect the prior** (MaskedMimic-style: a prior conditioned on sparse goals such as root or paddle targets instead of nothing), so it is never asked to act goal-free. A bigger build; a new decision.
3. **Trade H1 for prior stability.** A stronger KL (1e-3 to 1e-2) gives prior falls of about 20 % but misses H1 on serves and smashes.
4. **Revisit the H2 thresholds or start states**, e.g. rollouts from a ready stance instead of mid-motion frames.
