# Stage 5E style reference: 100STYLE filter rule and split (D-101, frozen 2026-10-18)

Written and frozen before any 100STYLE clip was extracted, retargeted or scored (D-098).

## Source

- **Dataset:** 100STYLE, by Ian Mason, Sebastian Starke and Taku Komura. Zenodo record 8127870; paper DOI 10.1145/3522618.
- **Licence:** CC BY 4.0. Credit is given in the README and here.
- **File:** `100STYLE.zip`, 1,468,515,354 bytes, md5 `3cf627852fd8192024c04a8d0ef49583`, verified on 2026-10-17. Stored in the git-ignored `mjlab/artifacts/motion/100style-raw/`.

## Filter rule (from 100STYLE's own labels)

1. **Style:** the folder `Neutral` only. All 99 other styles (e.g. Zombie, Chicken, Penguin) are excluded.
2. **Content type:** the file suffixes are 100STYLE's content labels.

   | Suffix | Content | Kept? |
   |---|---|---|
   | `FW` | forward walking | yes |
   | `BW` | backward walking | yes |
   | `SW` | sidestep walking | yes |
   | `SR` | sidestep running | yes |
   | `FR` | forward running | no |
   | `BR` | backward running | no |
   | `ID` | idling | no |
   | `TR1`-`TR3` | transitions | no |

   This follows D-098's rule: "neutral walking and sidestep only".
3. **Frames:** only those inside 100STYLE's `Frame_Cuts.csv` START..STOP range for that style and content type.
   - Neutral FW: 327-7445
   - Neutral BW: 380-8235
   - Neutral SW: 354-5730
   - Neutral SR: 340-3066

   All at 60 fps.

## Split (held-out reference slice)

Each of the four clips is cut by time inside its frame range:
- **First 70 %:** training data (tracking teacher and discriminator).
- **Last 30 %:** the held-out reference slice. It is used only by the style metric, and never for training.

## Retarget acceptance (checked before any clip is used)

The paddle G1 is retargeted with GMR, using the same IK pipeline as LAFAN1 (`scripts/motion/lafan_retarget.py`) and a 100STYLE joint map. A clip is accepted only if it passes all of these:
- **Position error:** body-position error median <= 0.08 m and p95 <= 0.20 m, the LAFAN1 / tennis thresholds.
- **Foot sliding:** for a foot below 3 cm, the median horizontal speed is <= 0.10 m/s.
- **Ground contact:** the deepest penetration is <= 2 cm.

A clip that fails is reported and left out. The rule and the thresholds are not changed afterwards.

## Style metric on the new reference (gate: <= 3.86, absolute; D-098)

- **Unchanged from the old metric** (`scripts/motion/style_score.py`):
  - pose features: 29 joints, projected gravity, hands and feet in the pelvis frame;
  - nearest-pose distance in standardised feature space;
  - 60,000 reference poses.
- **Reference composition:**
  - **Old reference:** tennis-v5 and LAFAN1, concatenated and sampled by frame count.
  - **New reference:** fixed source shares of the 60,000 poses:
    - tennis-v5: 0.50;
    - LAFAN1: 0.25;
    - the held-out 100STYLE slice: 0.25.

    Standardisation statistics come from the same composed sample.
- **Reporting:** every style result gives both the old-reference score and the new-reference score. h4-25b's re-score on the new reference is reported for information only.
- **Discriminator:** a style discriminator built for training on these clips excludes the wrist joints (D-098). The metric is not changed by that.

## Retarget result and one implementation note (2026-10-18, before any scoring)

**Retarget** (`scripts/motion/style100_retarget.py`, reports in `artifacts/motion/style100-g1/*.json`):

| Clip | Accepted? | Position error median / p95 | Foot sliding | Why |
|---|---|---|---|---|
| Neutral FW (forward walking) | yes, both parts | 2-3 cm / about 7 cm | <= 0.07 m/s | |
| Neutral BW (backward walking) | yes, both parts | 2-3 cm / about 7 cm | <= 0.07 m/s | |
| Neutral SW (sidestep walking) | yes, both parts | 2.4 cm / 6.6-7.1 cm | 0.04 m/s | |
| Neutral SR (sidestep running) | **no**, both parts | | 0.126 and 0.106 m/s (> 0.10) | The G1's ankle-roll joints are at their limit in 33-45 % of frames. Left out, as the rule says. |

**Ground contact:** the retargeter shifts each clip so that its lowest foot touches the ground. The penetration check (<= 2 cm) is therefore met by construction.

**Motion files** (50 fps):
- training part: `artifacts/motion/tracking/style100-train.npz`, 11,867 frames (4.0 min);
- held-out reference slice: `style100-ref.npz`, 5,083 frames (1.7 min).

**Share note:** the reference slice has fewer poses (5,083) than its 0.25 share of the 60,000-pose reference (15,000). The share is filled by repeating the slice's poses.
- **Nearest-pose distance:** repeats do not change a robot pose's distance to the nearest reference pose.
- **Standardisation:** the repeats weight it as the share says.
- **Human floor:** it is measured on held-out tennis and LAFAN1 frames only, because the 100STYLE slice is used up by its share.
