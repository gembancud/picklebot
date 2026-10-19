# Stage 5E gate: more reliable shots — NOT MET (2026-10-19)

The loop ended under the plateau rule (D-100, D-106).
- **Strikes:** three runs were killed (runs 1, 3 and 4). Run 2 was also killed but, per the user, it is not a strike (D-104).
- **Budget:** 4 of the 15 training runs were used.

**Final candidate** (rule D-096, applied in D-106 before any final result): **run 3, `s5e-03-v2-mixlat/model_2700`**.
- **Label:** "best drill v2, failed kill rules". It has the best per-shot p of the four runs, and it failed the court and arrival kill rules.
- **What it is:** a residual executor around run 18, continued from Stage 5D run 1 by PPO on drill v2, with training latency drawn from 0-40 ms (ball) and 0-20 ms (commands).

**Paired final** (`scripts/h5e_final.sh`):
- **Drill v2:** candidate and run 22 on the same four fresh dev seeds 4200472-4200475. Noisy planner spot and sim-to-real on, as frozen in D-101.
- **Court drill:** the candidate on 4200476-4200479.
- **Stage 5C battery:** the candidate once on 4200894-4200899.

No final seeds were used.

## Gate

| Criterion | Threshold | Candidate (run 3) | Run 22 | Met? |
|---|---|---|---|---|
| Per-shot legal p, drill v2 (noisy spot, sim-to-real on; 4 seeds pooled) | >= 0.80 | **0.585** [0.582, 0.587] (157,666 feeds) | 0.297 [0.295, 0.300] | no |
| Neutral group, Wilson lower bound | >= 0.92 | 0.678 (p 0.681) | 0.320 | no |
| Moderate group, Wilson lower bound | >= 0.80 | 0.512 (p 0.517) | 0.263 | no |
| Extreme group, Wilson lower bound | >= 0.55 | 0.262 (p 0.268) | 0.233 | no |
| Court falls (court drill, per robot episode; 4 seeds) | <= 1 % | 4.1 % (4.0 / 4.6 / 3.8 / 4.1 %) | 3.6 % (run 0) | no |
| Move-to-spot arrival, every direction | >= 90 % | 69.5-91.1 % (back 69.5 %, back-right 69.8 %) | >= 99.2 % (run 0) | no |
| Court main metric (no latency; 4 seeds pooled) | >= 76.8 % | **41.4 %** [41.0, 41.8] | 78.5 % (run 0) | no |
| Style, new reference (tennis-v5 0.5, LAFAN1 0.25, 100STYLE held-out 0.25) | <= 3.86 | **3.895** | 4.064 (run 0) | no (0.035 over) |

**0 of the 8 gate items are met.**
- **Style:** the candidate is the closest to its line. On the old reference it scores 3.869, and in its own run 3 battery it scored 3.862 (new reference).
- **Rally lengths** (reported, not gated): P(rally >= 5) is 9.1 % for the candidate and 0.5 % for run 22. P(rally >= 10) is 1.1 % and 0.0 %.
- **Scope of the gate:** p = 0.80 would mean about 11 % P(rally >= 10), less than Stage 5D's 20 % target. Only the 0.85 stretch target matches it (D-098).

## Runs

| # | Change (written before launch) | Drill v2 p | Court (no latency) | Arrival min | Court falls | Style (new reference) | Result |
|---|---|---:|---:|---:|---:|---:|---|
| 0 | (Stage 5D run 1, before training) | 0.306 | 78.9 % | 99.7 % | 6.2 % | 4.258 | stage start |
| 1 | consolidation into one lambda-3 executor | 0.295 | 76.66 % | 96.5 % | 6.7 % | 4.272 | killed (court), strike 1 |
| 2 | PPO on drill v2, latency 20-40 / 0-20 ms | 0.553 | 26.9 % | 90.4 % | 4.0 % | 4.039 | killed (court), not a strike (D-104) |
| 3 | latency drawn from 0 ms upward | **0.589** | 41.6 % | 69.6 % | 3.9 % | **3.862** | killed (court, arrival), strike 2 |
| 4 | half the episodes clean, half delayed | 0.550 | 53.4 % | 71.9 % | 4.6 % | 4.034 | killed (court, arrival), strike 3 |

Full log: [stage5e.md](stage5e.md). Decisions: D-096 to D-106.

## What Stage 5E established

1. **Latency is the main obstacle, not the drill or the planner.**
   - With every sim-to-real effect off, the start point returns 72 % of drill v2 shots. With 20-40 ms ball latency and 0-20 ms command latency it returns 31 %. Each delay alone costs about 20 points; ball-state noise costs nothing.
   - The planner's spot changes p by only 0-2 points, because no executor has learned to rely on it.
2. **Training under latency recovers much of the loss,** but specialises.
   - It roughly doubles drill v2 p, from 0.31 to 0.55-0.59.
   - The latency-trained executors then play worse without latency: run 2's no-latency court drill is 26.9 %, while with latency it is 47.7 %.
   - Drawing latency from zero (run 3) or keeping half the episodes clean (run 4) narrowed the gap: court drill 41.6 % and 53.4 %. None came close to 76.8 %.
3. **The frozen motion controller (H1) is not robust to command delay.**
   - The start point's walking falls from 99-100 % to 68-91 % arrival under delay, before any training.
   - Run 3 and run 4 lost arrival backwards and back-right (69.6-81 %), the directions that already suffer most under delay.
   - The executor steers the latent space of a controller that was trained without delay, and it cannot fully repair that controller's balance.
4. **Consolidation lost skill:** the distilled single executor dropped below the court kill line, and P(rally >= 10) on the Stage 5D rally evaluation fell from 10.2 % to 5.5 %.
5. **Human footwork data helped style.** 100STYLE Neutral FW, BW and SW were retargeted and accepted; SR (sidestep running) failed the foot-sliding check.
   - latent-07 tracks every 100STYLE window (57/57).
   - Drill v2 training brought style from 4.258 to 3.862-3.895 on the new reference, the best scores of any executor.
   - The new reference is stricter than the old one: h4-25b scores 3.910 on it, against 3.878 on the old.

## Deviations and caveats (stated in full)

1. **The candidate failed its kill rules** (court, arrival). It is named under the Stage 5D rule (D-096) and labelled.
2. **Run 2's kill is not a strike** (user, D-104). Its kill rule measured it outside the conditions it was trained for: the D-101 retention battery has no latency.
3. **Training latency changed twice after run 2** (D-104, D-105; the user chose both): from 20-40 ms only, to drawn from 0, to half the episodes clean. The evaluation and the gate stayed as frozen in D-101.
4. **The D-097 run order was not followed after run 2.** The falls fix, the stance spot on every feed, failure-weighted feeds and the backspin teacher were never run. The latency findings took the remaining runs, and the plateau rule ended the stage first.
5. **Retention design flaw:** D-101 froze the retention battery without the latency the stage trains under. It was found after run 2 and kept unchanged (D-104).
6. **The new style reference is stricter than expected.** D-097 called it a partial loosening; the frozen shares made it stricter for every executor (D-102).
7. **Small items:**
   - Tests: the gait-anchor test and two latent-drill tests fail only in long batched runs (a torch.compile recompile limit across environment sizes), and pass when run alone.
   - Dev seeds: the range 4200000-4200999 is nearly used up.

## Next (for the user to decide)

The evidence points at the controller.
- **D-097 rebuild rule:** "rebuild if p plateaus below 0.80". p reached 0.589 and the stage ended on the plateau rule.
- **Candidate next stage:**
  - retrain the H0 tracking teacher and the H1 motion controller with command latency (domain randomisation from 0 ms), so walking and balance hold up under delay;
  - then re-run the Stage 5E executor work on top of it: drill v2, the spot, failure-weighted feeds, the backspin teacher.
- **Also worth carrying over:** the 100STYLE footwork clips (discriminator style reward, wrists excluded), and court-wide feeds in the training mix, against forgetting.

## Review videos

Saved in `mjlab/artifacts/videos/h5c/share5e/`; every clip is an H.264 faststart MP4 with a GIF preview.
- **Candidate, court-wide clips:** side, behind, kitchen, move and long rally, on the Stage 5D video seeds 4200360-4200364. The run 22 clips on the same seeds are copied from Stage 5D.
- **Drill v2 rallies:** a 30 s drill v2 rally with the noisy planner and sim-to-real on, for the candidate and for run 22.
