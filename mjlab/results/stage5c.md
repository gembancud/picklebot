# Stage 5C: full-court coverage (D-069, D-075)

Starting executor: `h4-25b-more/model_27700` (the Stage 5B gate). Budget: 30 training runs.

## Footwork: the agility walker
**Task** `Picklebot-Latent-Reach-Agility-G1`: the H3 E2 reach task with root targets 1-3 m away, uniform in angle and distance, one per 2 s (H3: within 1 m), plus paddle targets as before.

**Baseline** (reach-06, `stage5b-h4-reach-direction-diag-1p5m.json`): within 25 cm of a 1.5 m target in 2 s, forward 28 %, right 30 %, left 0 %, back 0 %.

**Criterion** (D-075): if after the walker runs left or back still reach less than 75 % of the mean of right and forward at 1.5 m, retrain the controller with mirrored LAFAN1 locomotion.

**Known quirk:** a reach command resampled at an episode reset reads the robot's pre-reset position, so the first 2 s window of an episode can have an offset target. This has been so since H3; it affects training only, since evaluations clear the tally after the reset.

| # | Run | Change (written before launch) | From | Endpoint | Left / right / forward / back within 25 cm at 1.5 m |
|---|---|---|---|---|---|
| 1 | s5c-01-agility | agility walker task (1-3 m targets) | reach-06/model_34700 | | |

## Court-wide drill (D-076; `Picklebot-Latent-Court-G1`)
- **Zones:** back / mid / front by the pelvis x at feed time. Court-wide start and recovery spots.
- **Six new families:** drop, lob, cross forehand and backhand, volley forehand and backhand. Each is fed only where valid.
- **Offline feed check** (`scripts/tune_court_feeds.py`, `artifacts/eval/court-feeds-v1.json`, 512 feeds per cell):
  - every Stage 4 family is valid from every zone (travel <= 0.5 m);
  - drop asks for 1.3-2.4 m forward (back/mid); lob for 1.1-2.0 m back (mid/front);
  - cross asks for 2.2-3.2 m sideways at up to 1.5 m/s;
  - volleys are 100 % hittable before the bounce;
  - drop and reach short from the front land beyond the net (excluded).
- **Kitchen rules from the feet;** volleys in rally phase; pre-bounce volley hints.
- **Zone-conditioned learning-progress curriculum.**

## Evaluation (`scripts/h5c_eval.sh`, `scripts/h5c_summary.py`)
1. **Court drill:** every family, court-wide starts, random court-wide recovery spots, no hint, 2048 envs x 24 s. Gives per (zone x family) legal, recovery and falls. The pooled legal rate is the **main metric**.
2. **Move-to-spot drill:** arrival per direction (8 sectors).
3. **Regression on the Stage 5B drill**, with exactly its 14 families (`--families drill5b`; "every" now also contains the court families). Compared with h4-25b's paired final evaluation.
4. **Style score.**

## Baseline: h4-25b on the court drill (dev seeds 4200600-603; `stage5c-baseline-h4-25b-*.json`)
- **Main metric 52.0 %.** 15 of 55 (zone x family) cells reach 75 %.
  - Stage 4 families: 73-85 % from the back and mid zones, 44-70 % from the front.
  - Drop 11-32 %, cross 14-40 %, lob 0 %, volleys 0-0.7 %, reach deep 0-45 %.
- **Move-to-spot arrival 0 % in every direction. Recovery 1.53 m. Falls 10.3 %. Style 3.88.**
- **Stage 5B regression check** (h4-25b against itself): within -2.6..+1.0 points, so the check is sound.

## Court-wide executor runs (`Picklebot-Latent-Court-G1`)
| # | Run | Change (written before launch) | From | Endpoint | Main metric (court pooled) | Style |
|---|---|---|---|---|---|---|
| 2 | s5c-02-court | court-wide drill (D-076) with the zone-conditioned curriculum | h4-25b/model_27700 | model_28400 (see note) | **71.3 %** (52.0 baseline); 37/55 cells | 3.817 |
| 4 | s5c-04-volley | volley feeds re-aimed to waist-to-chest height (D-078); nothing else | s5c-02/model_28400 | last checkpoint before the cap | | |

### Run 2 evaluation (s5c-02/model_28400, dev seeds 4200620-623; `stage5c-s5c-02-*.json`)
- **Main metric 71.3 %** (h4-25b 52.0 %). 37 of 55 cells reach 75 %.
  - Stage 4 and reach_forehand/backhand families: 84-99 % in every zone.
  - Below 75 %: cross_backhand 40-47 %, cross_forehand 61-66 %, drop 44-61 %, reach_deep 57 % (back) / 9 % (mid) / 1 % (front), reach_short 65 % (mid), lob 2-4 %, volleys 0 %.
- **Move-to-spot arrival about 0 % in every direction.** Recovery 1.58 m. Falls 4.2 %. **Style 3.817.**
- **Stage 5B regression:** within 5 points except topspin -7.2, wide_forehand -6.4 and reach_deep -23.9.
- **Volley diagnosis** (`volley_diag.sh`, seed 4200630, with hint):
  - Contact: 16 % forehand, 1 % backhand. Legal: 0.6 %.
  - The robot lets the ball pass and swings after the bounce (mean contact height 0.38 m).
  - The D-076 volley feeds pass the pelvis knee-high (0.44-0.58 m in the mid zone): see D-078.
- **What the walker caps:** lobs and reach_deep from the mid/front zones (balls going behind the robot), move-to-spot arrival and recovery all need the backward and leftward footwork the controller lacks (D-077).

## Agility walker result: controller limit (D-077)
- **s5c-01-agility -> model_37300** (dev seed 4200610). Within 25 cm at 1.5 m in 2 s: forward 32 %, right 27 %, **left 0.1 %, back 0 %**.
  - Distance covered in 2 s: about 1.2 / 1.1 / 0.55 / 0.5 m.
  - At 2.5 m: 0 % in every direction.
  - The training curve was flat for the whole run.
- **D-075 criterion met:** retrain the controller.
- **Mirrored LAFAN1** (`scripts/motion/mirror_g1_csv.py`, `tests/test_mirror_g1.py`): 17 clips, 211,996 frames, `lafan-g1-mirror.npz`. Checked through forward kinematics: every left/right body pair mirrors the original within 1e-5 m (`artifacts/eval/check_mirror.py`).
- **Motion set** `tennis-lafan3.npz`: 90 tennis + 17 LAFAN1 + 17 mirrored clips, 549,350 frames. Envs sampled 50.5 / 24.2 / 25.3 % by source (task `Picklebot-Tracking-TennisLafan3-Huge-G1`).

## Controller retrain (D-077)
**H0 gate**, fixed now: per-stroke tennis within 3 points of H0 (H0: 93.2 %, every stroke type >= 89 %), LAFAN1 within 3 points of H0 (89.2 %), **mirrored LAFAN1 >= 86.2 %** (H0's LAFAN1 minus 3), falls <= 1 %. Scored with `scripts/motion/tracking_eval.py --per-stroke`, which now reports `by_source` and separate `lafanmirror_*` groups.

| # | Run | Change (written before launch) | From | Endpoint | Tennis / LAFAN1 / mirrored | Falls |
|---|---|---|---|---|---|---|
| 3 | s5c-03-h0mirror | ABORTED, not counted: launched alongside run 2, no learning iteration in 20 min (GPU contention); killed 17:38 | tracking-20-decay/model_60800 | - | - | - |
| 3 | s5c-03b-h0mirror | H0 continued on tennis + LAFAN1 + mirrored LAFAN1 (0.5/0.25/0.25), fixed lr 1e-5 as in tracking-20-decay; run alone | tracking-20-decay/model_60800 | model_63300 (fixed at launch: last checkpoint before the 7000 s cap at ~2.6 s/iter) | 94.0 / 88.7 / **84.9** | 0.84 % |
| 5 | s5c-05-h0mirror | continuation of run 3b (same data, lr, shares; seed 2): mirrored LAFAN1 is 1.3 points short | s5c-03b/model_63300 | model_65900 (fixed at launch) | 93.1-93.5 / 89.6-89.9 / 85.7-86.2; serve 84.0-85.7 | 0.66-0.69 % |
| 6 | s5c-06-h1mirror | **H1** latent distillation from run 3b's teacher on tennis-lafan3 (D-079); latent-07 settings | latent-07/latent_10651 | latent_12162 (cap) | 92.4 / 91.5; 87.9 / 87.8; **84.5 / 84.1** | 0.68-0.77 % |
| 7 | s5c-07-agility-m | agility walker (run 1's task) on the run-6 controller; only the controller changes | s5c-01-agility/model_37300 | model_40100 | 1.5 m within 25 cm: fwd 51 %, right 9 %, **left 0.4 %, back 0 %** | |
| 8 | s5c-08-agility-l3 | run 1's walker on latent-07 with the latent barrier lambda 1 -> 3 (D-080); nothing else | s5c-01-agility/model_37300 | model_40100 | 1.5 m within 25 cm: fwd 63 %, right 33 %, **left 0.4 %, back 0 %** | |
| 9 | s5c-09-agility-l3-fresh | run 8 without the warm start (fresh policy): the lineage from reach-06 never stepped left/back | none | model_2800 | 1.5 m within 25 cm: fwd 63 %, right 26 %, **left 0.2 %, back 0 %** | |
| 10 | s5c-10-h1footwork | **H1** on tennis-lafan4: + the walking teacher's footwork clips (D-081); teacher run 3b | latent-07/latent_10651 | latent_12135 (cap) | 91.1 / 91.0; 86.4 / 87.2; footwork 100 / 100 | 0.51-0.59 % |
| 11 | s5c-11-agility-f-l3 | run 9 (fresh walker, lambda 3) on the run-10 controller; only the controller changes | none | model_2800 (WSL shut down at 1:51:42; same iteration as run 9's endpoint) | 1.5 m within 25 cm: fwd 74 %, right 27 %, **left 0.5 %, back 0 %** | |
| 12 | s5c-12-kickstart | **kickstart** (D-082): walking teacher on move episodes + the starting executor on ball episodes, distilled through latent-07 at lambda 3 | s5c-02/model_28400 | model_29585 (cap) | **22.1 %**; 3/55 cells; **move arrival 76-99 % per direction** | **3.585** |
| 13 | s5c-13-court-l3 | PPO on the court drill at lambda 3 (task Picklebot-Latent-Court-L3-G1) from the kickstarted executor | s5c-12/model_29585 | **stopped after about 200 of an expected 1,000 iterations** (counted): falls 158-315 per logging interval, legal 0 | - | - |
| 14 | s5c-14-court-l3-std | run 13 with the latent action-noise std x 1/3 (`scripts/rescale_action_std.py`) | s5c-12/model_29585_std3 | model_30500 | **74.9 %**; 42/55 cells; **move arrival 0 %** | 3.868 |
| 15 | s5c-15-kickstart2 | kickstart (D-084): ball episodes copy run 14's latent exactly, move episodes copy the walking teacher; no PPO | s5c-14/model_30500 | model_31675 (cap) | **74.5 %**; 42/55 cells; **move arrival 46-97 %** | 3.872 |
| 16 | s5c-16-recover | run 15's kickstart + the walking teacher in the recovery phase of ball episodes (D-085) | s5c-15/model_31675 | model_32841 (cap) | **47.3 %**; 8/55 cells; move arrival 79-96 %; **falls 24 %** | 4.099 |
| 17 | s5c-17-court-l3-more | PPO continuation of run 14 (the hitting teacher), seed 2; nothing else | s5c-14/model_30500 | model_31400 | **80.4 %**; 42/55 cells; falls in every move episode | 4.016 |
| 18 | s5c-18-merge17 | run 15's kickstart recipe (D-084) with run 17 as the hitting teacher, from run 15 | s5c-15/model_31675 | checkpoint at the 6,900 s cap | | |

### Run notes
- **Run 2 endpoint** (fixed 17:40, before any evaluation): `--agent.max-iterations 3000` was mis-sized; at 12,288 envs an iteration takes about 6.7 s, so the 7000 s wall cap ends the run near iteration 28,500. The endpoint is **model_28400**, the last checkpoint certain to be written before the cap. Iterations 27,700-27,880 ran at about 1.7k steps/s while run 3 shared the GPU.
- **Run 3** was aborted and is not counted: started next to run 2, it printed no learning iteration in 20 minutes and cut run 2 to 1.7k steps/s. From now on, training runs go one at a time; the relaunch (s5c-03b) also restores tracking-20-decay's fixed learning rate of 1e-5, which the first launch had left out.
- **Run 3b H0 evaluation** (model_63300, dev seed 4200640, `stage5c-h0-03b.json`):
  - Tennis 94.0 % (H0 93.2 %). Per stroke against H0: forehand 96.0 (98.0), backhand 94.1 (90.7), forehand volley 96.9 (95.8), backhand volley 97.0 (95.0), smash 90.5 (89.5), serve 88.3 (89.0). Every stroke is within 3 points.
  - LAFAN1 88.7 % (H0 89.2 %).
  - **Mirrored LAFAN1 84.9 %, below the 86.2 % gate.** By clip type, against the originals: walk 93.0 (94.8), run 81.7 (84.3), sprint 78.7 (82.4), fight/sports 60.9 (76.2).
  - Falls 0.84 %.
  - **The H0 gate is not met yet**, so the run is chained (run 5).
- **H0 evaluation on a second seed** (4200642; `stage5c-h0-05b.json`, `-03b-b.json`, `-h0base.json`). Mirrored LAFAN1: original H0 83.4 %, run 3b 84.8 %, run 5 86.2 %.
  - Run 5's serve (84.0 / 85.7 %) is more than 3 points below H0's (89.7 %), and its smash fell to 87.4-87.8 %.
- **D-079:** the H0 chain stops at run 3b, with the mirrored target recorded as not met (84.9 / 84.8 % against 86.2 %). H1 is distilled from run 3b's teacher. Whether the controller gains left/back footwork is decided by the agility walker, measured as in run 1.
- **Run 6 H1 check** (latent_12162, encoder path, dev seeds 4200650 / 4200651; `stage5c-h1-06a/b.json`; latent-07 re-scored on 4200651 in `stage5c-h1-latent07.json`):

  | | Run 6 | latent-07 | Target |
  |---|---|---|---|
  | Tennis | 92.4 / 91.5 % | 93.4 % | within 3 points — **met** |
  | LAFAN1 | 87.9 / 87.8 % | 89.0 % | within 3 points — **met** |
  | Mirrored LAFAN1 | 84.5 / 84.1 % | 82.7 % | >= 84.9 % (LAFAN1 minus 3) — **missed by 0.4-0.8** |

  - Per stroke, serve fell to 81.3 / 82.0 % (latent-07 92.3 %) and smash to 84.2 / 82.0 % (89.5 %). Volleys and backhand improved.
  - Even latent-07 tracks mirrored walk (92.1 %) and run (81.2 %) through its encoder about as well as the originals. The encoder path does not test what the walker uses, though: the walker acts through the *prior* (z = mu_p + sigma_p tanh(a)), which never saw leftward or backward stepping states.
  - **The H1 check is not fully met.** As D-079 fixed, the agility walker decides (run 7).
- **Run 7** (dev seed 4200660): left and back did not improve on the mirrored-data controller (run 1: left 0.1 %, back 0 %). The training curve recovered from the controller swap and then stayed flat (root reward about 0.19, as in run 1).
- **Latent barrier check** (`scripts/motion/latent_barrier_check.py`, dev seed 4200661; `stage5c-barrier-*.json`).
  - In every clip group, on both controllers, the encoder's latent lies a median of 2.1-2.9 prior standard deviations from the prior mean in its farthest dimension (90th percentile 3.2-4.9).
  - At lambda = 1, under 3 % of steps fit inside the walker's reach in any group. At lambda = 3, 63-83 % do (mirrored fight/sports 39 %).
  - The limit is the latent action barrier, not the training data. **D-080:** keep latent-07 and test the walker at lambda = 3 (run 8).
- **Run 8** (dev seed 4200670): lambda 3 helped forward (63 % vs 32 %) and right (33 % vs 27 %). **Left (0.4 %) and back (0 %) are unchanged**, and at 2.5 m nothing is reached. The training curve was flat after recovering from the barrier change.
- **Reference point:** the flat joint-space walking teacher (`Picklebot-Teacher-Move-G1`, model_15900; `stage5-teacher-move.md`) reaches 98.95-100 % of move-drill spots (0.5-3 m) in every sector. The body can do the footwork; the latent route cannot yet.
- Run 9 asks whether the walker lineage is the obstacle: every walker so far descends from reach-06, which trained on targets within 1 m.
- **Run 9** (dev seed 4200680): trained from scratch, the walker settles in the same pattern, so the starting checkpoint was not the obstacle.
- **D-081: footwork data.** 128 x 30 s of the walking teacher's move-to-spot episodes recorded as motion clips (`scripts/motion/record_policy_clips.py`, training seed 11; `footwork-teacher.npz`, 191,872 frames).
  - Moving frames by direction: forward 37k, left 38k, right 36k, back 27k. LAFAN1 is 69 % forward.
  - Run 3b's H0 tracks every footwork window at 100 % (seed 4200690, `stage5c-h0-03b-lafan4.json`), so no H0 run is needed.
  - Motion set `tennis-lafan4.npz` (252 clips, 741,222 frames) is sampled 0.5 / 0.15 / 0.1 / 0.25 (tennis / LAFAN1 / mirrored / footwork).
- **Run 10 H1 check** (latent_12135; dev seeds 4200700 / 4200701; `stage5c-h1-10a/b.json`). Against latent-07 on tennis-lafan4 (seed 4200701, `stage5c-h1-latent07-lafan4.json`):
  - Tennis 91.1 / 91.0 % (93.5 %) and LAFAN1 86.4 / 87.2 % (89.1 %): both within 3 points.
  - Footwork 100 / 100 %. **The check is met.**
  - Serve 77.3 / 78.7 % (89.3 %) and smash 83.3 / 81.3 % (89.1 %) fall again, as in run 6. Serve is not part of any Stage 5C drill; smash will matter for lobs.
  - latent-07 also tracks the footwork windows at 100 % through its encoder. As with the mirrored clips, the question is the prior, which the walker tests.
- **Run 11** (dev seed 4200710): no left/back gain on the footwork controller either. That makes five walker runs, three controllers and two barriers with left <= 0.5 % and back 0 %.
- **Expressiveness floor** (`scripts/latent_reach_floor.py`; walking teacher, move-only, dev seed 4200720; `stage5c-floor-move-*.json`).
  - Best per-state fit of the walking teacher's leg actions (variance 0.389) through latent-07: 0.072 MSE at lambda 1 (59 % of latent commands saturated) and **0.027 at lambda 3 (26 % saturated)**.
  - The footwork controller does worse (0.099 / 0.061).
  - The footwork is inside latent-07's reach at lambda 3; PPO does not find it.
- **D-082:** kickstart the executor's footwork from the walking teacher through latent-07 at lambda 3 (`scripts/kickstart_h4.py`, `tests/test_kickstart_h4.py`), then PPO.
- **Run 12 evaluation** (model_29585, dev seeds 4200730-733, `stage5c-s5c-12-*.json`; Stage 5B check on `Picklebot-Latent-Drill3-Prior5-L3-G1`).
  - **Move-to-spot arrival, for the first time in any executor:** fwd 94.4, fwd-left 75.6, left 86.8, back-left 99.0, back 98.9, back-right 96.2, right 94.6, fwd-right 84.9 %. Every executor before scored 0 %.
  - **Style improved to 3.585** (run 2: 3.817).
  - **Hitting collapsed:** court main metric 22.1 % (run 2: 71.3 %); Stage 5B families 43-92 points below h4-25b; falls 4.7 %; recovery 1.58 m.
  - In training the ball-episode imitation error was small (0.002 joint MSE against 0.04 for footwork). But a return needs paddle timing to within centimetres, which joint-space imitation through a different barrier does not keep.
  - **Run 13:** PPO from this endpoint to win hitting back. The move-to-spot rewards stay in the task, so the footwork should hold.
- **Run 13:** the action-noise std inherited from lambda 1 (about 0.38) moves the latent 3x further at lambda 3. Falls rose to 158-315 per logging interval, and the run was stopped.
- **Run 14** (dev seeds 4200750-753):
  - Court main metric **74.9 %**, 42/55 cells (best so far). Stage 5B families within 5 points of h4-25b except backspin (-9.8) and reach_deep (-58).
  - **Move-to-spot arrival 0 %.** Style 3.868, recovery 1.68 m, falls 4.2 %.
  - Under PPO's action noise the robot never holds still long enough to "arrive", so nothing in training defended the footwork, and the prior penalty pulled the latent back.
- **Kickstart diagnostic** (`artifacts/eval/ks_diag.py`): on evaluation states run 12 matched its starting executor's joint targets (MSE 0.004), but its latent was off by a median 0.14 prior sigmas per dimension. Hence D-084's exact latent copy for hitting.
- **Run 15** (dev seeds 4200760-763), the **first executor with both skills**:
  - **Hitting:** court main metric 74.5 %, 42/55 cells.
  - **Footwork:** move-to-spot arrival fwd 88.5, fwd-left 45.5, left 67.1, back-left 95.0, back 96.5, back-right 95.2, right 92.4, fwd-right 82.7 %.
  - **Still failing:** recovery 1.68 m, falls 4.0 %, style 3.872; Stage 5B backspin -11.4 and reach_deep -58.
  - Volleys and lobs 0-1 %, reach_deep 0-28 %, cross_backhand 50-53 %.
  - Ball episodes copy run 14, which never walks back to the recovery spot, hence D-085.
- **Run 16** (dev seeds 4200770-773): **D-085's recovery phase failed.** Main metric 47.3 % (run 15: 74.5 %), falls 24 %, style 4.10.
  - Recovery (1.23 m vs 1.68 m) and move arrival (79-96 %) improved.
  - Switching teachers 0.2 s after contact leaves the robot walking when the next feed comes. The hitting teacher never handled that state, so the robot falls.
  - Run 15 stays the best two-skill executor.
- **Plateau count** (executor runs; main metric; best so far 74.9 %, run 14): run 15 (-0.4) and run 16 (-27.6) are the first two in a row under +1 point.
- **Run 17:** the most likely +1 point is more PPO on the hitting teacher. Run 14's legal-return reward was still rising at its cap (0.66 -> 0.73 over its last 600 iterations). The footwork can then be put back by kickstarting (run 15's recipe).
- **Run 17** (dev seeds 4200780-783): **main metric 80.4 % (+5.5 over run 14), so the plateau count resets.**
  - Lob 41-48 % (from 1-2 %), reach_deep 68 % (back) / 13-17 % (mid, front), cross_backhand 70-74 %.
  - Volleys still 0 % (contact 0 / 0.4 %). Style 4.016, falls 3.6 %.
  - Stage 5B families within 5 points of h4-25b except backspin (-15) and reach_deep (-19.5).
  - In move-only episodes it falls every time (robot fall rate 1.0 per episode), so PPO keeps no footwork. It serves as the hitting teacher for run 18.

