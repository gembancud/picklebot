"""Run one bounded continuation through the installed ML-Agents --resume path.

Requires a frozen plan/config prepared by the campaign owner. Copies the completed
parent run exclusively, remaps copied checkpoint-manager paths, and checks an exact
actor/critic/normalizer/Adam/global-step load before starting the trainer. This is a
checkpoint continuation with restarted processes and reused reset IDs, not a bitwise
continuation of environment state, PPO rollout buffers, or RNG streams.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

import torch
import yaml


PARENT_RUN = "execution-smooth-distance-01"
RUN = "execution-smooth-continued-01"
BEHAVIOR = "PicklebotExecutionV1"
CONTRACT = "execution-v1-136obs-16continuous-release"
START, TARGET, BUFFER = 262179, 1048576, 8192
TRAINING_SEED, BASE_PORT, WORKERS, ARENAS = 19013, 5655, 8, 16
FIRST_SEED, SEEDS_PER_WORKER = 1000000, 12288
WALL_TIMEOUT = 2400
FIRST_LAYER = "network_body._body_endoder.seq_layers.0.weight"
PARENT_CHECKPOINT_HASH = "d3d5c9ce0c1c8ef919d2b0ee4320842ffb61860c12a911b32414903cbd709205"
PARENT_MODEL_HASH = "29cb54047f5cb79f570114d09704bc8bf0513dba77874f289d9fcad354d2f8a6"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def tree_hashes(directory):
    resolved = directory.resolve()
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink() and path.resolve().is_relative_to(resolved), f"Unexpected linked result path: {path}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = sha(path)
    return result


def verify_hashes(directory, hashes):
    root = directory.resolve()
    for relative, expected in hashes.items():
        path = directory / relative
        require(path.resolve().is_relative_to(root), f"Hash manifest escapes expected root: {relative}")
        require(path.is_file() and sha(path) == expected, f"File identity changed: {path}")


def exact(expected, actual, name="state"):
    if isinstance(expected, torch.Tensor):
        require(isinstance(actual, torch.Tensor) and expected.dtype == actual.dtype
                and expected.shape == actual.shape
                and torch.equal(expected.detach().cpu(), actual.detach().cpu()), f"Resume tensor mismatch: {name}")
    elif isinstance(expected, dict):
        require(isinstance(actual, dict) and set(expected) == set(actual), f"Resume dictionary mismatch: {name}")
        for key in expected:
            exact(expected[key], actual[key], f"{name}/{key}")
    elif isinstance(expected, (tuple, list)):
        require(type(expected) is type(actual) and len(expected) == len(actual), f"Resume sequence mismatch: {name}")
        for index, (old, new) in enumerate(zip(expected, actual)):
            exact(old, new, f"{name}/{index}")
    else:
        require(type(expected) is type(actual) and expected == actual, f"Resume scalar mismatch: {name}")


def cpu_copy(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cpu_copy(item) for item in value]
    if isinstance(value, tuple):
        return tuple(cpu_copy(item) for item in value)
    return copy.deepcopy(value)


def step_of(state):
    values = list(state["global_step"].values())
    require(len(values) == 1 and values[0].numel() == 1, "Unexpected global step contract")
    return int(values[0].item())


def remap_status(parent_result, result, audit):
    relative = "run_logs/training_status.json"
    old = read(parent_result / relative)
    new = copy.deepcopy(old)
    changes = []

    def remap(value):
        path = Path(value)
        require(path.is_absolute() and path.resolve().is_relative_to(parent_result.resolve()),
                f"Parent checkpoint manager path outside parent run: {value}")
        target = result / path.resolve().relative_to(parent_result.resolve())
        require(target.resolve().is_relative_to(result.resolve()) and target.is_file(), f"Missing isolated checkpoint: {target}")
        changes.append({"old": value, "new": str(target)})
        return str(target)

    require(set(new) == {BEHAVIOR, "metadata"}, "Unexpected status behaviors; review resume explicitly")
    entry = new[BEHAVIOR]
    require(entry["final_checkpoint"]["steps"] == START, "Parent status step mismatch")
    for checkpoint in [*entry["checkpoints"], entry["final_checkpoint"]]:
        checkpoint["file_path"] = remap(checkpoint["file_path"])
        checkpoint["auxillary_file_paths"] = [remap(path) for path in checkpoint["auxillary_file_paths"]]
    # Only the copied metadata is rewritten; the parent remains immutable.
    shutil.copy2(parent_result / relative, audit / "parent-training-status.json")
    (result / relative).write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    for checkpoint in [*entry["checkpoints"], entry["final_checkpoint"]]:
        for value in [checkpoint["file_path"], *checkpoint["auxillary_file_paths"]]:
            require(Path(value).resolve().is_relative_to(result.resolve()), "Checkpoint retention could touch the parent")
    write(audit / "status-remap.json", {"originalHash": sha(parent_result / relative),
          "copiedHashAfterRemap": sha(result / relative), "changes": changes,
          "reason": "ML-Agents checkpoint retention uses these absolute paths for deletion; all are scoped to the isolated copy."})


def verify_config(config, old_config):
    new = yaml.safe_load(config.read_text(encoding="utf-8-sig"))
    old = yaml.safe_load(old_config.read_text(encoding="utf-8-sig"))
    require(set(new["behaviors"]) == {BEHAVIOR}, "Unexpected configured behavior")
    settings = new["behaviors"][BEHAVIOR]
    require(settings.get("init_path") is None, "Remove init_path: the pinned loader prioritizes it even with --resume")
    for key, expected in {"max_steps": TARGET, "checkpoint_interval": 262144, "keep_checkpoints": 4}.items():
        require(settings[key] == expected, f"Incorrect continuation {key}")
    for document in (new, old):
        behavior = document["behaviors"][BEHAVIOR]
        for key in ("init_path", "max_steps", "checkpoint_interval", "keep_checkpoints"):
            behavior.pop(key, None)
    require(new == old, "Config changed beyond removing init_path and the declared step/checkpoint budget")


def verify_resume_loader(config, command, result, parent_state, audit):
    # Use the same pinned CLI parser and PPO add_policy -> model_saver loader as
    # the subsequent trainer process, without environments, updates, or exports.
    from mlagents import torch_utils
    from mlagents.trainers.learn import parse_command_line
    from mlagents.trainers.ppo.trainer import PPOTrainer
    from mlagents.trainers.behavior_id_utils import BehaviorIdentifiers
    from mlagents.trainers.model_saver.torch_model_saver import TorchModelSaver
    from mlagents.trainers.training_status import GlobalTrainingStatus
    from mlagents_envs.base_env import BehaviorSpec, ObservationSpec, DimensionProperty, ObservationType, ActionSpec

    options = parse_command_line(command[1:])
    require(options.checkpoint_settings.resume and options.checkpoint_settings.maybe_init_path is None,
            "CLI did not resolve to resume without initialize-from")
    require(options.behaviors[BEHAVIOR].init_path is None, "Parsed init_path would supersede resume")
    require(Path(options.checkpoint_settings.write_path).resolve() == result.resolve(), "CLI result directory mismatch")
    torch_utils.set_torch_config(options.torch_settings)
    GlobalTrainingStatus.saved_state.clear()
    GlobalTrainingStatus.load_state(str(result / "run_logs/training_status.json"))
    trainer = PPOTrainer(BEHAVIOR, 10, options.behaviors[BEHAVIOR], True, True, TRAINING_SEED, str(result / BEHAVIOR))
    spec = BehaviorSpec([ObservationSpec((136,), (DimensionProperty.NONE,), ObservationType.DEFAULT,
                         "VectorSensor_size136")], ActionSpec(16, (2,)))
    parsed = BehaviorIdentifiers.from_name_behavior_id(BEHAVIOR + "?team=0")
    policy = trainer.create_policy(parsed, spec)
    trainer.add_policy(parsed, policy)
    state = {name: cpu_copy(module.state_dict()) for name, module in trainer.model_saver.modules.items()}
    exact(parent_state, state)
    require(step_of(state) == START and policy.get_current_step() == START, "Installed loader did not restore the expected global step")
    require(state["Optimizer:value_optimizer"]["state"], "Adam history must be populated")
    snapshot = audit / "resume-loaded-state.pt"
    torch.save(state, snapshot)
    exact(parent_state, torch.load(snapshot, map_location="cpu", weights_only=False))
    source_paths = [Path(inspect.getfile(item)) for item in (parse_command_line, PPOTrainer, TorchModelSaver, GlobalTrainingStatus)]
    proof = {"status": "exact_registered_state_restored", "globalStep": START,
             "modules": list(state), "actorCriticNormalizersAndAdamExact": True,
             "snapshotHash": sha(snapshot), "copiedCheckpointHash": sha(result / BEHAVIOR / "checkpoint.pt"),
             "configHash": sha(config), "installedSourceHashes": {str(path): sha(path) for path in source_paths},
             "method": "Separate preflight invokes installed PPOTrainer.add_policy(load=True); same CLI config/copy/loader as trainer subprocess, not an in-subprocess tensor hook.",
             "rngOrRolloutContinuationClaimed": False}
    write(audit / "resume-load-proof.json", proof)
    del trainer, policy, state
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return proof


def audit_final_states(parent, final):
    require(set(parent) == set(final), "Final checkpoint module contract changed")
    final_step = step_of(final)
    require(TARGET <= final_step < TARGET + BUFFER, f"Global step outside bounded target: {final_step}")
    changes = {}
    for name in ("Policy", "Optimizer:critic"):
        require(set(parent[name]) == set(final[name]), f"Final state keys changed: {name}")
        require(final[name][FIRST_LAYER].shape == (128, 136), "Executor input shape changed")
        require(all(torch.isfinite(value).all().item() for value in final[name].values() if isinstance(value, torch.Tensor)),
                f"Nonfinite model state: {name}")
        require(not torch.equal(parent[name][FIRST_LAYER], final[name][FIRST_LAYER]), f"No learned weight change: {name}")
        counters = [key for key in final[name] if key.endswith("normalizer.normalization_steps")]
        require(counters and all(torch.all(final[name][key] > parent[name][key]).item() for key in counters),
                f"Normalization counters did not advance: {name}")
        changes[name] = {"firstLayerChanged": True, "normalizersAdvanced": True,
                         "maximumFirstLayerDelta": float((final[name][FIRST_LAYER] - parent[name][FIRST_LAYER]).abs().max())}
    old_optimizer, new_optimizer = parent["Optimizer:value_optimizer"], final["Optimizer:value_optimizer"]
    exact(old_optimizer["param_groups"], new_optimizer["param_groups"], "Adam/param_groups")
    require(set(old_optimizer["state"]) == set(new_optimizer["state"]), "Adam parameter-state IDs changed")
    moment_changes = 0
    for parameter, old_state in old_optimizer["state"].items():
        new_state = new_optimizer["state"][parameter]
        require(set(old_state) == set(new_state), "Adam state contract changed")
        require(float(new_state["step"]) > float(old_state["step"]), "An Adam step counter did not advance")
        for key, value in new_state.items():
            if isinstance(value, torch.Tensor):
                require(torch.isfinite(value).all().item(), f"Nonfinite Adam state: {parameter}/{key}")
        moment_changes += int(not torch.equal(old_state["exp_avg"], new_state["exp_avg"]))
    require(moment_changes > 0, "Adam moments did not change")
    changes["Adam"] = {"parameterStates": len(new_optimizer["state"]), "allStepCountersAdvanced": True,
                        "changedFirstMomentStates": moment_changes}
    return final_step, changes


def audit_workers(audit, manifest, source, build):
    summaries, all_goals, inputs = [], [], {}
    for worker in range(WORKERS):
        folder = audit / f"worker-{worker:02}"
        startup, report = read(folder / "worker-startup.json"), read(folder / "report.json")
        require(startup["status"] == "configured" and not startup["error"], f"Worker {worker} startup failed")
        require(startup["workerId"] == worker and startup["trainerRequired"], "Worker identity/training mismatch")
        require(startup["sourceIdentity"] == source["sourceIdentity"] and startup["expectedBuildIdentity"] == build["buildIdentity"], "Worker source/build mismatch")
        require(startup["manifestHash"] == sha(audit / "manifest.json"), "Worker manifest hash mismatch")
        first_seed = FIRST_SEED + worker * SEEDS_PER_WORKER
        require(startup["firstSeed"] == first_seed and startup["seedCount"] == SEEDS_PER_WORKER and startup["arenas"] == ARENAS,
                "Worker reset interval or court count mismatch")
        require(report["trainerConnected"] and report["contract"] == CONTRACT and not report["failure"], "Worker did not complete valid training")
        require(report["status"] != "seed_budget_complete" and report["completedEpisodes"] < SEEDS_PER_WORKER, "Worker exhausted its declared training resets")
        require(report["sourceIdentity"] == source["sourceIdentity"] and report["split"] == "training", "Worker report source/split mismatch")
        episodes, goals = rows(folder / "episodes.jsonl"), rows(folder / "execution-goals.jsonl")
        require(len(episodes) == len(goals) == report["completedEpisodes"] and len(goals) > 0, "Worker evidence count mismatch")
        require(len({row["seed"] for row in goals}) == len(goals), "Duplicate completed reset within worker")
        for episode, goal in zip(episodes, goals):
            require(episode["seed"] == goal["seed"] and episode["player"] == goal["player"], "Private episode/goal pairing mismatch")
            require(first_seed <= goal["seed"] < first_seed + SEEDS_PER_WORKER, "Worker consumed unexpected reset IDs")
            require(episode["decisions"] == sum(episode["decisionsByPlayer"])
                    and all((number > 0) == (seat == episode["player"]) for seat, number in enumerate(episode["decisionsByPlayer"])),
                    "Private one-player drill decisions changed")
            require(goal["contract"] == CONTRACT and goal["assigned"] and goal["targetLayout"] == "two-regions"
                    and goal["radius"] == 1 and goal["rewardMode"] == "smooth-distance-2m", "Worker reward/goal contract mismatch")
            legal = episode["outcome"] in ("legal_return", "legal_serve")
            require(goal["legalLanding"] == legal and goal["hasLanding"] == legal, "Legal-landing evidence mismatch")
            require(all(math.isfinite(goal[key]) for key in ("distance", "bonus", "landingX", "landingZ", "targetX", "targetZ")), "Nonfinite reward evidence")
            if legal:
                distance = math.hypot(goal["landingX"] - goal["targetX"], goal["landingZ"] - goal["targetZ"])
                require(abs(distance - goal["distance"]) < 2e-5, "Landing distance evidence mismatch")
            expected = .25 * math.exp(-goal["distance"] / 2) if legal else 0
            require(abs(goal["bonus"] - expected) < 2e-7 and 0 <= goal["bonus"] <= .25, "Smooth reward formula mismatch")
            require(goal["targetHit"] == (legal and goal["distance"] <= 1), "Target success criterion changed")
        for name in ("worker-startup.json", "report.json", "episodes.jsonl", "execution-goals.jsonl"):
            inputs[f"worker-{worker:02}/{name}"] = sha(folder / name)
        summaries.append({"worker": worker, "episodes": len(goals), "firstSeed": first_seed,
                          "contract": report["contract"], "rewardFormulaVerified": True})
        all_goals.extend(goals)
    return summaries, all_goals, inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    base = root / "artifacts/hierarchy-v1/smooth-continued-01"
    old_base = root / "artifacts/hierarchy-v1/smooth-distance-01"
    audit, result = base / "training", root / "artifacts/mlagents" / RUN
    parent_result, parent_audit = root / "artifacts/mlagents" / PARENT_RUN, old_base / PARENT_RUN
    require(not audit.exists() and not result.exists(), "Use fresh exclusive continuation paths; partial attempts are preserved")
    require(os.name == "nt", "This bounded launcher is for the pinned Windows runtime")
    plan_path = base / "plan.json"
    plan = read(plan_path)
    expected_plan = {"parentRun": PARENT_RUN, "runId": RUN, "initialStep": START, "targetGlobalStep": TARGET,
                     "trainingSeed": TRAINING_SEED, "basePort": BASE_PORT, "workerCount": WORKERS,
                     "parentCheckpointHash": PARENT_CHECKPOINT_HASH, "parentModelHash": PARENT_MODEL_HASH,
                     "finalSeedsConsumed": False}
    require(all(plan.get(key) == value for key, value in expected_plan.items()), "Frozen plan does not match this bounded campaign")
    config = (args.config or root / plan["configPath"]).resolve()
    require(config.is_file() and config.resolve().is_relative_to(root) and sha(config) == plan["configHash"], "Frozen config mismatch")
    parent_launch = read(parent_audit / "launch.json")
    old_config = root / "config/mlagents/execution-v1-smooth-distance.yaml"
    require(sha(old_config) == parent_launch["configHash"]
            and sha(parent_audit / "manifest.json") == parent_launch["manifestHash"],
            "Parent training recipe no longer matches its recorded launch")
    old_command = parent_launch["args"]
    require(old_command[old_command.index("--seed") + 1] == str(TRAINING_SEED)
            and old_command[old_command.index("--num-envs") + 1] == str(WORKERS), "Parent seed/topology differs")
    verify_config(config, old_config)
    require((root / plan["sourceRecordPath"]).resolve() == (old_base / "source-records.json").resolve()
            and (root / plan["buildRecordPath"]).resolve() == (old_base / "build-verification.json").resolve(),
            "Plan references an unexpected source/build record")
    source, build = read(old_base / "source-records.json"), read(old_base / "build-verification.json")
    require(source["sourceIdentity"] == build["sourceIdentity"] == plan["sourceIdentity"] and build["buildIdentity"] == plan["buildIdentity"], "Source/build plan mismatch")
    require(source["contract"] == CONTRACT, "Unexpected source observation/action contract")
    verify_hashes(root, source["files"])
    binary = Path(build["directory"])
    verify_hashes(binary, build["files"])
    parent_checkpoint, parent_model = parent_result / BEHAVIOR / "checkpoint.pt", parent_result / f"{BEHAVIOR}.onnx"
    require(sha(parent_checkpoint) == PARENT_CHECKPOINT_HASH and sha(parent_model) == PARENT_MODEL_HASH, "Completed parent model/checkpoint changed")
    parent_verified = read(parent_audit / "verification.json")
    require(parent_verified["status"] == "completed_learning_check" and parent_verified["experiences"] == START
            and parent_verified["checkpointHash"] == PARENT_CHECKPOINT_HASH and parent_verified["modelHash"] == PARENT_MODEL_HASH, "Parent training verification mismatch")
    parent_state = torch.load(parent_checkpoint, map_location="cpu", weights_only=False)
    require(step_of(parent_state) == START, "Parent checkpoint is not at the declared resume step")
    parent_hashes = tree_hashes(parent_result)
    plan_hash = sha(plan_path)
    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    ledger = read(ledger_path)
    require(ledger.get("finalSeedsConsumed") == [], "Final seed ledger records consumed final seeds or has an unexpected schema")
    audit.mkdir()
    process = None
    started = None
    try:
        write(audit / "parent-result-inputs.json", {"root": str(parent_result), "files": parent_hashes})
        shutil.copytree(parent_result, result)
        require(tree_hashes(result) == parent_hashes, "Result copy was not byte-identical before metadata remap")
        remap_status(parent_result, result, audit)
        manifest = read(parent_audit / "manifest.json")
        require(manifest["sourceIdentity"] == source["sourceIdentity"] and manifest["buildIdentity"] == build["buildIdentity"], "Parent worker build mismatch")
        require(manifest["firstSeed"] == FIRST_SEED and manifest["seedsPerWorker"] == SEEDS_PER_WORKER
                and manifest["workerCount"] == WORKERS and manifest["arenasPerWorker"] == ARENAS
                and manifest["placementRewardMode"] == "smooth-distance-2m", "Parent reset distribution differs")
        manifest.update(evidenceRoot=str(audit), basePort=BASE_PORT)
        write(audit / "manifest.json", manifest)
        command = [str(Path(sys.executable).parent / "Scripts/mlagents-learn.exe"), str(config),
                   "--run-id", RUN, "--results-dir", str(root / "artifacts/mlagents"), "--resume",
                   "--seed", str(TRAINING_SEED), "--env", str(binary / "Picklebot.exe"),
                   "--num-envs", str(WORKERS), "--base-port", str(BASE_PORT), "--no-graphics",
                   "--timeout-wait", "180", "--max-lifetime-restarts", "0",
                   "--env-args", "--picklebot-manifest", str(audit / "manifest.json")]
        require(Path(command[0]).is_file(), "Run using the project's pinned Python environment")
        proof = verify_resume_loader(config, command, result, parent_state, audit)
        require(sha(result / BEHAVIOR / "checkpoint.pt") == PARENT_CHECKPOINT_HASH, "Preflight modified the copied checkpoint")
        require(tree_hashes(parent_result) == parent_hashes, "Preflight modified the completed parent run")
        write(audit / "launch.json", {"args": command, "planHash": plan_hash, "configHash": sha(config),
              "manifestHash": sha(audit / "manifest.json"), "sourceIdentity": source["sourceIdentity"],
              "parentLaunchHash": sha(parent_audit / "launch.json"),
              "parentConfigHash": sha(old_config), "parentManifestHash": sha(parent_audit / "manifest.json"),
              "buildIdentity": build["buildIdentity"], "resumeProof": proof, "initialStep": START,
              "targetGlobalStep": TARGET, "maximumAcceptedGlobalStep": TARGET + BUFFER - 1,
              "wallTimeoutSeconds": WALL_TIMEOUT, "scriptHash": sha(Path(__file__)),
              "workerEmbeddedModelHash": manifest["modelHash"], "resumedPolicyModelHash": PARENT_MODEL_HASH,
              "resetReuse": {"firstSeed": FIRST_SEED, "count": SEEDS_PER_WORKER * WORKERS},
              "limitations": ["RNG and environment processes restart; reset IDs are intentionally reused.",
                              "PPO rollout buffers and per-agent environment states are not checkpointed.",
                              "Inherited TensorBoard history is copied; new experiences start after global step262179.",
                              "Preflight proves the installed loader's exact module state; trainer logs additionally confirm its actual resume step."]})
        ledger.setdefault("trainingReuses", []).append({"firstSeed": FIRST_SEED, "count": SEEDS_PER_WORKER * WORKERS,
            "run": str(audit.relative_to(root)), "purpose": "Full checkpoint continuation from262179 to1048576; identical smooth target reward/reset distribution, restarted process RNG; no final seeds."})
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        started = time.monotonic()
        with (audit / "trainer-console.log").open("x", encoding="utf-8") as console:
            process = subprocess.Popen(command, cwd=root, stdout=console, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            write(audit / "process.json", {"pid": process.pid, "started": time.time(), "ownedProcess": True})
            print(f"{RUN}: trainer {process.pid}; resume{START} -> {TARGET}, 8 workers x 16 courts", flush=True)
            exit_code = process.wait(timeout=WALL_TIMEOUT)
        write(audit / "process-result.json", {"exitCode": exit_code, "wallSeconds": time.monotonic() - started, "timeout": False})
        require(exit_code == 0, "Trainer failed; inspect trainer-console.log")
        console_text = (audit / "trainer-console.log").read_text(encoding="utf-8-sig")
        require(f"Resuming training from step {START}." in console_text, "Trainer did not confirm expected resume step")
        reject = ("Traceback (most recent call last)", "[ERROR]", "Failed to load for module",
                  "Did not find these keys", "Did not expect these keys", "Starting training from step 0",
                  "Training status file not found", "different version of ML-Agents", "different version of PyTorch")
        require(not any(message in console_text for message in reject), "Trainer reported a partial/incompatible load or failure")
        final_checkpoint, final_model = result / BEHAVIOR / "checkpoint.pt", result / f"{BEHAVIOR}.onnx"
        final_state = torch.load(final_checkpoint, map_location="cpu", weights_only=False)
        final_step, changes = audit_final_states(parent_state, final_state)
        require(sha(final_model) != PARENT_MODEL_HASH and sha(final_checkpoint) != PARENT_CHECKPOINT_HASH, "Final output did not change")
        workers, goals, worker_inputs = audit_workers(audit, manifest, source, build)
        require(tree_hashes(parent_result) == parent_hashes, "Completed parent run was modified during continuation")
        verify_hashes(root, source["files"])
        verify_hashes(binary, build["files"])
        require(sha(plan_path) == plan_hash and sha(config) == plan["configHash"], "Frozen plan/config changed during continuation")
        numbered = []
        for path in sorted((result / BEHAVIOR).glob(f"{BEHAVIOR}-*.pt")):
            match = re.fullmatch(re.escape(BEHAVIOR) + r"-(\d+)\.pt", path.name)
            if match:
                numbered.append({"step": int(match[1]), "path": str(path.relative_to(root)), "sha256": sha(path)})
        summary = {"status": "completed_continuation_check", "initialStep": START, "experiences": final_step,
                   "newExperiences": final_step - START, "targetGlobalStep": TARGET,
                   "resumeStateExact": True, "parentRunUnchanged": True, "stateChanges": changes,
                   "workers": workers, "episodes": len(goals), "legalLandings": sum(row["legalLanding"] for row in goals),
                   "targetsHit": sum(row["targetHit"] for row in goals),
                   "legalTargetMissesWithPositiveFeedback": sum(row["legalLanding"] and not row["targetHit"] and row["bonus"] > 0 for row in goals),
                   "workerInputSha256": worker_inputs, "rewardFormulaVerified": True,
                   "sourceIdentity": source["sourceIdentity"], "buildIdentity": build["buildIdentity"],
                   "model": str(final_model.relative_to(root)), "modelHash": sha(final_model),
                   "checkpointHash": sha(final_checkpoint), "retainedNumberedCheckpoints": numbered,
                   "heldOutPerformanceEvaluated": False, "promoted": False, "masteryAccepted": False,
                   "finalSeedsConsumed": False, "rngOrRolloutContinuationClaimed": False}
        write(audit / "verification.json", summary)
        print(json.dumps(summary, indent=2), flush=True)
    except BaseException as error:
        cleanup = None
        # Only terminate the still-running trainer process that this launcher owns,
        # together with its descendants. No process-name matching or editor control.
        if process is not None and process.poll() is None:
            stopped = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                     capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            cleanup = {"ownedTrainerPid": process.pid, "exitCode": stopped.returncode,
                       "stdout": stopped.stdout, "stderr": stopped.stderr}
        failure = {"status": "failed_preserved", "error": repr(error), "traceback": traceback.format_exc(),
                   "timeout": isinstance(error, subprocess.TimeoutExpired), "cleanup": cleanup,
                   "wallSeconds": None if started is None else time.monotonic() - started,
                   "artifactsPreserved": True, "promoted": False}
        if not (audit / "process-result.json").exists():
            write(audit / "process-result.json", {"exitCode": None if process is None else process.poll(),
                  "timeout": failure["timeout"], "wallSeconds": failure["wallSeconds"]})
        write(audit / "failure.json", failure)
        raise


if __name__ == "__main__":
    main()
