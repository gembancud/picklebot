# Stage 2 gate — standing G1 hits a fed ball

Date: 2026-10-02. Branch `feat/mjlab-pivot`. Gate criterion (docs/MJLAB_PIVOT.md): *learns legal returns on easy feeds; report written.*

## Evidence
| Item | Result | Where |
|---|---|---|
| G1 + wrist paddle in the scene, envelope measured | Reach of the face centre up to 0.89 m; heights 0.30–1.73 m; peak face speed 14.0 m/s (fixed base) | `stage2-envelope.md` |
| Rules and legality | Batched port of Unity `DoublesRules` (rally level); 24 tests, mirroring 19 Unity cases | `picklebot_mj/rules.py`, `tests/test_rules.py` |
| Task | `Picklebot-Return-Stand-G1`: balance required, single-bounce forehand feed, contact then legal-return rewards, through mjlab's stock CLI | `picklebot_mj/tasks/return_stand.py` |
| Seeds | train 1–999, dev 4,200,000–4,200,999, final 9,200,000–9,200,999 (unused) | `picklebot_mj/seeds.py` |
| Training (≤ 2 h) | `return-stand-02`: 4096 envs, 722 iterations at the 7,000 s cap; fixed-endpoint `model_700` | `stage2-train.md` |
| **Dev evaluation** | **Legal return 96.1 % [95.0, 97.0] and 96.0 % [94.9, 96.8]** on two dev seeds (deterministic); contact 100 %; falls 0 %. Untrained baseline: 0 % legal, 81–83 % falls. | `stage2/eval-02-*.json` |
| Real stroke, not an artefact | Paddle 7.1 ± 0.2 m/s at contact; ball 3.3 → 11.2 m/s, matching the impulse model; net clearance 1.4 m; landing x 4.58 ± 0.93 m | `stage2-train.md` |
| Video | Side view: backswing, contact, ball over the net (successes) | `artifacts/stage2/return-stand-02-model_700.mp4` (local); frames in `stage2/` |

## Verdict
**Stage 2 gate: PASS.** The criterion is defined for easy feeds, and the policy meets it with a large margin on development evaluations.

## What this does not show (carried forward)
1. **Breadth:** one feed family (forehand, 0.30–0.65 m right, knee-to-waist height, single bounce, light topspin). No backhands, wide, deep, fast, spinning or volley feeds, and no footwork.
2. **Skill:** one stereotyped high loft with no placement control (no target input). It is not yet a rally player.
3. **Evidence quality:** development seeds were reused for two evaluations of one checkpoint from one training seed. No repeat training seeds, no final acceptance. The video shows successes only; the ~4 % misses (mostly long) are counted but not filmed.
4. **Physics simplifications** (Stage 1 caveats): kinematic paddle model with constant COR; paddle geoms don't collide with the body or floor; body contact approximated by pelvis/torso spheres; provisional court bounce.
5. **Throughput:** ~10k env steps/s with the robot; the Python ball term dominates (GPU ~33 % busy). Optimise before scaling training.

## Suggested next steps (not started; for the user to choose)
- Speed up the ball term (branch-free masks, no host syncs, CUDA graphs or `torch.compile`), then re-measure.
- Widen the feed distribution in stages (lateral range → backhand → depth and height → spin) with a curriculum, evaluating each family separately.
- Add a target input (landing region) and a placement metric, as in the Unity execution-v1 goals.
- Repeat training with 2–3 seeds before claiming robustness; record misses on video.
- Stage 3 per the plan: movement plus hitting, then teacher → student distillation.
