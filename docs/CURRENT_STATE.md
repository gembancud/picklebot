# Checkpoint before hierarchical control

Snapshot: **11 September 2026**. Current implementation: one actor per player instance, shared player weights, ML-Agents PPO. The proposed strategy/execution hierarchy has not been implemented.

## Demonstrated

- Learned fixed-ball serves, easy opening receives, central airborne and bounced returns.
- Constrained grip, wrist, elbow, shoulder and body control; no authored V3 stroke sequence.
- Up to 128 independent practice courts in the last comparison (8 workers × 16 courts).
- Paired practice and competitive self-play infrastructure, model exports, recordings and outcome-based evaluation.

## Latest measurement

Four matched 500,000-experience branches and 10,752 evaluation episodes completed. Every compared model kept 64/64 serves and 64/64 on each central-return test. The corrected critic-buffer key averaged 3.9 percentage points below the original trainer on earlier varied airborne returns and failed the predeclared improvement screen. All branches failed at least one directional movement-retention check. No candidate was promoted.

These are finite development tests with repeated simple setups. They do not establish full-court generalization, complete human biomechanics or competent 2v2. [Detailed results](research/critic-key-comparison.md)

## Next design

Two actor policies are proposed: a strategy policy chooses an intention and target; an execution policy coordinates movement, preparation, contact and recovery. All four players may share both policies' weights and act independently. Serving and returning may remain capabilities of one execution policy; no bank of experts is required by this proposal.

The next motor milestone is a return policy that accepts a target area and handles varied incoming balls and continuous shot transitions. Broader placement, timing, teammate coordination and reliable sustained rallies remain open. No architecture migration or new training run is included in this snapshot.

## Archive boundaries

Source, scenes, all existing ONNX exports, five full comparison checkpoints, training configuration and compact evaluation evidence are committed. Local virtual environments, generated executable builds, raw rollouts, TensorBoard events, credentials and bulk frame collections remain local. Older specifications and reports describe earlier stages; their historical conclusions are preserved.

The original repository README is preserved in [the archive](archive/README-before-2026-09-11.md). The current setup is [here](TRAINING_SETUP.md).
