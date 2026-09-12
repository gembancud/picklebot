# Actual-policy wider movement review

Concrete workspace scripts reuse the existing Unity camera recorder and HTML museum. No simulation source, model weights, seed ledger, or original evaluation output is modified.

## Commands

Run preparation after the completed wide analysis:

```powershell
& 'F:/dev/picklebot/tools/mlagents-training/.pixi/envs/default/python.exe' 'work/hierarchy-v1/prepare_wide_recording.py' --root 'F:/dev/picklebot'
```

This creates `outputs/wide-movement-review-01/manifest.json` and the generated `capture.cs`, with its SHA256 frozen in the manifest. The template is `work/hierarchy-v1/wide_recording_capture.cs`.

Once the owned Editor is idle in its isolated empty Play Mode scene:

```powershell
& 'C:/Users/Admin/AppData/Local/Unity/bin/unity.exe' command eval_file 'C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/outputs/wide-movement-review-01/capture.cs' --project-path 'F:/dev/picklebot' --format json
```

`eval_file(file, timeout=5000)` is present in the installed `com.unity.pipeline@9bb4172c603c` source. The asynchronous capture body returns after registering an Editor update callback. Its completion evidence is `complete.json` plus `parity.json`, not the CLI registration response. A failed attempt preserves `error.json`, partial images and any evidence already written. Do not overwrite or rerun a started capture directory.

After successful capture:

```powershell
& 'F:/dev/picklebot/tools/mlagents-training/.pixi/envs/default/python.exe' 'work/hierarchy-v1/build_wide_recording.py' --root 'F:/dev/picklebot'
```

The builder checks the original episode/goal/first-decision records again, validates every JPEG and generates `index.html`, `museum.css`, `museum.js`, `data.js`, and `verification.json`. Open the HTML and inspect both cameras, navigation, scrubbing and playback. Pinned training Python already contains Pillow.

## Scope and fidelity

- **Condition A only, at most eight clips.** For each left/right/shallow/deep direction, select the lowest-seed A legal return and lowest-seed unsuccessful A return. Missing categories remain explicitly unavailable; no replacements based on visual appeal. The right-direction cohort currently has no legal A return, so it will have only a failure example.
- **Exact original 512-reset schedule.** The capture repeats all 512 A attempts using eight arenas, the current 136-observation execution-goal contract, the same model at step 1,048,609 and the original ordinal-dependent curriculum. Shortening each recording to one seed would change drill/player/distance assignments. No B video replay is needed because the completed audit already contains paired A/B metrics.
- **Actual images and poses.** Two 800×600 JPEG views every 12 simulation ticks produce 20 fps from the 240 Hz simulation. Frames store ball position/rotation/velocities, all four player root/hand/shoulder/feet/paddle states and visible part transforms. They are sampled actual poses, not reconstructed animation. Terminal outcomes may occur between image samples.
- **Rendering leaves physics state alone.** Only arena Renderer visibility is temporarily changed. The code restores all visibility and RenderTexture state before stepping. It does not change GameObject layers, synchronize physics transforms, move bodies or add colliders. Cameras and light are temporary owned objects.
- **Full replay parity.** All 512 episode records, execution-goal/landing records and first observations/actions must match the original evidence after float32 normalization; integers, strings and booleans match exactly. Source/model/checkpoint/reference/ledger hashes are checked before and after. Any mismatch blocks verified publication and preserves failure evidence.
- **Same reserved development cases.** The existing wide campaign reservation covers these diagnostic replays. There are no new seed allocations, ledger additions, final-seed uses or optimizer updates.

The existing `outputs/drill-museum-01` frontend is copied into the new collection and lightly adapted. Four direction exhibits show all directional attempts, including misses, with a separate target-hit count. The 256 directional challenges are a subset of the full 512-attempt replay. Measured path and contact displacement appear for each clip; nominal centimetres label feed displacement relative to the paddle, not required body travel.

The owned wider evaluation Editor log contains `-batchmode` without `-nographics`; the capture also requires a non-null graphics device before starting. No Editor restart is needed if that preflight passes.

## Provenance

Preserve the manifest, actual generated capture script, template/preparer/builder scripts, complete/parity/error records, replay evidence, pose recordings and image hashes with the original wide campaign references. Never alter the original diagnostic outcomes or denominators to accommodate a recording failure.
