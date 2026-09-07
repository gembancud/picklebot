# Move the player-agent project

This source snapshot includes selected model weights. It does not include the
bulk recorded games or drill datasets. Keep those files on the original machine
for historical audits. Do not delete them after a clone.

## What a clone includes

- Unity source, scenes, assets, `.meta` files, package locks, and project settings.
- Python trainers, diagnostics, tests, and frozen evaluation plans.
- The original doubles models and the 63-file baseline manifest with its three
  required evidence reports.
- Experimental player checkpoint `ppo-20260907-130353`, including `actor.json`,
  `critic.pt`, training metadata, source snapshots, and output-parity inputs.
- Starting checkpoint `trunk-movement-fit-20260907-122354` and older opponent
  `contact-movement-fit-20260907-114743`, with their saved metadata.
- The latest development summaries. Both execution modes lost all eight games.
  No checkpoint in this transfer is accepted as the completed player-agent goal.

The latest checkpoint folder is about 1.9 MB. These selected files fit in ordinary
Git. Do not add each training output to Git. Use a separate artifact archive if
the checkpoint collection grows substantially.

The clone excludes Unity caches, Python environments, local Codex connections,
and most files in `artifacts`. `.gitignore` lists the exact artifact exceptions.
Historical reports contain original absolute paths. Keep them unchanged; they
are evidence, not portable restart commands.

## Set up the destination

1. Clone the repository. Do not enable line-ending conversion. The included
   `.gitattributes` preserves file bytes because the baseline uses file hashes.
2. Install Unity **6000.5.5f1**, revision **d16e074b49fd**. Open the cloned project
   and let Unity restore the packages in `Packages/packages-lock.json`.
3. Install Python **3.10.12**. Create a new environment on this machine. Do not
   copy the Mac `.venv` folder.

```text
python -m venv .venv/player-agents
```

On Windows, the environment interpreter is
`.venv/player-agents/Scripts/python.exe`. On Linux or macOS, it is
`.venv/player-agents/bin/python`. Use that interpreter for each command below.

```text
python -m pip install -r config/player-agents/requirements.txt
python -m unittest discover -s scripts/tests -p "test_player*.py"
python scripts/player-agents-baseline.py --check
```

These commands refer to the new environment interpreter, not an unrelated system
Python. The current trainer uses CPU tensors and two PyTorch threads. An installed
CUDA build of PyTorch does not make this trainer use the GPU automatically.
GPU execution and parallel simulation workers require separate measured changes.

## View the existing scenes

Open `Assets/Picklebot/Scenes/IndependentPlayers.unity`, press Play, and select
the Game tab. Space pauses. N starts a new game. R toggles replay. I toggles intent.
The scene retains its existing experimental preview model. The newer checkpoint
under `artifacts` is not installed in the scene automatically.

The preserved doubles baseline is
`Assets/Picklebot/Scenes/PickleballDoubles.unity`. Physics remains provisional:
the outdoor 40-hole ball and acrylic court profile is not physically calibrated.

## Checks required before more training

- Confirm the destination OS and Unity CLI connection. Local connection settings
  are not part of this upload. Do not reuse commands containing the old Mac path.
- Verify source hashes on the destination. Current Python and C# source-hash
  functions use slash-based test-folder filtering. Windows path separators may
  change that result. This has not been tested on Windows. Do not bypass a
  mismatch or overwrite the original hashes to make a check pass.
- Verify saved-model output parity in Unity and run bounded physical-limit and
  game checks. Cross-machine simulation equivalence is not yet established.
- Reserve fresh training/development seed blocks against the historical records
  on the original machine. Keep the final seed range unused.
- Start a new bounded collection from the saved actor and critic. This retains
  learned parameters; it is not an exact mid-update process resume.

Some historical diagnostic commands need omitted raw data. In particular, the
saved stage-evaluation summaries do not make `player-stage-evaluate.py` runnable
in a clone: its shot-quality reference report and associated traces are not
included. Restore the exact required evidence before using such commands. Fresh
self-play collection does not need all old recorded games.

No automatic training, installation, cleanup, or model promotion occurs on clone.
See `docs/PLAYER_AGENTS_PROGRESS.md` for the measured results and remaining work.
