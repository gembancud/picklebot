# Stage 5B H0: the tracking teacher covers footwork (2026-10-10) — gate MET

**Teacher:** `2026-10-10_05-18-15_tracking-20-decay/model_60800`. Task `Picklebot-Tracking-TennisLafan2-Huge-G1`: 2048-1024-512 actor and critic, paddle G1 with full self-collision plus the paddle face, multi-clip command with 50/50 tennis/LAFAN1 sampling.

**Motion set:** `tennis-lafan2.npz`, 107 clips.
- **Tennis-MoCap v5:** 90 clips, 42 min.
- **LAFAN1:** 17 clips, 71 min (walk, run, sprint, fight-and-sports). Jumps and mixed actions were dropped (D-051).

## Gate (D-050/D-051), final evaluation on dev seed 4,200,316, 4 repeats (`stage5b-h0-block-final.json`)
| Item | Result | Threshold |
|---|---|---|
| Tennis, per stroke, overall | **93.2 %** (697 segments) | ≥ 87.5 % |
| Per stroke type | FH 98.0, BH 90.7, FH-v 95.8, BH-v 95.0, serve 89.0, smash 89.5 % | each ≥ 77 % |
| LAFAN1, 4 s windows | **89.2 %** (walk 94.8, run 85.6, sprint 84.7, sports 75.8 %) | ≥ 85 % |
| Falls (unintended) | **0.59 %** (raw 2.0 %, see below) | ≤ 1 % |
| r-MPKPE (reported against the D-049 deviation) | 8.2 cm | (6 cm bound, D-049) |

## How it got there
- **Tennis-only teacher** (tracking-06-wide, 1024-wide): 90.5 % per stroke.
- **Adding LAFAN1** (tracking-08 to tracking-10, chained): tennis 73.7 → 76.8 %, LAFAN1 62.6 → 66.5 %. The gain stalled.
- **Rule 8 follow-ups:** a 2048-wide network (80.9 / 69.3 %), then more training (82.4 / 70.9 %). Gate missed; the user decided D-051 (drop jumps and mixed actions) and D-052 (long-training block).

**Long block** (runs 13–20, 2048-wide, 4096 envs; 8192 envs gave only 1.27× samples/s, below the 1.3× bar):

| Evaluation | After | Tennis | LAFAN1 | Main metric |
|---|---|---:|---:|---:|
| baseline | model_38300 | 82.6 | 76.4 | 79.5 |
| 1 | run 2 | 86.2 | 84.7 | 85.5 |
| 2 | run 4 | 89.7 | 87.8 | 88.8 |
| 3 | run 6 | 87.4 | 86.9 | 87.2 (< 1 point gain, so the decay starts) |
| final | 2 decay runs at a fixed lr 1e-5 | **93.2** | **89.2** | **91.2** |

- **Decay deviation:** D-052 named 1e-4, but the adaptive rate had already fallen to 3.4e-5, so 1e-5 kept the intent of a decay.
- **Total teacher training:** about 61k iterations, roughly 6e9 samples and about 35 GPU-hours.

## Fall measure corrected (2026-10-09)
LAFAN1 walk3 subjects 1 and 4 crawl or lie down: the reference torso drops to 0.11–0.17 m in about 9–10 % of frames. The raw measure (torso below 0.5 m) counted the robot following them as falls.
- **Corrected measure:** a fall needs the reference torso above 0.6 m while the robot's is below 0.5 m.
- **Both rates reported:** 0.59 % corrected, 2.0 % raw.

## Footwork coverage (`scripts/motion/footwork_coverage.py`, `stage5b-footwork-coverage.json`)
Heuristics on the reference motion, seconds per clip type:

| Type | Min | Ready stance | Lateral shuffle |
|---|---:|---:|---:|
| forehand / backhand | 7.4 / 7.7 | 23 / 17 | 29 / 27 |
| FH / BH volley | 7.9 / 7.0 | 22 / 19 | 42 / 15 |
| serve / smash | 4.9 / 7.0 | 3 / 22 | 10 / 24 |
| LAFAN1 walk / run / sprint / sports | 37.3 / 16.1 / 9.1 / 8.2 | 75 / 9 / 34 / 48 | 74 / 62 / 15 / 79 |

- **Ready stance and lateral shuffles are present but thin:** about 5 and 6 minutes of 112.
- **The crossover and split-step heuristics are not reliable here.** Running and walking gaits cross the midline, and heel-off counts as "both feet up". Visual review is needed for those.
- **Pickleball-specific dinks and underhand serves are absent.** The latent controller can express only what is here.

## Next: H1
Distil this teacher into the encoder, prior and decoder latent controller.
