# Current training setup

Windows is the pinned platform for this checkpoint.

| Component | Pinned version |
|---|---|
| Unity Editor | 6000.5.5f1 |
| ML-Agents Unity package | 4.1.0 |
| Python | 3.10.12 |
| ML-Agents Python source | See `tools/mlagents-training/source-pin.json` |
| PyTorch | 2.8.0, CUDA 12.6 wheels |
| Environment manager | Pixi, separate training manifest and lock |

Install Pixi and Unity first. From the repository root:

```powershell
pixi install --locked
pixi run python scripts/setup_mlagents.py
pixi run --manifest-path tools/mlagents-training/pixi.toml trainer-help
```

The setup script fetches the exact upstream source revision and installs the separate training environment. The root Pixi environment preserves older experiments; use the training manifest for current ML-Agents work. Python source and Unity package versions have different numbering.

Current control: 124 observations, 16 continuous actions and one binary action branch. The reduced body and physical limits are defined in `Assets/Picklebot/PlayerControls` and `PlayerControlsIntegration`; agents, drills and worker orchestration are in `PlayerLearning`.

PPO configurations are preserved under `config/mlagents`. Production runs use headless workers with explicit manifests, private observations/actions, a finite experience budget, unique output directories and separate development evaluations. Do not launch an old worker manifest against a different source/build snapshot.

The official Unity CLI manages the Editor. Historical Coplay instructions and earlier hand-written trainers are preserved as history; the current learning path uses ML-Agents PPO. See [current state](CURRENT_STATE.md) before resuming any historical run.

## Reusable material

- All existing scene-referenced ONNX models are included in `Assets/Picklebot/PlayerLearning/Models`.
- Five full optimizer checkpoints (the comparison parent and its four branches) are included in `training/snapshots`, with hashes and lineage in `manifest.json`.
- The last comparison's plans, results, runtime identities and diagnostic verification are in `docs/research/critic-key-evidence`.
- Exact historical workflow source is in `research/critic-key-comparison/workflow`. It retains machine-specific paths and is an audit archive, not a portable one-command training launcher. Its training-data directories are intentionally not committed.

The critic-key correction was installed only in isolated experiment packages. The default environment remains the pinned upstream implementation; the isolated correction did not pass the gameplay improvement screen.
