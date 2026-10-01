# Picklebot — notes for Claude

Unity 6000.5.5f1 + ML-Agents PPO project teaching a constrained articulated body to serve/return pickleball. Windows host (`F:\dev\picklebot`). Active branch line: `feat/hierarchical-control` (goal-conditioned "execution" policy). `git` is **not** on PATH in the default PowerShell.

## Where to start reading
- `docs/CURRENT_STATE.md` — newest-first status log (top entry may be stale; verify against `artifacts/`).
- `docs/DRILL_MASTERY_GOAL.md` — active milestone and its evidence requirements.
- `docs/HIERARCHICAL_CONTROL.md` — strategy/execution design and execution-v1 contract.
- `docs/DECISIONS.md` — append-only decision log (last formal entry D-037).
- `docs/TRAINING_SETUP.md`, `docs/WINDOWS_SETUP.md`, `docs/DEMO.md`.
- `docs/research/execution-v1-*.md` — per-experiment reports.

## Active code (Assets/Picklebot)
- `PlayerLearning/` — ML-Agents adapter and drills (active).
  - `PlayerExecutionGoalV1.cs` — contract `execution-v1-136obs-16continuous-release`, behavior `PicklebotExecutionV1`, 124 obs + 12 goal features.
  - `PlayerExecutionDrillsV1.cs` — opt-in goal sampler (own RNG), placement bonus (≤0.25, `linear-radius` / `smooth-distance-2m`), writes `execution-goals.jsonl`.
  - `PlayerMlAgentV3.cs` — agent; 16 continuous outputs + masked binary release branch.
  - `PlayerMlDrillsV3.cs` — drill runner/scheduler, decisions every 12 ticks.
  - `PlayerRecoveryScheduleV3.cs` — familiar / prior / focus episode mixture; `PlayerRightReturnAcquisitionV1.cs`.
  - `PlayerHeadlessBootstrapV3.cs` + `PlayerWorkerPlanV3.cs` — headless worker reads `--picklebot-manifest`.
  - `Editor/ExecutionBuildV1.cs` — `-executeMethod Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine` worker build.
  - `Tests/` — main PlayMode test suite.
- `PlayerControlsIntegration/` — match/world glue, `PlayerContactDrillV3` (drill rewards), `PlayerObservationV3` (124 obs), `PlayerPrecontactPotentialV3` (opt-in shaping).
- `PlayerControls/` — V3 body/action (18 channels).
- `Doubles/` is still a dependency (`DoublesWorld`/`DoublesRules`). Core, Simulation, Evaluation, Training, Rally, Competition, Inspection, Match, Museum, PlayerAgents, DoublesTraining are historical phases — don't modify without reason.
- `Scenes/execution-*-build-NN.unity` are generated per worker build; don't hand-edit.

## Python / training
- Root `pixi.toml`: legacy env (torch 2.1.2 CPU, no mlagents). `pixi run player-tests` runs `scripts/tests/test_player*.py`. The `*-check` tasks are historical snapshots that are *expected* to reject later source changes.
- `tools/mlagents-training/pixi.toml`: current trainer env (torch 2.8.0 cu126, vendored ML-Agents pinned in `source-pin.json`, unpatched). Run things with `pixi run --manifest-path tools/mlagents-training/pixi.toml python ...`. Pixi lives at `F:\dev\tools\pixi\bin\pixi.exe`.
- `tools/mlagents-training/initialize_execution_v1.py` — warm-start 124→136 obs (not a resume). `run_smooth_continuation.py` — canonical exact resume helper that later campaign runners import.
- `config/mlagents/execution-v1-*.yaml` + `*-workers.json` — trainer configs / worker manifests (8 workers × 16 courts).
- `research/hierarchy-v1/<campaign-NN>/` — committed, hash-pinned workflow scripts + compact evidence. Historical: never rerun against completed dirs; copy into a new campaign dir instead.
- `artifacts/hierarchy-v1/<campaign>/` (audit, builds, evaluations) and `artifacts/mlagents/<run-id>/` (checkpoints, ONNX, TB events) — local, large.
- Unity is driven via the official Unity CLI: `unity.exe test <root> --mode PlayMode|EditMode --filter ...`, `unity.exe command eval_file <script.cs> --project-path F:/dev/picklebot --format json`. Test runs may strip `;SENTIS_ANALYTICS_ENABLED` from `ProjectSettings.asset` — restore it.

## Working rules (from DECISIONS.md and practice)
- **Final acceptance seeds are never used** for training, selection, early stopping or tuning (`artifacts/player-v3/seed-ledger.json` → `finalSeedsConsumed == []`). Training, development (4000000–4099999) and final ranges are disjoint.
- **No automatic promotion or extension.** Plans (`plan.json`) are frozen before launch with a fixed-endpoint selection. Evaluate per skill/variation (narrow A/B/random, wide A/B, randomized A/B), report legal returns *and* target hits, and give A/B assignment gain with intervals. Don't hide failures in averages. 5-pp legal-retention loss limit vs parent.
- Each run gets fresh output dirs (`execution-<topic>-NN`, models `ExecutionV1<Topic>Final01`). Never relaunch an old manifest against a different source/build.
- Decisions are append-only: new direction = new D-xxx entry; keep failed reports; don't relabel historical artifacts or rewrite `sourceHash` values.
- Change one variable per experiment where possible. Pinned versions change only with a decision entry and before/after verification.
