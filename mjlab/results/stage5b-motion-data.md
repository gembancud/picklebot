# Stage 5b — Human motion data for G1 + paddle (AMP / tracking priors)

Research-only survey, 2026-10-07. Nothing was downloaded, installed or trained. Web pages, READMEs, licence
files and GitHub/Hugging Face API metadata were read; local mjlab 1.6.0 source in WSL
(`/home/gem/envs/picklebot-mj/.../mjlab`) was read. Anything not confirmed from a primary source is marked
**unverified**.

## 1. Summary and recommendation

**No pickleball motion dataset exists** (no hit in searches). Usable racket-stroke mocap that is openly licensed is
scarce; the best fit is a small tennis BVH set (Tennis-MoCap, CC BY-SA 3.0) that includes **forehand/backhand
volleys** — the closest analogue to compact dinks/volleys. Generic balanced locomotion is easy (LAFAN1 already
retargeted to G1). Pickleball-specific footwork (split-step, shuffle, crossover, kitchen-line recovery) is **not
present as labelled clips in any open dataset found**; the realistic route is filming it yourself and running
video → SMPL-X → G1 (GVHMR + GMR), which is exactly how HITTER (G1 table tennis) and AdaPT (G1 tennis) got their
stroke references.

Recommended starting set (phase A, no body-model registration needed):

| # | Item to approve for download | Source URL | Size | Licence | Use |
|---|---|---|---|---|---|
| A1 | Tennis-MoCap BVH (100 files, 17 players x 6 strokes) | https://github.com/jdpulgarin/Tennis-MoCap | ~209 MB (sum of `data/` per GitHub API) | CC BY-SA 3.0 (commercial OK, attribution, share-alike on distributed derivatives) | Stroke references: forehand, backhand, forehand volley, backhand volley, serve, smash |
| A2 | LAFAN1 retargeted to G1, `g1/*.csv` only (40 files) | https://huggingface.co/datasets/unitreerobotics/LAFAN1_Retargeting_Dataset (official; returned HTTP 401 to anonymous API/raw requests today — may now need an HF login; **unverified**) — mirror: https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset | ~90 MB (G1 folder, mirror) | Derived from LAFAN1 = CC BY-NC-ND 4.0 → treat as **non-commercial research only, do not redistribute**; Unitree card states no separate licence (**unverified**) | Balanced locomotion / AMP style set (walk1-4, run1-2, sprint1, jumps1). Already in the exact CSV layout mjlab's `csv_to_npz.py` reads |
| A3 | GMR retargeter (git clone + pip deps) | https://github.com/YanjieZe/GMR | repo ~276 MB per GitHub API (mostly robot meshes/videos) + Python deps (mujoco, mink, etc.; **size unverified**) | MIT | Retarget A1 BVH (and later video output) to G1 29-DoF; exports BeyondMimic-style CSV (`scripts/batch_gmr_pkl_to_csv.py`) |

Phase B (only if phase A is insufficient for footwork; needs separate approval because of non-commercial licences
and registration):

| # | Item | Source | Size | Licence |
|---|---|---|---|---|
| B1 | GVHMR code + checkpoints (+ ViTPose/YOLO/SimpleVO weights it fetches) | https://github.com/zju3dv/GVHMR | code ~10 MB; checkpoints **several GB, unverified** | Code: "educational, research and non-profit purposes only", derivatives must be open-source, no commercial use |
| B2 | SMPL-X model files (`SMPLX_{NEUTRAL,MALE,FEMALE}`) and SMPL (needed by GVHMR) | https://smpl-x.is.tue.mpg.de , https://smpl.is.tue.mpg.de | ~hundreds of MB (**unverified**) | Registration required; non-commercial research only; no redistribution of model; commercial via Meshcapade |
| B3 | Self-recorded or licensed pickleball footwork/stroke videos (1 person, static camera, full body in frame) | user | small | Footage rights: user's own footage is fine; broadcast/YouTube footage is copyrighted — vid2player3d could not release models trained on broadcast data "due to license issues" |

Optional, lower priority (each needs its own approval): AdaPT repo (Apache-2.0; contains 2 G1 serve clips already
in mjlab `.npz` format, ~0.55 MB each, plus a racket-in-hand G1 MJCF and a GMR-pkl→mjlab-npz converter — a working
reference for exactly our pipeline): https://github.com/noitom-robotics/AdaPT (~77 MB repo). LATENT G1 tennis subset
(Google Drive, size unverified) has **no licence file** → all rights reserved by default; do not use without
asking the authors.

Estimated phase-A download: **~300 MB data + ~280 MB GMR repo + its Python deps**.

Suggested use: (1) AMP style reward from LAFAN1-G1 walk/run clips + retargeted Tennis-MoCap strokes (two
discriminators or one with stroke clips weighted), or (2) BeyondMimic-style tracking teacher per stroke clip, then
distil. HITTER used (2) restricted to bodies above the pelvis for swings while leaving footwork to the task reward —
a sensible first step that avoids needing footwork clips at all.

## 2. Datasets

| Dataset | Racket/footwork content | Format / skeleton | Size | Licence | G1 version exists? |
|---|---|---|---|---|---|
| **Tennis-MoCap** (Pulgarin-Giraldo et al., Univ. Caldas) | 17 players (5 high-perf, 12 regular); serve, smash, forehand, backhand, forehand volley, backhand volley; repeated strokes in ~30 s series (sample file: 2999 frames @100 Hz). `labels.csv` has 106 rows. No racket marker | BVH, OptiTrack Arena, 18 joints (Hips, single Chest, Neck, Head, Collar/Shoulder/Elbow/Wrist, Hip/Knee/Ankle; no toes/hands) | ~209 MB, 100 files | CC BY-SA 3.0 Unported | No. GMR does not ship a mapping for Arena BVH → needs a small custom IK config (LAFAN1-BVH config is the template) |
| **LAFAN1** (Ubisoft) | 77 seqs, 4.6 h, 5 subjects, 30 fps: walk, run, sprint, jumps, dance, fight, fightAndSports, push/stumble, fall-get-up. No racket strokes; walk clips contain direction changes (sidesteps/backwards **unverified**) | BVH | raw zip size unverified | CC BY-NC-ND 4.0 | Yes: Unitree retarget (CSV, 30 fps, G1 29-DoF, 40 G1 files); ember-lab-berkeley/LAFAN-G1 (IsaacLab-AMP npz, 40 files, ~475 MB, card says CC-BY-4.0 — conflicts with upstream ND/NC, treat as NC) |
| **AMASS** (incl. CMU, KIT, BMLmovi …) | Large general mocap. CMU keyword search: **0 hits** for tennis/racket/racquet/badminton; "swing" hits are playground/golf. CMU has sidestep (18 hits), walk backward (32), basketball (38), lunge (4), jumping jacks (11). HumanML3D text mentions tennis motions inside AMASS (count/source **unverified**) | SMPL-H / SMPL-X npz | full AMASS tens of GB (**unverified**) | AMASS: non-commercial research only, no redistribution, registration. Raw CMU: "free for research… may include in commercially-sold products, but may not resell this data" | GMR/ProtoMotions retarget AMASS SMPL-X → G1. Third-party G1 AMASS dumps exist (e.g. openhe/g1-retargeted-motions) but licence follows AMASS |
| **HumanML3D** | 14,616 clips, 28.6 h, text labels; motions are AMASS + HumanAct12 | Joint features (needs AMASS to rebuild) | small labels | Labels MIT-ish; motions = AMASS terms (**unverified**) | Only useful as a text index into AMASS |
| **Motion-X / Motion-X++** | 81K/120K seqs incl. HAA500 and online video subsets; HAA500 likely includes tennis/badminton action classes (**unverified**) | SMPL-X npy, 30 fps | large | Non-commercial, request form; per-subset licences | No |
| **BONES-SEED** (Bones Studio) | 142K motions (288 h, 120 fps, Vicon), "Sport"/"Sports" categories ~4K motions each; racket content **unverified** (website says everyday/locomotion focus) | SOMA BVH + **Unitree G1 CSV** | 758 GB total repo storage | Gated; academic non-commercial or startups < US$1M revenue; no redistribution; mandatory attribution | Yes (G1 CSV supplied). Best source of varied generic footwork if licence fits |
| **AdaPT** (Huang et al. 2026, built on mjlab) | Paper: 21.5 h tennis (3 pros from broadcast via GVHMR + 219 min/2,987-clip mocap "Mr. Black"). **Released: only 2 serve clips** | mjlab tracking `.npz` | ~1.1 MB | Repo Apache-2.0 (data provenance not separately stated) | Yes (G1 + racket MJCF) |
| **LATENT** (Tsinghua/Galbot, arXiv 2603.12686) | G1 tennis; "small subset" of mocap tennis fragments released | G1 `.npz` (OpenTrack/Brax layout, not mjlab) | unverified | **No licence** (GitHub reports none) | Yes |
| **Vid2Player3D** (Zhang et al. SIGGRAPH 2023) | Broadcast-derived tennis motion; code released, motion data and trained models **not released** ("license issues") | SMPL | — | code NOASSERTION | No |
| **THETIS** | 8,734 Kinect clips, 55 players, 12 tennis shots incl. volleys, serves, smash | RGB/depth video + Kinect v1 skeleton (noisy, ~20 joints) | unverified | "Freely available for research" | No; quality too low for physics priors |
| **CalTennis** (arXiv 2606.20542) | 51 h multi-view (2-6 cam, 60 Hz) tennis video, 40 players; no SMPL GT | video | large | CC BY 4.0 per arXiv page; release link **unverified** | No — but licensed footage for GVHMR |
| AthletePose3D / SportsPose | Athletics/skating; SportsPose has a tennis activity (marker-less 3D keypoints) | 3D keypoints | — | AthletePose3D CC BY-NC-SA 4.0; SportsPose **unverified** | No |
| TTSwing, badminton (arXiv 2602.08370), OmniRetarget, PHUMA | TTSwing = IMU only; badminton mocap not released (**unverified**); OmniRetarget (MIT, G1 object/terrain); PHUMA (CC BY 4.0, 73 h G1 locomotion) | — | — | as stated | OmniRetarget/PHUMA are G1-native generic locomotion alternatives |

## 3. Video-to-motion tools

| Tool | Code licence | Body model needed | GPU / deps | Output | Notes |
|---|---|---|---|---|---|
| **GVHMR** (SIGGRAPH Asia 24) | Custom: educational/research/non-profit only; derivatives open-source; commercial by email | SMPL + SMPL-X (registration, non-commercial) | Inference on single consumer GPU (RTX 4070 should suffice, **unverified** VRAM); SimpleVO default, DPVO optional, `-s` for static camera | `hmr4d_results.pt` (SMPL-X params, world-grounded, gravity-aligned) | GMR has `scripts/gvhmr_to_robot.py`; its demo video is literally `tennis.mp4`. Used by HITTER and AdaPT |
| WHAM | MIT | SMPL (registration) | ViTPose + DPVO/DROID-SLAM | SMPL world-frame | Older; needs SMPL→SMPL-X conversion for GMR |
| TRAM | MIT | SMPL | Masked DROID-SLAM (compile), heavier | SMPL world-frame | Good for moving cameras |
| 4DHumans / HMR2.0 | MIT | SMPL | light | per-frame camera-frame SMPL (no world trajectory) | Not enough for footwork (root drift) |
| SLAHMR | MIT | SMPL-H | optimisation, slow | world SMPL | Superseded |

All share the SMPL-family constraint: model files are non-commercial; outputs derived from them carry that
restriction in practice (**licence interpretation unverified — ask Meshcapade for commercial**). Footage: own or
explicitly licensed video only; broadcast footage is copyrighted.

## 4. Retargeting tools to G1

| Tool | Licence | Inputs | G1 out of box | Output | Paddle handling |
|---|---|---|---|---|---|
| **GMR** (YanjieZe) | MIT | SMPL-X (AMASS, OMOMO, GVHMR), BVH (LAFAN1, Nokov, Xsens), FBX (OptiTrack), PICO | Yes: `unitree_g1` (29 DoF), `unitree_g1_with_hands` | pkl (root pos/rot, dof_pos, link poses) → CSV for BeyondMimic via `batch_gmr_pkl_to_csv.py` | None built in. AdaPT applied random wrist perturbations during retargeting; racket then rigidly mounted on `right_wrist_yaw_link` |
| BeyondMimic / whole_body_tracking (HybridRobotics) | MIT | Unitree-style CSV (30 fps) | Yes | npz via `csv_to_npz.py` (same as mjlab's) | n/a |
| ProtoMotions v3 (NVlabs) | Apache-2.0 | SMPL/SMPL-X (AMASS), BONES-SEED G1 CSV | Yes (PyRoki retargeter) | own motion lib | n/a; also has AMP/ASE implementations (IsaacLab/Genesis/Newton, not mjlab) |
| PHC scripts | BSD-3-Clause-Clear (+asset licences) | AMASS SMPL | G1 fitting scripts exist in forks (**unverified** upstream) | pkl | n/a |
| Unitree LAFAN retarget | data only; code not released (**unverified**) | — | G1/H1/H1-2 | CSV | n/a |
| AdaPT `motionio/gmr_pkl.py` | Apache-2.0 | GMR pkl | G1 + racket MJCF | mjlab tracking npz | Racket mesh + cylinder proxy + `racket_point` site as children of `right_wrist_yaw_link` |

Recommended paddle treatment: retarget body only (paddle not in the human data), keep the paddle as a fixed child of
`right_wrist_yaw_link` (as `picklebot_mj/g1_paddle.py` already does), and either (a) exclude the wrist from the
style/tracking terms and let the task reward set paddle-face orientation, or (b) post-process each stroke clip so
the paddle face points along the human's racket-face direction at contact (human racket pose is not in Tennis-MoCap;
approximate from forearm). HITTER tracked only bodies above the pelvis and let goal rewards place the racket.

## 5. mjlab tracking task input format (read from local mjlab 1.6.0)

- Task `Mjlab-Tracking-Flat-Unitree-G1` (+ `-No-State-Estimation`), `mjlab/tasks/tracking/config/g1/`.
- **Motion file = one `.npz`** loaded by `MotionLoader` (`tasks/tracking/mdp/commands.py`) with keys
  `joint_pos (T, n_joints)`, `joint_vel (T, n_joints)`, `body_pos_w (T, n_bodies, 3)`, `body_quat_w (T, n_bodies, 4, wxyz)`,
  `body_lin_vel_w`, `body_ang_vel_w (T, n_bodies, 3)`; `fps` is stored but not read. Arrays cover **all robot bodies
  in model order**; the command then selects `body_names` via `robot.find_bodies`. Frame rate must equal env step
  rate: sim dt 0.005 x decimation 4 = **50 Hz**.
- Tracked bodies: pelvis, hip_roll, knee, ankle_roll (L/R), torso_link (anchor), shoulder_roll, elbow, wrist_yaw (L/R).
- Passing it: `train ... --env.commands.motion.motion-file /path/motion.npz` (local) or `--registry-name org/motions/name`
  (W&B artifact). Single clip per run; `sampling_mode` adaptive/uniform/start over time bins. No multi-clip library.
- Converter: `mjlab/scripts/csv_to_npz.py` (BeyondMimic port). Input CSV, no header, one row per frame:
  `x y z qx qy qz qw` (root, **xyzw**) + 29 joint angles in Unitree order (left leg 6, right leg 6, waist yaw/roll/pitch,
  left arm 7, right arm 7) — identical to the Unitree LAFAN1 CSV and GMR's CSV export. Default `--input-fps 30
  --output-fps 50`; replays through FK on the stock G1 scene. **Caveats:** it always saves to `/tmp/motion.npz` and
  then uploads to W&B unconditionally (needs a small local patch or wandb offline); it uses the stock G1 (no paddle),
  so if the paddle body changes body indexing, regenerate with the paddle scene (paddle as last child of the right
  wrist probably appends at the end — **unverified**).
- **AMP is not available locally**: installed rsl_rl 5.4.2 has only `ppo.py` and `distillation.py`; no discriminator in
  mjlab. Options: gbionics/amp-rsl-rl (BSD-3), Renforce-Dynamics/beyondAMP (has an mjlab backend; no licence file
  reported), several `AMP_mjlab` G1 repos (no licence; reference only).

## 6. Feasibility and risks

- **Joint limits (mjlab g1.xml):** waist roll and pitch only ±0.52 rad (±30°); waist yaw ±150°. Human strokes use large
  trunk rotation (fine) but deep side-bend/forward flexion on low volleys will saturate → expect knee/hip to absorb it.
  Elbow −60°…+120° (no hyperextension). Wrist roll ±113°, pitch/yaw ±92°. Ankle roll ±15°, ankle pitch −50°/+30°:
  crossover steps and wide lateral lunges will be clipped; hip roll adduction limited to 30°, which restricts crossover
  stepping.
- **Scale:** G1 ~1.3 m vs ~1.75 m humans (~0.75). GMR scales by height; stride length, split-step hop and reach shrink
  accordingly — timing (Hz) will not match human footwork speed at the same court distances.
- **Dynamics:** retargets are kinematic only (Unitree states its LAFAN retarget ignores dynamics/actuator limits);
  fast forehands may exceed G1 joint velocity/torque — expect tracking error at contact; AdaPT/HITTER report needing
  timing/speed adaptation.
- **Tennis ≠ pickleball:** tennis groundstrokes are bigger, two-handed backhands map poorly to a one-paddle G1;
  volleys in Tennis-MoCap are the best dink/volley proxy. Serve: pickleball is underhand — tennis serves/smashes are
  only useful as overhead references.
- **Data quality:** Tennis-MoCap has a single spine joint and no foot/toe or racket markers → torso twist and foot
  orientation are coarse; check for left-handed players and mirror where needed. Video-derived motion (GVHMR) has foot
  skate/jitter → filter and rely on physics tracking to clean it.
- **Licences:** LAFAN1-derived and AMASS/SMPL-derived data are non-commercial; keep them out of any commercial
  deliverable and never commit them to a public repo. Tennis-MoCap (CC BY-SA) and own footage are the only fully
  redistributable stroke sources found.
- **Prior art on this exact setup:** HITTER (G1 table tennis): 2 clips (forehand/backhand) from video via GVHMR → GMR,
  30→50 Hz, BeyondMimic-style tracking reward on bodies above pelvis, racket on right wrist via 3D-printed connector,
  29 DoF @50 Hz. AdaPT (G1 tennis, mjlab): GVHMR+GMR, wrist perturbations, 23-inch racket on wrist mount at 25° offset.
  Badminton (arXiv 2602.08370, PM01 robot): mocap incl. 6-DoF racket, AMP in a final stage. TaskNPoint (arXiv
  2606.26215): G1 backhand from one human video demo per skill.

## 7. Sources

- mjlab local: `mjlab/tasks/tracking/mdp/commands.py`, `config/g1/env_cfgs.py`, `tracking_env_cfg.py`, `scripts/csv_to_npz.py`, `scripts/train.py`, `asset_zoo/robots/unitree_g1/xmls/g1.xml`
- https://github.com/jdpulgarin/Tennis-MoCap
- https://huggingface.co/datasets/unitreerobotics/LAFAN1_Retargeting_Dataset ; https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset ; https://huggingface.co/datasets/ember-lab-berkeley/LAFAN-G1
- https://github.com/ubisoft/ubisoft-laforge-animation-dataset
- https://amass.is.tue.mpg.de/license.html ; http://mocap.cs.cmu.edu/ (search + FAQ) ; https://github.com/EricGuo5513/HumanML3D ; https://github.com/IDEA-Research/Motion-X
- https://huggingface.co/datasets/bones-studio/seed ; https://bones.studio/info/seed-license
- https://github.com/noitom-robotics/AdaPT ; https://arxiv.org/abs/2608.20087 ; https://humanoidtennis.github.io/AdaPT
- https://github.com/GalaxyGeneralRobotics/LATENT ; https://arxiv.org/abs/2603.12686
- https://research.nvidia.com/labs/toronto-ai/vid2player3d ; https://github.com/nv-tlabs/vid2player3d
- https://arxiv.org/abs/2508.21043 (HITTER) ; https://arxiv.org/html/2602.08370 (badminton) ; https://arxiv.org/abs/2606.26215 (TaskNPoint) ; https://arxiv.org/abs/2606.20542 (CalTennis)
- THETIS: https://openaccess.thecvf.com/content_cvpr_workshops_2013/W08/papers/Gourgari_THETIS_Three_Dimensional_2013_CVPR_paper.pdf ; AthletePose3D: https://github.com/calvinyeungck/AthletePose3D
- https://huggingface.co/datasets/omniretarget/OmniRetarget_Dataset ; https://arxiv.org/abs/2510.26236 (PHUMA)
- https://github.com/YanjieZe/GMR ; https://github.com/HybridRobotics/whole_body_tracking ; https://github.com/NVlabs/ProtoMotions ; https://github.com/ZhengyiLuo/PHC
- https://github.com/zju3dv/GVHMR ; https://github.com/yohanshin/WHAM ; https://github.com/yufu-wang/tram ; https://github.com/shubham-goel/4D-Humans ; https://github.com/vye16/slahmr ; https://smpl-x.is.tue.mpg.de/modellicense.html
- https://github.com/gbionics/amp-rsl-rl ; https://github.com/Renforce-Dynamics/beyondAMP ; https://github.com/ccrpRepo/AMP_mjlab
