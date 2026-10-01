"""One reward-only arm from the common pre-axes checkpoint; frozen plan required.

Uses hash-pinned resume/audit helpers from the successful preceding continuation.
No work happens on import. A fixed final checkpoint is mandatory; there is no
automatic extension, promotion, Unity Editor control, or environment redesign.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback

RUN = "execution-movement-progress-01"
PARENT_RUN = "execution-smooth-continued-01"
BASE = "artifacts/hierarchy-v1/movement-progress-01"
PARENT_BASE = "artifacts/hierarchy-v1/smooth-continued-01"
SOURCE_BASE = BASE
BEHAVIOR = "PicklebotExecutionV1"
CONTRACT = "execution-v1-136obs-16continuous-release"
START, TARGET, MID, BUFFER = 1048609, 2097152, 1572864, 8192
TRAINING_SEED, PARENT_SEED, BASE_PORT = 19017, 19013, 5755
WORKERS, ARENAS, FIRST_SEED, SEEDS_PER_WORKER = 8, 16, 1000000, 12288
WALL_TIMEOUT = 3600
PARENT_CHECKPOINT_HASH = "c882329d7303f75703338738868a2ba53f553940e876b7962a7d410f20fa5a3d"
PARENT_MODEL_HASH = "40047704eaf92ae933e861abfbe4c6f262a4595685ca985e3c1a185804ed13cb"
PARENT_SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
CONTROL_BASE = "artifacts/hierarchy-v1/axes-recovery-01"
CONTROL_SOURCE = "557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f"
CONTROL_MODEL = "ExecutionV1AxesRecoveryFinal01"
FINAL_MODEL = "ExecutionV1MovementProgressFinal01"
REWARD_FLAG = "movementForwardProgressReward"
HELPER = "tools/mlagents-training/run_smooth_continuation.py"
HELPER_HASH = "c4454b1c7e69b50386ece91167edcc5d67def34886247079cb0c25fbe633d715"
CONFIG = "config/mlagents/execution-v1-movement-progress.yaml"
PARENT_CONFIG = "config/mlagents/execution-v1-smooth-continued.yaml"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_helper(root):
    path = root / HELPER
    require(sha(path) == HELPER_HASH, "Review the changed continuation helper before use")
    spec = importlib.util.spec_from_file_location("picklebot_pinned_continuation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These explicit campaign constants are consumed by the unchanged helper
    # functions. Its previous-campaign main() is never called.
    for name in ("RUN", "PARENT_RUN", "START", "TARGET", "BUFFER", "TRAINING_SEED", "BASE_PORT",
                 "WORKERS", "ARENAS", "FIRST_SEED", "SEEDS_PER_WORKER", "WALL_TIMEOUT",
                 "PARENT_CHECKPOINT_HASH", "PARENT_MODEL_HASH"):
        setattr(module, name, globals()[name])
    return module


def port_preflight():
    sockets = []
    try:
        for port in range(BASE_PORT, BASE_PORT + WORKERS):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(sock)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("0.0.0.0", port))
        return {"checkedAt": time.time(), "ports": list(range(BASE_PORT, BASE_PORT + WORKERS)),
                "allExclusiveBindsSucceeded": True, "reservationHeldDuringTrainerStart": False}
    finally:
        for sock in sockets:
            sock.close()


def audit_progress(episodes):
    """Check effective scope and recorded bounds, not reconstructed tick geometry."""
    enabled_count, positive_count, total, rewarded_steps = 0, 0, 0., 0
    for episode in episodes:
        enabled = episode["movementForwardProgressRewardEnabled"]
        expected = (episode["task"] in ("rally-air-feed", "rally-bounce-feed")
                    and episode["movementFeed"] and episode["movementPattern"] == "axes"
                    and 0 < episode["movementRange"] <= .0625)
        require(type(enabled) is bool and enabled == expected, "Forward-progress reward escaped focus-only scope")
        bonus, steps = episode[REWARD_FLAG], episode["movementForwardProgressRewardedSteps"]
        require(type(bonus) in (int, float) and math.isfinite(bonus) and 0 <= bonus <= .250001,
                "Recorded progress reward is nonfinite or exceeds cap")
        require(type(steps) is int and steps >= 0 and ((bonus > 0) == (steps > 0)), "Progress reward/positive-award count differs")
        require(enabled or (bonus == 0 and steps == 0), "Familiar/prior/serve/receive received progress reward")
        require(not bonus or episode["faceContact"], "Progress bonus without accepted contact")
        enabled_count += int(enabled)
        positive_count += int(bonus > 0)
        total += bonus
        rewarded_steps += steps
    return dict(episodes=len(episodes), enabledFocusEpisodes=enabled_count, positiveRewardEpisodes=positive_count,
                totalProgressReward=total, positiveRewardedSteps=rewarded_steps,
                scopeAndCapVerified=True, perTickGeometryReconstructed=False,
                interpretation="Outcome-independent telemetry audit. Zero positive rewards is reported, not converted into a success claim.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    args = parser.parse_args()
    root = args.root.resolve()
    require(os.name == "nt", "Use the pinned Windows runtime")
    pinned = root / "tools/mlagents-training/.pixi/envs/default/python.exe"
    require(Path(sys.executable).resolve() == pinned.resolve(), "Run with the project's pinned Python")
    helper = load_helper(root)
    base, parent_base = root / BASE, root / PARENT_BASE
    audit, result = base / "training", root / "artifacts/mlagents" / RUN
    parent_audit, parent_result = parent_base / "training", root / "artifacts/mlagents" / PARENT_RUN
    require(not audit.exists() and not result.exists(), "Continuation paths must be unused; partial runs remain preserved")
    plan_path, config, parent_config = base / "plan.json", root / CONFIG, root / PARENT_CONFIG
    plan = read(plan_path)
    source, build = read(root / SOURCE_BASE / "source-records.json"), read(root / SOURCE_BASE / "build-verification.json")
    SOURCE = source["sourceIdentity"]
    require(SOURCE not in (PARENT_SOURCE, CONTROL_SOURCE) and source["parentSourceIdentity"] == CONTROL_SOURCE,
            "Progress arm requires newly verified source descending from the axes control")
    require(build["buildIdentity"] != read(root / CONTROL_BASE / "build-verification.json")["buildIdentity"],
            "Progress arm cannot reuse the no-progress control build")
    expected = {"status": "frozen_movement_progress_after_axes_review", "parentRun": PARENT_RUN, "runId": RUN,
                "initialStep": START, "targetGlobalStep": TARGET, "trainingSeed": TRAINING_SEED,
                "basePort": BASE_PORT, "workerCount": WORKERS, "sourceIdentity": SOURCE,
                "parentCheckpointHash": PARENT_CHECKPOINT_HASH, "parentModelHash": PARENT_MODEL_HASH,
                "finalSeedsConsumed": False, "configPath": CONFIG, "helperPath": HELPER, "helperHash": HELPER_HASH}
    require(all(plan.get(k) == v for k, v in expected.items()), "Frozen plan does not match this draft campaign")
    require(plan["runnerHash"] == sha(Path(__file__)) and plan["limits"]["wallSeconds"] == WALL_TIMEOUT,
            "Runner or wall budget changed after plan freeze")
    require(plan["testsProof"]["result"] == "Passed" and sha(Path(plan["testsProof"]["path"])) == plan["testsProof"]["sha256"] == source["testsHash"],
            "Frozen reward/default-scope test evidence changed")
    require(plan["controlCampaign"] == CONTROL_BASE and plan["controlSourceIdentity"] == CONTROL_SOURCE
            and plan["rewardChange"]["flag"] == REWARD_FLAG and plan["rewardChange"]["enabled"] is True
            and plan["rewardChange"]["focusOnly"] is True and plan["rewardChange"]["maximumPerEpisode"] == .25,
            "Frozen reward contrast differs")
    helper.verify_hashes(root, plan["evaluation"]["baselineInputs"])
    require(sha(config) == plan["configHash"], "Frozen trainer config changed")
    launch = read(parent_audit / "launch.json")
    require(sha(parent_config) == launch["configHash"] and sha(parent_audit / "manifest.json") == launch["manifestHash"],
            "Parent recipe no longer matches its launch")
    command_before = launch["args"]
    require(command_before[command_before.index("--seed") + 1] == str(PARENT_SEED)
            and command_before[command_before.index("--num-envs") + 1] == str(WORKERS), "Parent RNG/topology differs")
    helper.verify_config(config, parent_config)
    require(source["sourceIdentity"] == build["sourceIdentity"] == SOURCE and source["contract"] == CONTRACT
            and build["buildIdentity"] == plan["buildIdentity"], "Source/build identity mismatch")
    helper.verify_hashes(root, source["files"])
    binary = Path(build["directory"])
    helper.verify_hashes(binary, build["files"])
    checkpoint, model = parent_result / BEHAVIOR / "checkpoint.pt", parent_result / f"{BEHAVIOR}.onnx"
    require(sha(checkpoint) == PARENT_CHECKPOINT_HASH and sha(model) == PARENT_MODEL_HASH, "Completed parent files changed")
    verified = read(parent_audit / "verification.json")
    require(verified["status"] == "completed_continuation_check" and verified["experiences"] == START
            and verified["checkpointHash"] == PARENT_CHECKPOINT_HASH and verified["modelHash"] == PARENT_MODEL_HASH
            and verified["resumeStateExact"] and verified["parentRunUnchanged"], "Parent completion proof mismatch")
    state = helper.torch.load(checkpoint, map_location="cpu", weights_only=False)
    require(helper.step_of(state) == START, "Parent checkpoint has unexpected step")
    parent_hashes, plan_hash = helper.tree_hashes(parent_result), sha(plan_path)
    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    ledger = read(ledger_path)
    require(ledger.get("finalSeedsConsumed") == [], "Final seed ledger usage differs")
    initial_ports = port_preflight()
    audit.mkdir()
    process, started = None, None
    try:
        write(audit / "parent-result-inputs.json", {"root": str(parent_result), "files": parent_hashes})
        shutil.copytree(parent_result, result)
        require(helper.tree_hashes(result) == parent_hashes, "Parent result copy is not byte-identical")
        helper.remap_status(parent_result, result, audit)
        manifest = read(parent_audit / "manifest.json")
        require(manifest == plan["parentManifest"], "Parent physical training recipe differs from plan")
        require(manifest["sourceIdentity"] == PARENT_SOURCE
                and manifest["workerCount"] == WORKERS and manifest["arenasPerWorker"] == ARENAS
                and manifest["firstSeed"] == FIRST_SEED and manifest["seedsPerWorker"] == SEEDS_PER_WORKER
                and manifest["placementRewardMode"] == "smooth-distance-2m", "Parent manifest contract mismatch")
        require(manifest["sourceIdentity"] == PARENT_SOURCE, "Parent manifest source differs")
        manifest.update(evidenceRoot=str(audit), basePort=BASE_PORT, sourceIdentity=SOURCE,
                        buildIdentity=build["buildIdentity"], movementPattern="axes", movementRange=.0625,
                        movementForwardProgressReward=True)
        require(manifest == plan["trainingManifest"], "Training recipe differs from frozen progress plan")
        write(audit / "manifest.json", manifest)
        command = [str(pinned.parent / "Scripts/mlagents-learn.exe"), str(config), "--run-id", RUN,
                   "--results-dir", str(root / "artifacts/mlagents"), "--resume", "--seed", str(TRAINING_SEED),
                   "--env", str(binary / "Picklebot.exe"), "--num-envs", str(WORKERS), "--base-port", str(BASE_PORT),
                   "--no-graphics", "--timeout-wait", "180", "--max-lifetime-restarts", "0",
                   "--env-args", "--picklebot-manifest", str(audit / "manifest.json")]
        require(Path(command[0]).is_file(), "Pinned ML-Agents CLI missing")
        proof = helper.verify_resume_loader(config, command, result, state, audit)
        require(sha(result / BEHAVIOR / "checkpoint.pt") == PARENT_CHECKPOINT_HASH
                and helper.tree_hashes(parent_result) == parent_hashes, "Resume preflight modified checkpoint or parent")
        final_ports = port_preflight()
        write(audit / "launch.json", {"args": command, "planHash": plan_hash, "configHash": sha(config),
              "manifestHash": sha(audit / "manifest.json"), "sourceIdentity": SOURCE, "buildIdentity": build["buildIdentity"],
              "parentLaunchHash": sha(parent_audit / "launch.json"), "parentConfigHash": sha(parent_config),
              "parentManifestHash": sha(parent_audit / "manifest.json"), "resumeProof": proof,
              "initialStep": START, "targetGlobalStep": TARGET, "maximumAcceptedGlobalStep": TARGET + BUFFER - 1,
              "wallTimeoutSeconds": WALL_TIMEOUT, "scriptHash": sha(Path(__file__)), "helperHash": HELPER_HASH,
              "portPreflight": [initial_ports, final_ports], "workerEmbeddedModelHash": manifest["modelHash"],
              "resumedPolicyModelHash": PARENT_MODEL_HASH, "trainingSeed": TRAINING_SEED,
              "rewardChange": plan["rewardChange"], "controlCampaign": CONTROL_BASE,
              "limitations": ["Processes and RNG restart; reset IDs are intentionally reused.",
                              "PPO rollout buffers and live environment states are not restored.",
                              "Copied TensorBoard history precedes1048609; count only later steps as new training.",
                              "Port checks are live checks, not an atomic lease through trainer startup.",
                              "One matched-seed reward arm and an already completed control; not independent replication or bitwise trajectory equivalence."]})
        # Refresh to avoid overwriting reservations made during the loader check.
        ledger = read(ledger_path)
        require(ledger.get("finalSeedsConsumed") == [], "Final seed usage changed during preflight")
        require(not any(row["run"] == f"{BASE}/training" for row in ledger.get("trainingReuses", [])), "This training reuse was already recorded")
        before_ledger_bytes = ledger_path.read_bytes()
        require(json.loads(before_ledger_bytes.decode("utf-8-sig")) == ledger, "Seed ledger changed during allocation")
        with (audit / "seed-ledger-before.json").open("xb") as stream:
            stream.write(before_ledger_bytes)
        ledger.setdefault("trainingReuses", []).append({"firstSeed": FIRST_SEED, "count": SEEDS_PER_WORKER * WORKERS,
            "run": f"{BASE}/training", "purpose": f"Reward-only arm from common parent{START} to{TARGET}; same axes6.25-25cm25/25/50mix and smooth placement; focus-only capped actual post-contact progress reward enabled; restarted matched RNG{TRAINING_SEED}; no final seeds."})
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        write(audit / "seed-ledger-allocation.json", {"ledgerBeforeHash": sha(audit / "seed-ledger-before.json"),
              "ledgerAfterHash": sha(ledger_path), "trainingReuse": ledger["trainingReuses"][-1], "finalSeedsConsumed": False})
        started = time.monotonic()
        with (audit / "trainer-console.log").open("x", encoding="utf-8") as console:
            process = subprocess.Popen(command, cwd=root, stdout=console, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            write(audit / "process.json", {"pid": process.pid, "started": time.time(), "ownedProcess": True})
            print(f"{RUN}: trainer{process.pid}; resume{START} -> {TARGET}, {WORKERS}workers x{ARENAS}courts", flush=True)
            code = process.wait(timeout=WALL_TIMEOUT)
        write(audit / "process-result.json", {"exitCode": code, "wallSeconds": time.monotonic()-started, "timeout": False})
        require(code == 0, "Trainer failed; inspect preserved console")
        text = (audit / "trainer-console.log").read_text(encoding="utf-8-sig")
        reject = ("Traceback (most recent call last)", "[ERROR]", "Failed to load for module", "Did not find these keys",
                  "Did not expect these keys", "Starting training from step 0", "Training status file not found",
                  "different version of ML-Agents", "different version of PyTorch")
        require(f"Resuming training from step {START}." in text and not any(s in text for s in reject), "Trainer resume/failure check failed")
        final_checkpoint, final_model = result / BEHAVIOR / "checkpoint.pt", result / f"{BEHAVIOR}.onnx"
        final_state = helper.torch.load(final_checkpoint, map_location="cpu", weights_only=False)
        step, changes = helper.audit_final_states(state, final_state)
        require(sha(final_model) != PARENT_MODEL_HASH and sha(final_checkpoint) != PARENT_CHECKPOINT_HASH, "Training outputs unchanged")
        workers, goals, inputs = helper.audit_workers(audit, manifest, source, build)
        progress_audits = []
        for worker in range(WORKERS):
            worker_report = read(audit / f"worker-{worker:02}" / "report.json")
            require(worker_report["movementPattern"] == "axes" and worker_report["movementRange"] == .0625
                    and abs(worker_report["movementRehearsalRange"]-.1) < 1e-7 and worker_report["movementRecoveryMix"]
                    and worker_report["interleavedRecovery"] and worker_report["movementTiming"] == 0
                    and worker_report["movementStartVariation"] == 0 and worker_report["movementPositionReward"] == 0
                    and worker_report[REWARD_FLAG] is True,
                    "Worker axes/rehearsal/interleaving contract differs")
            require(read(audit / f"worker-{worker:02}" / "worker-startup.json")[REWARD_FLAG] is True,
                    "Worker startup did not record enabled progress reward")
            episodes = helper.rows(audit / f"worker-{worker:02}" / "episodes.jsonl")
            progress_audits.append({"worker": worker, **audit_progress(episodes)})
            focus = [row for row in episodes if row["movementPattern"] == "axes"]
            require(focus and all(0 < row["movementRange"] <= .0625 and row["movementRegion"] in (1,3,5,7) for row in focus),
                    "Actual graded axes focus resets missing or malformed")
            require(all(row["movementPattern"] in ("court", "axes") for row in episodes), "Unexpected focus pattern in axes training")
            workers[worker]["focusEpisodes"] = len(focus)
            workers[worker]["focusLegalReturns"] = sum(row["outcome"] == "legal_return" for row in focus)
            require(worker_report["nextSeedIndex"] < SEEDS_PER_WORKER,
                    "A worker issued its full reset allocation, including unfinished resets")
        require(helper.tree_hashes(parent_result) == parent_hashes, "Completed parent run was modified")
        helper.verify_hashes(root, source["files"])
        helper.verify_hashes(binary, build["files"])
        helper.verify_hashes(root, plan["evaluation"]["baselineInputs"])
        require(sha(plan_path) == plan_hash and sha(config) == plan["configHash"], "Frozen plan/config changed")
        require(read(ledger_path).get("finalSeedsConsumed") == [], "Final acceptance seeds changed during training")
        numbered = []
        for path in (result / BEHAVIOR).glob(f"{BEHAVIOR}-*.pt"):
            match = re.fullmatch(re.escape(BEHAVIOR) + r"-(\d+)\.pt", path.name)
            if match:
                numbered.append({"step": int(match[1]), "path": path.relative_to(root).as_posix(), "sha256": sha(path)})
        numbered.sort(key=lambda item: item["step"])
        mid = min(numbered, key=lambda item: (abs(item["step"]-MID), item["step"])) if numbered else None
        require(mid is not None and abs(mid["step"]-MID) <= BUFFER, "Fixed trajectory checkpoint was not retained")
        summary = {"status": "completed_continuation_check", "initialStep": START, "experiences": step,
                   "newExperiences": step-START, "targetGlobalStep": TARGET, "resumeStateExact": True,
                   "parentRunUnchanged": True, "stateChanges": changes, "workers": workers, "episodes": len(goals),
                   "legalLandings": sum(row["legalLanding"] for row in goals), "targetsHit": sum(row["targetHit"] for row in goals),
                   "workerInputSha256": inputs, "rewardFormulaVerified": True, "sourceIdentity": SOURCE,
                   "buildIdentity": build["buildIdentity"], "model": final_model.relative_to(root).as_posix(),
                   "modelHash": sha(final_model), "checkpointHash": sha(final_checkpoint), "retainedNumberedCheckpoints": numbered,
                   "fixedMidpoint": mid, "evaluateMidpoint": plan["evaluation"]["evaluateMidpoint"],
                   "movementProgressRewardAudit": progress_audits, "rewardChange": plan["rewardChange"],
                   "controlCampaign": CONTROL_BASE, "independentTrainingReplication": False,
                   "heldOutPerformanceEvaluated": False, "promoted": False, "masteryAccepted": False,
                   "finalSeedsConsumed": False, "rngOrRolloutContinuationClaimed": False, "automaticExtension": False}
        write(audit / "verification.json", summary)
        print(json.dumps({key: summary[key] for key in ("status", "experiences", "newExperiences", "episodes", "modelHash")}), flush=True)
    except BaseException as error:
        cleanup = None
        if process is not None and process.poll() is None:
            stopped = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                                     text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            cleanup = {"ownedTrainerPid": process.pid, "exitCode": stopped.returncode, "stdout": stopped.stdout, "stderr": stopped.stderr}
        failure = {"status": "failed_preserved", "error": repr(error), "traceback": traceback.format_exc(),
                   "timeout": isinstance(error, subprocess.TimeoutExpired), "cleanup": cleanup,
                   "wallSeconds": None if started is None else time.monotonic()-started, "artifactsPreserved": True, "promoted": False}
        if not (audit / "process-result.json").exists():
            write(audit / "process-result.json", {"exitCode": None if process is None else process.poll(),
                  "timeout": failure["timeout"], "wallSeconds": failure["wallSeconds"]})
        write(audit / "failure.json", failure)
        raise


if __name__ == "__main__":
    main()
