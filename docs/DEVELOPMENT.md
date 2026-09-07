# Picklebot development setup

## Pinned tools

| Tool | Version |
|---|---|
| Unity Editor | `6000.5.5f1` |
| Unity Test Framework | `1.7.0` |
| CoplayDev MCP for Unity | `10.0.0` |
| Phase 0 environment | `env-v0` |
| Phase 1A protocol | `phase1a-protocol-v0` |
| Phase 1B calibration spec | `physics-calibration-v0` |
| Phase 1B output environment | `env-v1` |
| Physics feel-check tool | `physics-museum-v1` |
| Selected trainer adapter target | `com.unity.ml-agents@4.0.3` |
| Python trainer | `mlagents==1.1.0`, PyTorch `2.1.2`, Python `3.10.12` |

Package versions and Git dependencies are pinned in `Packages/manifest.json`.
Do not change a pinned version without a decision entry and a passing
before/after verification run.

## Open the project

Open the repository root as the Unity project:

```text
/Users/gem/git/jsts/picklebot
```

Unity-generated `Library`, `Temp`, `Logs`, and `UserSettings` directories are
ignored by Git.

## Inspect the calibrated physics interactively

Open `Assets/Picklebot/Scenes/PhysicsMuseum.unity` and enter Play Mode. The six
stations exercise the real `env-v1` environment while keeping all museum input,
telemetry, camera, and trajectory presentation in the separate
`Picklebot.Museum` assembly.

Mac keyboard and mouse/trackpad controls, station behavior, visual legends, and
the boundary between intuitive feel checks and empirical calibration are
documented in [PHYSICS_MUSEUM.md](PHYSICS_MUSEUM.md).

## MCP for Unity

The project pins CoplayDev MCP for Unity `v10.0.0`. The Codex project
configuration points to the plugin's loopback HTTP endpoint:

```text
http://127.0.0.1:8080/mcp
```

After Unity imports the project:

1. Open **Window → MCP for Unity**.
2. Run **Auto-Setup**.
3. Start the Unity Bridge if it is not already running.
4. Select Codex and configure the detected client.
5. Restart Codex so the project-local MCP server is discovered.

The MCP is development tooling only. Runtime and core simulation assemblies
must not reference it.

## Batch verification

Batch commands require an active Unity Editor entitlement. The scripts default
to the pinned editor path above; override it only with an explicit
`PICKLEBOT_UNITY` environment variable.

Run the fast suites independently:

```bash
./scripts/phase0-editmode.sh
./scripts/phase0-playmode.sh
```

Run the explicit 10,000-episode soak:

```bash
./scripts/phase0-soak.sh
```

Run the complete Phase 0 gate:

```bash
./scripts/phase0-verify.sh
```

Run the Phase 1A fast suites:

```bash
./scripts/phase1a-editmode.sh
./scripts/phase1a-playmode.sh
```

Generate the explicit 1,000-episode-per-policy baseline and readiness evidence:

```bash
./scripts/phase1a-evidence.sh
```

Run the complete Phase 0 plus Phase 1A regression gate:

```bash
./scripts/phase1a-verify.sh
```

The Unity Test Framework command-line filters are intentional:

- EditMode selects only `Picklebot.Tests.EditMode`;
- normal PlayMode excludes the `Soak` category;
- the soak selects its exact full test name.

Generated NUnit XML and Unity logs are written below
`artifacts/phase0/tests/` and remain local during development. The Phase 0
closing NUnit XML snapshots are versioned below
`docs/evidence/phase0/tests/`. The versioned soak summary and per-episode
manifests are written to:

```text
docs/evidence/phase0/soak/summary.json
docs/evidence/phase0/soak/episodes.jsonl
```

Set `PICKLEBOT_SOURCE_COMMIT` when verifying a checkout that should be named
explicitly in the soak summary. If it is unset, the soak script reads the
current Git `HEAD`.

Phase 1A uses the same variable for baseline and readiness reports. Local NUnit
XML and logs are written under `artifacts/phase1a/tests/`; versioned closing
evidence belongs under `docs/evidence/phase1a/`.

## Next gate: Phase 1B physics calibration

Phase 1B is specified but not yet implemented. Its fixtures, acceptance
measurements, provenance requirements, and artifact layout are normative in
[PHASE1B_PHYSICS_CALIBRATION_SPEC.md](PHASE1B_PHYSICS_CALIBRATION_SPEC.md).
Implementation must add real scripts and tests before documenting them here as
runnable commands. Closing evidence will be versioned under
`docs/evidence/phase1b/`, and the passing simulator will be frozen as `env-v1`.

The phase changes simulator behavior, so `env-v0` and its Phase 1A evidence are
not updated in place. D-023 permits the bounded Phase 1C0 diagnostic probe
defined in
[PHASE1C0_LEARNING_PROBE_SPEC.md](PHASE1C0_LEARNING_PROBE_SPEC.md) without
claiming this calibration phase is closed.

## Trainer environment

Phase 1A selected the ML-Agents 4.0 package line without installing it. D-023
authorizes installation for Phase 1C0 after the release pair is reverified.
The global/base Python environment is never treated as the trainer environment.

For Phase 1C0:

1. create the project-isolated Conda environment from
   `config/phase1c0/environment.yml`;
2. install and smoke-test Python `3.10.12` plus PyPI ML-Agents Python `1.1.0`
   against Unity package `com.unity.ml-agents@4.0.3`; on Apple Silicon the
   Conda environment supplies the package's required native
   `grpcio==1.48.2`, while PyTorch remains pinned to `2.1.2` so checkpoint
   export stays compatible with ML-Agents' ONNX `1.15.0` and protobuf
   `3.20.3` constraints;
3. keep generated runs, checkpoints, summaries, and trajectories below
   `artifacts/phase1c0/` and enforce the storage budget in the probe spec;
4. pass a Unity-Python handshake before beginning optimization;
5. use `Phase1CObservationEncoderV0`; the frozen Phase 1A encoder has a
   different ball-spin scale and must not be reused for `env-v1` training.
6. never construct a request from `Phase1CProtocolV0.FinalEvaluationSeeds`
   during Phase 1C0.

Create or repair the environment with:

```bash
./scripts/phase1c0-env-create.sh
```

Start a new bounded run:

```bash
./scripts/phase1c0-train.sh phase1c0-local-001
```

Resume that exact run after a recoverable interruption:

```bash
./scripts/phase1c0-train.sh phase1c0-local-001 --resume
```

Then open `Assets/Picklebot/Scenes/Phase1CTraining.unity` and enter Play Mode
only after the trainer reports that it is listening. Native model selection
and unseen-seed replay use
`Assets/Picklebot/Scenes/Phase1CValidation.unity`.

The version guidance is from the upstream
[ML-Agents installation guide](https://github.com/Unity-Technologies/ml-agents/blob/develop/docs/Installation.md)
and [release table](https://github.com/Unity-Technologies/ml-agents).

The headless command shape and semicolon/filter behavior follow Unity's current
Test Framework command-line reference:

<https://docs.unity3d.com/Packages/com.unity.test-framework@2.0/manual/reference-command-line.html>
