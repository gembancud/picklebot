# Stage 5b survey: CalTennis -> GVHMR -> GMR -> G1 footwork pilot

Web research only, done 2026-10-10. Nothing was downloaded, installed or run. **[V]** means I checked it on the linked page or API. **[U]** means I could not verify it, or it is my own estimate.

## 1. CalTennis (arXiv 2606.20542)
- Paper: https://arxiv.org/abs/2606.20542 (Demler, Xie, Werner, Szczuka, Perona; Caltech; 18 Jun 2026) [V]. Project page: https://ilonadem.github.io/caltennis-website/ (says code is "coming soon") [V].
- **Release location:** Hugging Face only. https://huggingface.co/datasets/demalenk/caltennis [V]. I found no Google Drive or GitHub release. There is also a preview Space, https://huggingface.co/spaces/demalenk/caltennis-preview-viewer. It was asleep when I checked, so I could not read its contents.
- **Licence:** the HF card and API give **`cc-by-nc-4.0`** [V]. The "CC BY 4.0" on arXiv is the licence of the *paper*. Treat the data as **CC BY-NC 4.0**: non-commercial use with attribution. That suits this project. The licence covers the videos, timestamps and calibration.
- **Access:** the API returns `gated: false, private: false` [V]. No login, request form or click-through is needed. Direct file URLs are `https://huggingface.co/datasets/demalenk/caltennis/resolve/main/<path>`.
- **Size and layout [V]:** about 104 GB stored (`usedStorage` 104,080,354,161 B). The card says about 120 GB. There are 20 session folders `MM_DD_YYYY_HH_MM_courtN/`, plus `camera_calibration/<session>/<video_id>/calib.json`, `metadata_mini.jsonl` and `metadata_mid.jsonl`. Each video has a sibling `<video_id>_timestamps.npy` (float64, one value per frame). `metadata_*.jsonl` rows look like `{video, timestamps, calibration, session_id, video_id}`. "mini" and "mid" are file lists, about 40 videos each.
- **Selective download:** yes, per file, with `hf_hub_download` or a plain HTTPS GET. There are no pre-cut clips. In the mini and mid sessions each camera file is one long recording, for example:
  - `01_23_2026_17_00_court2/...E_01...mp4`: 1.51 GB, about 80 min.
  - `01_28_2026_16_30_ath/..._X_1_...mp4`: 1.77 GB, about 39 min.

  Typical files are 1.0–1.8 GB [V].
  - **Exception, good for the pilot:** session `09_18_2025_16_15_court5` holds short clips of 22–209 MB (41 s to 6 min), each with a `calib.json` [V]. It is *not* in the mini or mid lists, so it may be an early recording session. Its content is [U].
- **Camera setup [V]:** consumer iPhones (main 1x lens) on tripods about 1.65 m high. There are 2–6 synchronized views per session, 60 Hz, 1920x1080 and face-blurred. The sample `calib.json` has a pinhole `K` (f ≈ 1606 px, cx,cy = 960,540), `R/t` (world↔camera) in a court frame, the camera centre (z ≈ 1.67 m) and a reprojection error of 3.7 px, with no distortion coefficients. Players are 13.4–16.7 m from the camera in 90% of frames. **At that range a player is only about 170–200 px tall** [U, computed from K]. That is small for HMR models.
- **3D / SMPL annotations: none in the release.** The HF tree has only videos, timestamps, calibration and paper assets [V]. The paper evaluates SMPL-X outputs from 5 models but does not publish them, and multi-view triangulation is "label-free" evaluation. So GVHMR (or a similar model) is **still required**. The calibration does let us re-anchor or triangulate the root (§3).
- **Content [V, from the paper and card]:** 40 players, collegiate to recreational, 51 h, 11.03 M frames. Unscripted practice and match play: serves, volleys, sprints, footwork drills, half- and full-court. Full body is mostly visible. Multiple people appear in frame. I did not verify per-session labels such as "drill" vs "match".
- **Benchmark (paper Table 2) [V], measured as cross-view disagreement:**

  | Model | Translation | PA-MPJPE | Foot velocity | Foot height | Stability |
  |---|---|---|---|---|---|
  | GVHMR | 3.59 m | 88 mm | 2.49 m/s | 60 mm | 21 mm |
  | WHAM | 2.66 m | 119 mm | 0.72 m/s (best) | — | — |
  | PromptHMR | 0.94 m (best) | 84 mm | 3.23 m/s | — | — |
  | TRAM | 2.34 m | — | 6.65 m/s | — | — |
  | GENMO | — | — | — | — | 16 mm (best) |

  The authors conclude "no single model dominates". Depth and translation, and foot contact, are the main failure modes for distant, fast tennis players.

## 2. GVHMR (https://github.com/zju3dv/GVHMR)
- **Code licence [V]:** custom licence for "educational, research and non-profit purposes only". Derivatives must stay open source and non-commercial. This is fine for this project.
- **Install [V]** (docs/INSTALL.md): `git clone`, then Python **3.10**, then `pip install -r requirements.txt && pip install -e .`.
  - requirements.txt pins `torch==2.3.0+cu121`, `torchvision==0.18.0+cu121`, `numpy==1.23.5`, `lightning==2.3.0`, `ultralytics==8.2.42`, `timm==0.9.12`, `smplx`, `chumpy` and `pycolmap`.
  - It also installs a **pytorch3d 0.7.6 wheel from dl.fbaipublicfiles.com (py310 / cu121 / pt230, Linux only)**.
  - The docs use conda, but a py3.10 venv in WSL2 should work [U].
  - The cu121 wheels support the RTX 4070 (sm_89).
  - DPVO (CUDA 12.1 toolkit plus Eigen build) is **optional**. It is not needed with `-s` (static camera). The default moving-camera path is SimpleVO (SIFT).
- **Checkpoints [V].** The official source is Google Drive folder `1eebJ13FUEXrKBawHpJroW0sNSxLjh9xD`. Sizes below are from the identical HF mirror `camenduru/GVHMR`:

  | File | Size |
  |---|---|
  | `gvhmr/gvhmr_siga24_release.ckpt` | 163.5 MB |
  | `hmr2/epoch=10-step=25000.ckpt` | 2,709 MB (HMR2.0a features; 4D-Humans, MIT) |
  | `vitpose/vitpose-h-multi-coco.pth` | 2,549 MB (ViTPose, Apache-2.0) |
  | `yolo/yolov8x.pt` | 136.9 MB (Ultralytics, **AGPL-3.0**) |
  | `dpvo/dpvo.pth` (skip) | 14.2 MB |

  **Inference total is about 5.56 GB.** The training data tarballs, including BEDLAM at 21 GB, are *not* needed.
- **Body models [V]:** `inputs/checkpoints/body_models/smplx/SMPLX_{NEUTRAL,MALE,FEMALE}.npz` and `.../smpl/SMPL_{GENDER}.pkl`. These come from https://smpl-x.is.tue.mpg.de and https://smpl.is.tue.mpg.de, and **you must register personally (email plus accept the licence)**. The licence is a single-user, non-transferable, free right for **non-commercial scientific research**. No redistribution is allowed (so files can't be shared from a colleague or committed to git), and the SMPL-X paper must be cited. Approximate sizes: SMPL-X v1.1 npz+pkl zip about 0.8 GB, SMPL v1.1.0 python zip about 0.25 GB [U].
  - GMR needs `SMPLX_NEUTRAL.pkl` in `GMR/assets/body_models/smplx/`, which may already be present. GMR's README notes that the `smplx` ext must be switched from npz to pkl if you use the pkl files.
- **GPU memory [U]:** I found no official figure. The weights are about 2.5 GB each for ViTPose-H and HMR2 ViT-H, fp32, run in batches of 16 at 256-px crops. **12 GB should be enough for short clips.**
  - ViTPose `get_batch` loads *all* cropped frames of the clip into RAM: about 0.8 MB per frame, so about 1.4 GB per 60 s at 30 fps [V code]. Never feed it a 40–80 min file. Cut 10–60 s clips first.
  - Give WSL2 at least 16 GB of RAM.
- **Speed [V]:** the paper reports 1430 frames on an RTX 4090 at 4.9 s YOLO + 20 s ViTPose + 10.1 s ViT features + 11 s DPVO, and **0.28 s for GVHMR itself**. A 4070 is roughly 2–2.5x slower [U]. That gives about 1–2 min per 30 s clip including mesh rendering.
- **Frame rate pitfall [V code]:** `demo.py` re-writes the input at `fps=30` *without dropping frames*. A 60 Hz CalTennis clip would therefore become 2x slow motion. **Resample to 30 fps first** (`ffmpeg -vf fps=30`). GMR also assumes 30 fps.
- **Static camera / multi-person [V code]:**
  - `-s` sets R_w2c = I and uses `pp_static_joint_cam`, which is right for CalTennis.
  - `--f_mm` sets focal length (default is a guess). For CalTennis, convert `K` (f ≈ 1606 px at 1920 w) to an equivalent of about 30 mm [U: check GVHMR's f_mm→px convention]. Alternatively, patch the demo to take K directly.
  - Tracking is single-person: `Tracker.get_one_track` uses YOLOv8x and picks the track with the **largest summed normalized bbox area**, which is usually the near player. To pick a specific player, either crop the clip spatially (then fix K/principal point) or patch the selection to use court position from the calibration.
- **Alternatives:**
  - WHAM (github.com/yohanshin/WHAM, MIT, needs SMPL registration): best foot-velocity score on CalTennis.
  - TRAM (github.com/yufu-wang/tram, MIT, SMPL; heavy stack with DROID-SLAM, Detectron2, SAM, ZoeDepth).
  - 4D-Humans/HMR2 (MIT, SMPL, PHALP tracking; per-frame camera-frame output only, no world trajectory).
  - PromptHMR (github.com/yufu-wang/PromptHMR, licence [U], SMPL-X, torch 2.4/2.6; best translation score on CalTennis).
  - GVHMR remains the pragmatic choice because GMR ingests its output directly.

## 3. Video -> GMR input
- **Pipeline:** cut a 30 fps clip, then run `python tools/demo/demo.py --video=clip.mp4 -s [--f_mm F]`. This writes `outputs/demo/<clip>/hmr4d_results.pt` (a torch dict with `smpl_params_global`, `smpl_params_incam` and `K_fullimg`). Then run `python scripts/gvhmr_to_robot.py --gvhmr_pred_file .../hmr4d_results.pt --robot unitree_g1 --save_path clip.pkl [--record_video]` [V].
- **GMR loader [V code]** (`general_motion_retargeting/utils/smpl.py`, `load_gvhmr_pred_file`):
  - Reads `smpl_params_global[body_pose, betas, global_orient, transl]` into a **neutral SMPL-X** model, padding betas 10→16.
  - Hard-codes `mocap_frame_rate = 30` and estimates height as `1.66 + 0.1*betas[0]`.
  - Rotates y-up to z-up.
  - The output pkl has `fps=30, root_pos, root_rot (xyzw), dof_pos, local_body_pos=None, link_body_list=None`.
- **Known quality issues:**
  - Root translation and depth drift (GVHMR has 3.6 m cross-view disagreement on CalTennis).
  - Foot sliding and foot-contact flicker.
  - Jitter at about 170 px player height.
  - Wrong shape/height from betas, which matters because GMR scales by height.
  - Floor penetration or floating.
  - GMR itself warns that some motions retarget badly (TEST_MOTIONS.md).
  - GVHMR already does contact-based post-processing (`pp_static_joint`, CCD-IK `process_ik`) [V], but it is not enough for fast lateral moves.
- **Typical fixes:**
  1. **Use the calibration.** Take `smpl_params_incam` and map it to the court frame with `R_c2w, t_c2w`. Fix depth by putting the stance foot on the court plane (z=0) along its camera ray, or triangulate the pelvis from 2 synchronized views. This removes most of the translation error. The pilot clips are E/W, NE/NW and SE/SW pairs.
  2. Pick height and shape per player by hand (fixed betas or fixed `actual_human_height`) instead of using per-clip betas.
  3. Low-pass filter the root and joints (Savitzky–Golay or 1€/Butterworth at about 6–8 Hz). Then detect contacts (foot height < 3–5 cm and speed < 0.2–0.3 m/s), lock the planted foot with leg IK, and clamp the minimum foot height to 0.
  4. After GMR, re-ground and check the G1 joint and velocity limits.
  5. Ultimately, use physics-based tracking in mjlab (BeyondMimic-style). It filters out non-physical artefacts, and clips that a tracker cannot follow should be dropped.

  Recent work such as BeyondRetarget (arXiv 2609.29850) argues for these steps rather than a raw GVHMR→retarget chain.

## 4. Concrete pilot plan
**Data.** Fetch 6 short, synchronized clips from session `09_18_2025_16_15_court5`. Each needs its `.mp4`, `_timestamps.npy` and `camera_calibration/<session>/<video_id>/calib.json` [sizes V]:

| video_id (prefix `09_18_2025_`) | MB | Duration |
|---|---|---|
| `17_25_35_000_court5_NW_01_17_26_16_546` | 22.3 | 41 s |
| `17_25_43_000_court5_NE_01_17_27_11_168` | 42.1 | 88 s |
| `17_20_07_000_court5_SE_02_17_22_15_793` | 67.3 | 128 s |
| `17_20_42_000_court5_SW_02_17_22_00_648` | 100.6 | 79 s |
| `17_22_37_000_court5_E_01_17_25_04_395` | 80.5 | 147 s |
| `17_22_41_000_court5_W_01_17_24_57_243` | 101.8 | 136 s |

- Total is about **415 MB** (+0.4 MB npy and calib).
- First open NW_01 (22 MB) to confirm the session shows full-body rallies or drills [U].
- Then cut 10–20 segments of 5–20 s, one per footwork type: split-step, shuffle, crossover, recovery, ready stance.
- Fallback: one mini-split file such as `01_28_2026_16_30_ath/01_28_2026_15_42_52_000_court1_X_1_16_20_53_928.mp4`, **1.03 GB**, about 38 min of an athletic session.

**Install** (WSL2, new py3.10 venv at `~/venvs/gvhmr`):
- GVHMR repo and requirements: torch cu121 about 2.5 GB, pytorch3d wheel, the rest about 1–2 GB → **about 4–5 GB**.
- `ffmpeg` via apt, about 100 MB, if it is not already present.
- Skip DPVO and the training data.

**Totals:**
- Downloads: about 0.4 GB data + 5.6 GB checkpoints + about 1 GB body models + about 4–5 GB environment → **about 11–12 GB**.
- Disk: about 15 GB including outputs.

**Runtime [U]:**
- About 1–2 min per 15 s clip for GVHMR on the 4070. 20 clips take about 30–45 min.
- GMR retargeting is real-time on CPU, so seconds per clip.
- Add 1 day of scripting for the calibration re-anchoring, filtering and contact cleanup.

**Downloads needing user approval:**

| # | Item | Source | Size | Licence |
|---|---|---|---|---|
| 1 | 6 CalTennis clips + npy + calib.json | huggingface.co/datasets/demalenk/caltennis | ~415 MB | CC BY-NC 4.0 |
| 2 | GVHMR source | github.com/zju3dv/GVHMR | <50 MB [U] | GVHMR non-commercial research |
| 3 | GVHMR Python deps (torch 2.3.0+cu121, torchvision, ultralytics, ...) | PyPI + download.pytorch.org/whl/cu121 | ~4 GB [U] | BSD / MIT / Apache; ultralytics AGPL-3.0 |
| 4 | pytorch3d 0.7.6 wheel | dl.fbaipublicfiles.com | ~0.1 GB [U] | BSD |
| 5 | `gvhmr_siga24_release.ckpt` | GVHMR Google Drive folder (or HF mirror camenduru/GVHMR) | 163.5 MB | GVHMR non-commercial |
| 6 | `hmr2/epoch=10-step=25000.ckpt` | same | 2.71 GB | 4D-Humans MIT |
| 7 | `vitpose-h-multi-coco.pth` | same | 2.55 GB | Apache-2.0 |
| 8 | `yolov8x.pt` | same | 136.9 MB | AGPL-3.0 |
| 9 | SMPL-X v1.1 models | smpl-x.is.tue.mpg.de (login) | ~0.8 GB [U] | MPI non-commercial, single-user |
| 10 | SMPL v1.1.0 python models | smpl.is.tue.mpg.de (login) | ~0.25 GB [U] | MPI non-commercial, single-user |
| 11 | `ffmpeg` (apt) | Ubuntu archive | ~0.1 GB | LGPL/GPL |

**Registrations the user must do personally:**
- SMPL-X account (smpl-x.is.tue.mpg.de). Accept the licence.
- SMPL account (smpl.is.tue.mpg.de). Accept the licence.

You do not need a Hugging Face or Google account: the dataset is ungated, and Drive folders are public (Drive may throttle large files, so the HF mirror is an alternative).

**Gate the pilot:**
- Visually inspect 10–20 retargeted G1 clips.
- Check foot-skate in metres per contact frame before and after cleanup, and root speed against the multi-view triangulated pelvis.
- Only then decide whether the clips go into the tracking curriculum.
