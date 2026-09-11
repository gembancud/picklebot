# Windows setup and official Unity CLI

The destination is F:\dev\picklebot. D-030 authorizes the Windows setup and
migration from CoplayDev MCP to Unity's official standalone CLI.

## Installed tools

| Component | Version |
|---|---|
| Unity Editor | 6000.5.5f1, revision d16e074b49fd |
| Official Unity CLI | 1.0.0-beta.8 |
| Unity Pipeline | 0.6.0-exp.1 |
| Pixi | 0.80.0 |
| Python | 3.10.12, conda-forge Windows build |
| NumPy | 1.23.5 |
| PyTorch | 2.1.2+cpu |

Unity CLI was installed with the Windows installer linked from
https://unity.com/blog/meet-the-unity-cli . Pipeline 0.5.0-exp.1 failed live
commands with this CLI; 0.6.0-exp.1 was installed explicitly and tested.
CoplayDev is removed from the package manifest and resolved lock. No new
CoplayDev connection was configured. Unity Personal entitlement resolved.

Pixi lives at F:\dev\tools\pixi\bin\pixi.exe. The environment is
.pixi/envs/default and pixi.lock records the resolved Windows dependencies.
Open a fresh terminal to pick up the installed tools on PATH.

```powershell
cd F:\dev\picklebot
pixi install --locked
pixi run player-tests
pixi run source-check
pixi run source-check-unity
unity open F:\dev\picklebot
unity command eval 'return UnityEngine.Application.unityVersion;' --project-path F:\dev\picklebot --format json
```

The existing Python training wrapper was tested against the real CLI response,
including its project-path and nested success/result checks. Source identity is now portable under D-031. Historical checkpoints retain
their original source identity; see the migration and next steps below.

## Verified results

- All 296 player Python tests pass; artifacts/windows-player-tests.log.
- All 156 project EditMode tests pass; artifacts/windows-unity-editmode.json.
  The initial run exposed an obsolete ML-Agents 4.0.0 test expectation; it now
  matches the already-pinned 4.0.3 package. No simulator behavior changed.
- Saved actor ppo-20260907-130353 passes 32 Unity inference parity cases, maximum
  error 0.000003814697265625. Evidence is under artifacts/windows-cli-migration.
  Actor and parity input were copied there so original reports remain untouched.
- Original baseline passed before package migration. After migration,
  tooling-check verifies 61 unchanged files and exactly two recorded package
  replacements against config/windows-tooling-migration.json. The original
  63-file baseline manifest is unchanged. The strict historical baseline-check
  command intentionally reports those two package deviations.
- All 154 normal PlayMode tests pass in 66.61 seconds;
  artifacts/windows-unity-playmode.json records the completed result.

## Source identity migration (D-031)

Python and Unity now produce the same contact, player and team hashes. The
current player hash is
b317a6263e786b46398c36978ca38c3f34edc58643294a88ec88123c3cdbb79e.
The transferred actor still records its original hash
7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845.
Changing the hash implementation changes the source revision; that history is
preserved rather than hidden. config/windows-source-migration.json records
the exact transition. All 82 original artifact/model files are unchanged.

`pixi run source-check` verifies the full recorded migration against the original
baseline: 58 unchanged files, three source-tool changes and two package changes.
`pixi run source-check-unity` additionally compares live Unity and Python hashes.
The original `baseline-check` and D-030 `tooling-check` are historical strict
checks; they intentionally reject the later D-031 source edits.

Post-fix results: 300 Python tests and 158 EditMode tests pass. The saved actor
passes 32 parity cases, max error 0.000003814697265625. Logs are
artifacts/windows-hash-python-tests.log and artifacts/windows-hash-unity-tests.json;
parity is in artifacts/windows-source-migration/unity-parity.json.
The earlier 154 PlayMode test result predates this identity-only edit; no new
PlayMode run is claimed for D-031.

## Next before training

Use existing explicit historical-candidate support when evaluating transferred
actors: preserve actorTrainingSourceHash separately from current sourceHash.
Strict same-source evaluation and historical doubles evidence checks remain
strict, so a transfer is not an exact same-source resume. New data and future
checkpoints will carry the new source identity through the existing workflow.

Next run bounded physical-limit and throughput checks, then reserve fresh seed
blocks against the original history before proposing a new training run.
The trainer uses CPU tensors; CUDA and parallel workers remain separate measured
changes. Retrospective audits may need datasets omitted from the transfer.


## Current experimental integration (D-033)

The opt-in V2 body adapter changes two shared body-source files after D-031.
Use `pixi run --locked controls-check` for current exact source/archive/model
verification, or `controls-check-unity` to compare live Unity identities.
The old `source-check` is a historical D-031 snapshot and now correctly rejects
later adapter changes. No original migration or model evidence is overwritten.
See PLAYER_CONTROLS_V2.md before attempting V2 training or checkpoint transfer.


Current D-034 decision interface: use `pixi run --locked decisions-check` or
`decisions-check-unity`. This preserves the prior D-033 evidence and explicitly
records the read-only rule getters and 96-input/15-action interface. The D-033
controls-check remains a historical exact snapshot and rejects later changes.


Current D-035 physical game mechanics: use `pixi run --locked game-check` or
`game-check-unity`. This includes explicit historical source checks for the
experimental elbow refinement and preserves all previous records/models.
Prior stage checks remain historical snapshots. See PLAYER_CONTROLS_V2.md for
the current mechanics evidence and unresolved learned-action/training scope.

Current D-036 source verification: `pixi run --locked intent-check` and
`intent-check-unity`. The old actor bridge fails its first physical diagnostic
at step 675; it is not promoted or accepted. See PLAYER_CONTROLS_V2.md.

D-037 current verification: `pixi run --locked wrist-check` / `wrist-check-unity`.
The checkpoint now completes a diagnostic game after bounded wrist recovery;
all rallies still end after a single return. Agent acceptance remains incomplete.
