# Stage 5B H1: the tracking teacher distilled into a latent controller (2026-10-10) — gate MET

**Student:** `artifacts/train/latent/latent-06/latent_9131.pt` (`picklebot_mj/latent.py`).
- **Encoder** q(z | s, g) sees all 160 tracking observations. The goal g is the first 67: reference joint command and anchor pose error.
- **Prior** p(z | s) and **decoder** D(s, z) see only the 93 proprioceptive observations: base velocities, joint positions and velocities, last action.
- **Shape:** 32-d latent; encoder and prior 1024-512; decoder 1024-512-256.

**Teacher:** `tracking-20-decay/model_60800` (H0).

## Training (`scripts/distill_latent.py`, DAgger on the teacher's own task, 4096 envs)
| Run | Iterations | Settings | Student tennis / LAFAN1 (dev seed) |
|---|---|---|---|
| latent-01 | 0–1729 | beta (teacher share) 1 → 0 over 800 its; KL 0.01 → 0.001 over a 4000-it schedule | 72.6 / 76.5 % (4200317) |
| latent-02 | 1729–3400 | same schedule | 81.7 / 83.1 % (4200318) |
| latent-03 | 3400–4000 | schedule end | 89.5 / 87.7 % (4200319) |
| latent-04 | 4000–5708 | KL held at 0.001 (chain run 4) | 88.4 / 87.1 % (4200320); chain ends, G1 missed on serve and smash |
| latent-05 | 5708–7425 | **rule 8 follow-up 1: KL weight 1e-4** | 92.0 / 88.9 % (4200321); serve 85.3, 0.7 short |
| latent-06 | 7425–9131 | **follow-up 2: more training** (same settings) | **93.0 / 88.8 %** (4200322) |

The KL weight was the key lever. At 1e-3 the latent carried about 2.7 nats and fast overhead strokes failed; at 1e-4 it carries about 12. Final distillation MSE is 0.002.

## Gate G1 (teacher minus 3 points; dev seed 4,200,322, 4 repeats; `stage5b-h1-latent-06.json`)
| Item | Student | Teacher | Threshold |
|---|---:|---:|---:|
| Tennis overall | **93.0 %** | 93.2 | ≥ 90.2 |
| Forehand | 95.8 % | 98.0 | ≥ 95.0 |
| Backhand | 93.4 % | 90.7 | ≥ 87.7 |
| Forehand volley | 95.2 % | 95.8 | ≥ 92.8 |
| Backhand volley | 96.1 % | 95.0 | ≥ 92.0 |
| Serve | 87.3 % | 89.0 | ≥ 86.0 |
| Smash | 88.8 % | 89.5 | ≥ 86.5 |
| LAFAN1 (4 s windows) | 88.8 % | 89.2 | ≥ 86.2 |
| r-MPKPE | 8.3 cm | 8.2 | ≤ 9.2 |
| Falls (unintended) | 0.63 % | 0.59 | ≤ 1 % |

The raw fall rate is 2.1 %.

## What this gives
The **prior and decoder** see no reference information, so together they form a controller whose behaviour comes only from the human clips. Higher layers drive it through z. A tracking task can drive it through the encoder (it matches the teacher), and a task policy can drive it through z = μ_p + λσ_p·tanh(a) (H3/H4).

**Caveat:** a low KL weight makes the encoder more informative, but the prior is a looser guide. H2 measures whether prior-only rollouts still stay human-like and upright.

## Next: H2
Prior quality: 1,000 rollouts of 10 s from the prior alone (z = μ_p + σ_p·ε).
- **Gate:** falls ≤ 5 %, style score ≤ 2.0.
- Videos for the user.
