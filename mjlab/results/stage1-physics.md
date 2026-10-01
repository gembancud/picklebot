# Stage 1 — ball, court, net and paddle physics: gate report

Date: 2026-10-02. Branch `feat/mjlab-pivot`. Decisions: D-038 (mjlab), D-039 (analytic ball contacts).
Code: `mjlab/picklebot_mj/{court,ball,ball_sim,rig_env}.py`. Tests: `mjlab/tests/` (90 pass, 13 strict xfails documenting the rejected native-contact baseline). Run with `bash -l mjlab/scripts/test.sh` in WSL.

## Design summary
- **Court and net:** regulation dimensions identical to Unity `CourtGeometryV0/V1`. The net sags from 0.9144 m at the sidelines to 0.8636 m at the centre; posts sit 6.7056 m apart.
- **Ball:** 24 g, r = 37 mm, hollow-shell inertia. Drag, Magnus lift and spin decay are ported from Unity `AerodynamicModelV1` (Cd 0.30, lift slope 0.195, Cl ≤ 0.25).
- **Contacts:** analytic and batched on the GPU (D-039), because native MuJoCo soft contacts gave impact-phase-dependent restitution (`stage1-bounce.md`). The model uses swept and closest-point tests, a rigid-sphere impulse with normal COR, Coulomb friction with the slip/roll transition, and spin coupling. Sub-steps adapt so the ball never moves more than 0.5 r relative to any surface per sub-step.
- **Integration:** inside an mjlab env, the ball advances on every MuJoCo physics step (5 ms). The paddle pose and velocity come from the scene; the reaction impulse is returned.

## Gate criteria

| Criterion | Result | Verdict |
|---|---|---|
| Official drop band (1.981 m drop, ball-bottom datum; rebound top 0.762–0.864 m) | Court COR 0.6381 gives 0.813 m. Apex/height ratio spread < 0.2 % across 53 drop heights and phases (1.95–2.05 m + random), at 1/4/10 sub-steps and at dt 2–20 ms. Native MuJoCo spread COR 0.10–2.88 on the same sweep. | **PASS** (provisional: no acrylic-court reference exists; the official granite band is used as a bound) |
| Impact timing and drift (spec §5) | Analytic toss/drop timing is exact to integration error; no horizontal drift on vertical drops (tests) | **PASS** |
| No energy gain | Random batches: 4,096 court impacts, 2,048 net impacts and 2,048 paddle impacts with spin; energy is monotone through repeated bounces | **PASS** |
| Flight vs RK4 reference | `BallSim` matches `reference_flight` to 1e-6 m over 0.3 s. Native MuJoCo flight with the same wrench: 2.6–3.6 cm after 1 s at 5 ms (first order) | **PASS** |
| Spin behaviour | Angled bounces gain topspin; topspin keeps pace; backspin skids at speed and checks back at low speed; brushing the paddle gives topspin (> 50 rad/s); topspin dives and backspin floats in flight | **PASS** |
| Net stops balls, clear balls pass | 12 and 30 m/s balls at 12 positions are stopped at dt 5 and 20 ms and returned at < 0.3× speed. A ball 10 cm over the net is untouched. A net-cord touch deflects upward. Balls beyond the posts pass; posts bounce balls back. | **PASS** |
| Paddle PBCoR ≤ 0.43 | Surrogate 0.40 ± 0.02 at 5/10/20/30 m/s | **PASS** |
| No paddle tunnelling | 30 m/s swing through a resting ball at 40 phases, dt 5 and 20 ms with one requested sub-step: all hit, exit speed (1 + e)·30 ± 0.2 m/s | **PASS** |
| Momentum | Ball Δp − gravity = −paddle impulse to 1e-9 | **PASS** |
| GPU integration | 4096 envs, 8,192 scripted swings: hit 100 %, landed 100 %, far court 89.9 % (misses long from the scripted speed range), net touches 0. Video rendered (`mjlab/artifacts/stage1/rig.mp4`, local). | **PASS** |
| Throughput ≥ 10× Unity (≥ 10k steps/s) with ball and paddle | **38,153 env steps/s** at 4096 envs (152,613 physics steps/s), 38× Unity | **PASS** |

## Caveats carried into Stage 2
1. **Throughput with a robot is not yet measured.** The ball sim costs about 26 ms per physics step at 4096 envs (many small kernels, host syncs from `.any()` and adaptive sub-step counts). Estimate with the G1: the Stage 0 G1 velocity task took ~48 ms of collection per env step, plus 4 × ~21 ms of ball sim, gives roughly 30k steps/s at 4096 envs. Still above the gate, but the ball sim would dominate. Optimise (branch-free masks, CUDA graphs or `torch.compile`) if Stage 2 measurements require it.
2. **The reaction impulse is not yet applied to a dynamic body.** The rig paddle is kinematic; the G1 wrist will receive it via `xfrc_applied` in Stage 2.
3. **Paddle model simplifications:** a kinematic (infinite-mass) face with constant COR, no dwell or trampoline effect, no grip compliance, and the handle excluded from collisions. Paddle and ball parameters are Unity's provisional surrogates, not measurements.
4. **Court bounce is provisional:** calibrated to the official drop band on granite; there is no acrylic-court reference (as in Unity Phase 1B).
5. Ball contact with robot bodies other than the paddle is not modelled yet (planned as a rules event in Stage 2).

## Verdict
**Stage 1 gate: PASS**, with the caveats above. Proceed to Stage 2 (standing G1 with wrist paddle).
