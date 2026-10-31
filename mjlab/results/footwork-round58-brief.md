# Panel round 58 brief: probe P1 = NO-ADAPT (2026-10-31)

Read first:
- D-183 to D-188 (with addenda) in docs/DECISIONS.md;
- mjlab/results/footwork-review.md;
- docs/research/footwork-route-2026-10-29.md (sections 1, 5 and 8);
- results/h1adapt01-summary.txt and results/h1fwdec-summary.txt.

## Where the footwork phase stands

| step | result |
|---|---|
| 1 | **Done.** Footwork specialist fw1b-S model_16600 is BODY-OK under mean actions: about 1.9-2.1 m/s in every direction, arrival >= 0.99, backpedals facing the net. |
| 2, H0 | h0-fw-02: **H0F-FAIL**. LAFAN1 travel 0.865 < 0.90; serve / smash / backhand volley -3.3 to -3.8 points. Held-out footwork travel 0.963 (parent 0.50). |
| 2, H1' | H1' (decoder-only re-distil from it): held-out footwork travel 0.956. Strokes vs latent-07: serve **-23**, smash -8, backhand volley -5. A zero-shot swap into the composite is INVALID: falls 7 -> 202 per 1,000 env-s, arrival about 0. |
| 2, P1 | **NO-ADAPT** (this round). See below. |

## P1 (D-188)

Rally 22b's residual was fine-tuned for 400 iterations on H1': the one change was the controller, via the cfg override. It passed its +120 kill line, with training falls 86.8 -> 27.0.

Endpoint, paired on dev 4220242 (mean actions, Measure60):

| | 22b + latent-07 | P1 + H1' | validity line |
|---|---|---|---|
| falls per 1,000 env-s | 6.9 | **79.5** | <= 13.8 |
| worst-sector untimed arrival | 0.88 | **0.015** | >= 0.80 |
| fallen + censored share | 0.109 | **0.401** | <= 0.15 |
| R (left / back) | 0.635 | 0.742 (not read: INVALID) | |
| sustained p50 (m/s) | 1.16-1.45 | 1.46-1.82 | |
| peak p50 (m/s) | 1.39-1.66 | 1.90-2.28 | |

- **VERDICT: NO-ADAPT** (falls > 50).
- Pairs rally read, reported only (CONFOUNDED), dev 4220244:
  - base: P(5+) open 0.387, mean length 2.57;
  - P1: **0 shots** in 53,852 rallies.
- Under D-188: re-ask the panel, (c) vs (d).

## What we know about the cap and the gain (for the cost / benefit call)

- **The rally composite is travel-capped by the motion layer.** Bridge: CAP-INHERITED, R 0.636. The speed it lacks is real: the body does about 2 m/s.
- **A faster decoder moves the composite's legs faster, but the composite cannot balance or stop on it.** That holds zero-shot, and after 400 iterations of residual adaptation. RES_BASE (frozen) and the residual were built on latent-07's dynamics.
- **The footwork-route doc (section 1) bounds the footwork fix:**
  - left / back feeder balls are about 21 %, returned 43-46 %;
  - lifting them to 90 % gives feeder legal about 89 %;
  - the target needs about 95 % per ball;
  - footwork is necessary, not sufficient.
- **Best rally so far:** P(5+) open about 0.39 (runs 22b / 23). Target 0.80.
- **Experiment design's D-188 gate on (c):** a CPU-only P(5+) upper bound, from existing rally logs, on removing late left / back arrivals. If it cannot reach about 0.5, weigh (d) first. **This bound has not been computed yet.** It could be the first action, with no GPU.

## Options

- **(c) Full route-D chain on a stroke-fixed decoder.**
  1. (a) H1'' re-distil with a per-source sampler floor (training seed 180; the D-188 gates);
  2. a RES_BASE rebuild on H1'' (s5c-14 / 15 / 17 / 18 pattern, about 8 GPU-h);
  3. a rally re-climb (20-40 GPU-h).

  Total about 30-50 GPU-h with high risk: D-107 shows consolidation can lose skill.
- **(d) Another route to fast footwork that keeps latent-07.** For example:
  - **Kickstart the rally residual toward the footwork specialist's joint targets in move episodes** (footwork-route doc, route C; the specialist now exists and is BODY-OK).
  - A leg-joint residual (route (a) in the doc; runs 12-13 failed when the learner was frozen).
  - A hybrid: switch the decoder to H1' only in move or footwork phases (new code; risky).
- **(e) Pause footwork and return to the within-reach rally levers** (ball-1 work, feeder share), taking the about-0.5 ceiling as the near-term goal. Then come back to footwork.

## Questions for round 58

1. Correction check on D-188 and P1.
2. (c), (d) or (e)? Give the first action and its coded lines. Should the CPU-only P(5+) bound run first?
3. Is the footwork phase plan still the right climb? Give an honest cost-per-gain view.

Seeds: dev next free 4220245 (spares 4220227-4220229, 4220235-4220240, 4220243). Training seeds from 181 (180 reserved for H1'').
