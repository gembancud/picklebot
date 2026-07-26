# Picklebot development setup

## Pinned tools

| Tool | Version |
|---|---|
| Unity Editor | `6000.5.5f1` |
| Unity Test Framework | `1.7.0` |
| CoplayDev MCP for Unity | `10.0.0` |
| Phase 0 environment | `env-v0` |
| Phase 1A protocol | `phase1a-protocol-v0` |
| Selected trainer adapter target | `com.unity.ml-agents@4.0.3` |

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

## Trainer environment

Phase 1A selects the ML-Agents 4.0 package line but does not install it. The
project manifest therefore remains free of ML-Agents, and the machine's current
Python environment is not treated as a trainer environment.

Before Phase 1B:

1. prepare Python `3.10.12` in a dedicated environment;
2. install and smoke-test ML-Agents Python `1.1.0` against the exact selected
   Unity package;
3. place Python, PyTorch, run artifacts, and checkpoints on a volume with
   sufficient free space;
4. run a short adapter handshake and inference/training smoke before a long
   experiment.

The version guidance is from the upstream
[ML-Agents installation guide](https://github.com/Unity-Technologies/ml-agents/blob/develop/docs/Installation.md)
and [release table](https://github.com/Unity-Technologies/ml-agents).

The headless command shape and semicolon/filter behavior follow Unity's current
Test Framework command-line reference:

<https://docs.unity3d.com/Packages/com.unity.test-framework@2.0/manual/reference-command-line.html>
