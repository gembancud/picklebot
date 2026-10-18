# Stage 5E: more reliable shots (D-096..D-101)

**Gate** (D-097/D-098, never loosened):
- **Per-shot legal p >= 0.80** on drill v2, with the noisy planner's spot (`h5e_eval.sh` job `v2-noisy`).
- **Group floors** on Wilson lower bounds: neutral >= 0.92, moderate >= 0.80, extreme >= 0.55.
- **Court falls** <= 1 %.
- **Move-to-spot arrival** >= 90 % in every direction.
- **Court main metric** >= 76.8 %.
- **Style** <= 3.86 on the new reference. The old-reference score is reported alongside.

Stretch target: p >= 0.85. **p = 0.80 implies about 11 % P(rally >= 10), below Stage 5D's 20 %.**

**Loop rules (D-100):**
- **Start:** Stage 5D run 1 (`s5d-01-rally/model_1800`), consolidated first. Run 22 (`s5c-22-res-rally/model_900`) is the comparison.
- **Budget:** up to 15 runs, each <= 2 h, with a fixed endpoint and one change written down before launch.
- **Plateau:** 3 executor runs in a row each < 1 point gain in per-shot p (v2-noisy). Killed runs count as strikes. A run within 1.5 points of the best is repeated on a second seed.
- **Kill thresholds:** fixed for the whole stage from run 0.

**Run order (D-097):**
1. consolidation;
2. falls fix (mechanism written before the run);
3. stance spot on every feed;
4. failure-weighted feeds;
5. backspin family teacher.

## Run 0: the frozen battery before any training (dev seeds 4200365-4200399)

| Executor | v2 p, noisy spot [95 % CI] | neutral / moderate / extreme (Wilson low) | v2 p, clean spot | v2 p, no spot | P(rally >= 5 / >= 10), noisy | Court main | Court falls | Arrival (min) | Style old / new |
|---|---|---|---|---|---|---|---|---|---|
| Stage 5D run 1 (start) | **0.306** [0.302, 0.311] | 0.338 / 0.244 / 0.230 | 0.307 | 0.318 | 0.005 / 0.000 | 78.9 % | 6.2 % | 99.7 % (back-left) | 4.214 / 4.258 |
| run 22 | 0.296 [0.292, 0.300] | 0.312 / 0.263 / 0.232 | 0.298 | 0.311 | 0.004 / 0.000 | 78.5 % | 3.6 % | 99.2 % (left) | 4.023 / 4.064 |

h4-25b style (information only, D-098): 3.878 on the old reference, **3.910 on the new one** (seed 4200397). The stage baseline itself does not reach 3.86 on the new reference.

**Stage kill thresholds** (D-102, fixed from run 0 for the whole stage; base = Stage 5D run 1):
- v2 p (noisy) < 0.276 (base 0.306 - 3 points);
- court main metric < 76.8 %;
- court falls > 7.2 % (base 6.2 % + 1 point);
- arrival < 90 % in any direction;
- style on the new reference > 4.41 (base 4.258 + 0.15).

## Runs

| # | Run | Change (written before launch) | From | Endpoint | v2 p (noisy) | Groups (Wilson low) | Court main | Court falls | Arrival min | Style old / new |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s5e-01-consolidate | consolidation only (D-102): composite of run 18 + Stage 5D run 1 residual -> one lambda-3 executor, on the Stage 5D rally drill (no latency) | run 18 init; teacher s5d-01/model_1800 | model_126 (loss plateau, 11 min) | 0.295 | 0.327 / 0.239 / 0.205 | **76.66 % (kill rule < 76.8)** | 6.7 % | 96.5 % (back) | 4.221 / 4.272 |
| 2 | s5e-02-v2-ppo | PPO on drill v2 with sim-to-real on (D-102/D-103); Stage 5E PPO settings (gamma 0.995, 50-update critic warm-up) | s5d-01-rally/model_1800 (residual around run 18) | model_2600 (wall cap at 2,661) | **0.553** [0.548, 0.558] | 0.624 / 0.493 / 0.277 | **26.9 % (kill rule); 47.7 % with latency (start: 42.2 %)** | 4.0 % | 90.4 % (back-right) | 4.015 / 4.039 |
| 3 | s5e-03-v2-mixlat | run 2 with mixed training latency: 0-40 ms observations, 0-20 ms commands, both including zero (D-104, user) | s5d-01-rally/model_1800 | model_2700 (wall cap) | **0.589** [0.584, 0.594] | 0.682 / 0.511 / 0.248 | **41.6 % (kill rule)** | 3.9 % | **69.6 % (back-right; kill rule)** | **3.844 / 3.862** |
| 4 | s5e-04-v2-eplat | run 3 with per-episode latency: half the episodes clean, half delayed (D-105, user) | s5d-01-rally/model_1800 | model_2799 (iteration cap) | 0.550 [0.545, 0.555] | 0.622 / 0.476 / 0.291 | **53.4 % (kill rule)** | 4.6 % | **71.9 % (back; kill rule)** | 4.008 / 4.034 |

## Notes
- **Run 0 diagnosis: latency, not the drill** (dev seed 4200398; 256 robots, 30 s rallies; Stage 5D run 1).

  | Setting on drill v2 | Per-shot p |
  |---|---|
  | all sim-to-real off, no spot | 0.72 (Stage 5D's rally evaluation: 0.77) |
  | all off, noisy planner spot | 0.69 |
  | ball-state noise only | 0.71 |
  | ball observations 20-40 ms late only | 0.51 |
  | joint commands 0-20 ms late only | 0.49 |
  | everything on (the frozen evaluation) | 0.31 |

  - **Noise:** harmless.
  - **Delays:** each costs about 20 points, and together about 40. No executor or controller was ever trained with delays.
  - **Concern:** the H1 motion controller, which turns latents into joint targets and keeps the balance, is frozen and was trained without command delay. Executor PPO under delay can relearn the hitting timing, but it may not be able to repair the controller's balance under delay. If p stays low, a controller retrain with delays (H0 -> H1) belongs to the D-097 rebuild decision.
  - **Gate:** the gate stays measured with sim-to-real on, as frozen (D-101).
- **Rally-mode falls per episode:** the "falls per episode" field of a drill v2 job is about 1.0 for every executor, because a 90 s rally episode almost always ends in a fall. Stage 5D's rally evaluation shows the same. Court falls for the gate come from the court drill (24 s episodes) of the Stage 5C battery, as in Stage 5D.
- **The new style reference scores Stage 5D run 1 higher (worse), 4.258 against 4.214 on the old one.**
  - **Why:** the old reference was drawn by frame count and was about 70 % LAFAN1 locomotion (279k of 405k frames). The frozen new shares give 25 % LAFAN1 and 25 % 100STYLE footwork, so fewer locomotion poses in all.
  - D-097 called the new reference a partial loosening, but for this executor it is stricter.
  - Both scores are reported, and the gate uses the new one (D-098).
- **Footwork check (step 3, D-097): passed.** latent-07 tracks every 4 s window of the 100STYLE training clips: 57/57 (FW 20, BW 22, SW 15), with no falls. It tracks tennis-v5 strokes at 93.5 % (dev seed 4200399, `stage5e-footwork-check-latent07.json`). By the D-097 rule (>= 90 %), style uses a discriminator reward on these clips, wrists excluded; no H0 -> H1 retrain for style. The separate latency risk to the controller (D-102) is not tested by this check.
- **Run 1 (consolidation) is killed:** court main metric 76.66 % < 76.8 %.
  - The copy lost rally skill on the old Stage 5D rally evaluation: P(rally >= 10) 10.2 % -> 5.5 %, and per-shot p on drill v2 0.306 -> 0.295.
  - It counts as plateau strike 1 (D-097/D-100: killed runs count).
  - Run 2 therefore continues the unconsolidated Stage 5D run 1 residual (D-103).
- **Run 2: killed, not a strike** (D-104, user). It is latency-specialised: court drill 47.7 % with latency (start point 42.2 %) but 26.9 % without it (start point 78.9 %).
  - **Gains:** drill v2 p 0.306 -> 0.553; drill v2 falls per feed 6.2 -> 3.2 %; style 4.214 -> 4.015 (old reference) and 4.258 -> 4.039 (new).
  - **Spot:** not used; p is the same with the noisy spot and without one.
  - **Next:** run 3 trains with mixed latency (0 ms included).
- **Run 3: killed** (court main 41.6 % < 76.8 %; arrival 69.6 % < 90 %). It is plateau strike 2 (runs 1 and 3); one more ends the stage.
  - **Drill v2:** best so far. p 0.589 (no spot 0.573), P(rally >= 5) 9.1 %, P(rally >= 10) 1.1 %.
  - **Style:** best of any executor. 3.844 on the old reference, 3.862 on the new one (gate 3.86).
  - **Retention:** the no-latency court drill (41.6 %), the move drill (arrival 69.6-91.8 %) and the Stage 5D rally evaluation (P(rally >= 10) 0.02 %) all fell, with mixed latency in training.
- **Run 4: killed** (court 53.4 % < 76.8 %; arrival 71.9 % back < 90 %). Strike 3, so Stage 5E ends under the plateau rule (D-106).
  - **What half-clean episodes helped:** the no-delay court drill (41.6 -> 53.4 %) and arrival in most directions (94-100 %, except back 71.9 % and back-right 81.2 %).
  - **What they cost:** drill v2 p fell to 0.550 (run 3: 0.589), and style returned to 4.008 / 4.034.
- **Final (D-106):** candidate run 3 ("best drill v2, failed kill rules") against run 22; `scripts/h5e_final.sh`.
