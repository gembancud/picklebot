# Trained executor: 24 million steps

The shared execution policy uses two256-unit hidden layers,136 observations,16 continuous actions and one binary branch. It learns constrained movement and strokes under externally supplied drill goals. A learned strategy policy is not trained yet.

| Saved state | Step | Files |
|---|---:|---|
| Final training save | 24,000,022 | [ONNX](../Assets/Picklebot/PlayerLearning/Models/ExecutionV1RandomizedScale24mFinal.onnx), [full trainer checkpoint](../training/snapshots/execution-v1-randomized-scale-24m-final.pt) |
| Last evaluated snapshot | 23,999,987 | [ONNX](../Assets/Picklebot/PlayerLearning/Models/ExecutionV1RandomizedScale24m24000000.onnx), [full trainer checkpoint](../training/snapshots/execution-v1-randomized-scale-24m-evaluated.pt) |

The final save and evaluated snapshot are distinct. Do not attribute the evaluation below to the final save without evaluating it. Full checkpoints retain actor, critic, normalization, optimizer and global step; ONNX is for Unity inference. Load full checkpoints only from trusted sources. Neither snapshot is promoted as a mastered game policy.

## Last evaluated results

| Test | Target A | Target B |
|---|---:|---:|
| Narrow rally returns |224/224|223/224|
| Wide rally returns |260/384|255/384|
| Randomized rally returns |352/448|356/448|
| Wide-battery serves |64/64|64/64|
| Wide-battery opening receives |64/64|64/64|

These are repeatedly used development seeds. They do not establish unseen-match performance or reliable target-conditioned placement. The raw final episode/goal records are included as gzip files under the publication archive; failed outcomes remain in the denominators.

## Reproduce and continue

- [Training setup](TRAINING_SETUP.md) and [Windows setup](WINDOWS_SETUP.md) pin the Unity/ML-Agents environment.
- [Exact continuation configuration](../research/hierarchy-v1/randomized-scale-publication/randomized-scale-24m/training/config.yaml) records PPO and network settings. The completed max_steps budget must be raised for a new continuation.
- Use a fresh run directory with the selected full checkpoint under `PicklebotExecutionV1/checkpoint.pt`, remove `init_path`, and use the maintained trainer's `--resume` path. Verify the restored global step, actor, critic, normalizers and Adam state before collecting data; `--initialize-from` is not an exact resume.
- Archived campaign scripts preserve original absolute paths and immutable run IDs as provenance. Copy/adapt them for a fresh campaign; do not rerun them against completed output folders. Executable builds and original runtime artifacts must be rebuilt/restored separately.
- [Skill history](../research/hierarchy-v1/randomized-scale-publication/skill-history.csv) contains per-task counts across all scheduled checkpoints. [Publication manifest](../research/hierarchy-v1/randomized-scale-publication/publication-manifest.json) records source paths and SHA-256 identities.

## What GitHub contains

Source, training configuration and dependency manifests, workflow scripts, selected trained models and resumable checkpoints, compact evaluation records and historical experiment reports. The latest compact publication adds roughly8MB before Git compression; it does not upload the45GB local artifact tree and does not require Git LFS.

Bulk raw training logs, TensorBoard event files, intermediate model exports, generated executable builds, recordings and external HTML museums remain local. Unity caches and installed Python dependencies are excluded. GitHub is a source/model recovery point, not a complete disk backup. New runs must explicitly archive their selected checkpoint and results to be included.
