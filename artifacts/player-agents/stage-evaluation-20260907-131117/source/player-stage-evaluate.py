#!/usr/bin/env python3
"""Run the fixed development probe and match sequence for one saved player actor."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from player_actor import Actor, ROOT, file_hash, source_hash
from player_serve_return import audit as serve_audit
from player_teacher_gap import audit as return_audit
from player_skill_gate_games import validate_game_outcome

spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/player-compare-models.py")
comparison = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparison)

SEED = 1141000
REFERENCE = ROOT / "artifacts/player-agents/shot-quality-20260907-071111.json"
REFERENCE_HASH = "bca2df18ca98e0e6a6e53b3a251bf3c59a94d32bb148e33b34ac69504a155e9f"
SOURCES = ("player-stage-evaluate.py", "player-compare-models.py", "player-agents-train-loop.py",
    "player_actor.py", "player_ppo.py", "player_acceptance.py", "player_contact_outcomes.py",
    "player_serve_return.py", "player_teacher_gap.py", "player_shot_quality.py", "player_skill_retention.py",
    "player_skill_gate_games.py", "player-unity-job-status.cs", "player-serve-return-probe.cs",
    "player-teacher-gap.cs", "player-final-evaluate.cs")


def artifact_path(value, prefix=None):
    if not isinstance(value, str): raise ValueError("Expected an artifact path")
    path = (ROOT / value).resolve()
    path.relative_to((ROOT / "artifacts/player-agents").resolve())
    if prefix is not None and not path.name.startswith(prefix): raise ValueError("Unexpected artifact kind")
    return path


def validate_state(state, source, idle=False):
    if (state.get("playing") is not True or state.get("generatedCallbackDetection") is not True
            or state.get("source") != source or type(state.get("busy")) is not bool
            or not isinstance(state.get("jobs"), list)):
        raise ValueError("Unity is stopped, uses different source, or lacks an authoritative job check")
    if idle and (state["busy"] or state["jobs"]):
        raise RuntimeError("Finish the existing Unity job before this evaluation")


def validate_parity(actor, source):
    parity = json.loads((actor.parent / "unity-parity.json").read_text())
    if (parity.get("passed") is not True or parity["actorHash"] != file_hash(actor)
            or parity["sourceHash"] != source or parity["cases"] < 32
            or not 0 <= parity["maximumError"] < .0001
            or parity["inputHash"] != file_hash(actor.parent / "parity-input.json")):
        raise ValueError("Missing or stale Unity parity")
    return parity


def unity(command, argument):
    result = subprocess.run(["unity", "command", command, argument, "--format", "json", "--project-path", str(ROOT)],
        cwd=ROOT, capture_output=True, text=True, timeout=45)
    # Do not retry an uncertain state-changing command.
    if result.returncode: raise RuntimeError("Unity command failed; inspect the same job before any restart: " + result.stdout)
    return comparison.loop.unity_value(json.loads(result.stdout))


def unity_state(source, idle=False):
    state = unity("eval_file", "scripts/player-unity-job-status.cs")
    validate_state(state, source, idle)
    return state


def wait_probe(source, callback):
    deadline = time.monotonic() + 1800
    while True:
        time.sleep(10)
        state = unity_state(source)
        if not state["busy"]:
            if state["jobs"]: raise RuntimeError("Inconsistent Unity job state")
            return
        if not state["jobs"] or any(callback not in job["name"] for job in state["jobs"]):
            raise RuntimeError("Unexpected concurrent Unity job; inspect without restarting")
        if time.monotonic() > deadline:
            raise RuntimeError("Probe observation timeout; inspect this same active callback before restarting")


def add_game_outcomes(verified):
    folder = Path(verified["folder"])
    outcomes = [validate_game_outcome(json.loads((folder / f"group-{g}.json").read_text())) for g in range(8)]
    result = dict(verified)
    result["truncatedRallies"] = sum(o["truncatedRallies"] for o in outcomes)
    result["truncatedFraction"] = result["truncatedRallies"] / result["rallies"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor", type=Path)
    args = parser.parse_args()
    actor = artifact_path(str(args.actor)); _, metadata = Actor.load_export(actor)
    source = source_hash()
    if metadata["sourceHash"] != source or metadata["trainingSteps"] <= 0:
        raise ValueError("Use a trained current-runtime actor")
    validate_parity(actor, source)
    if file_hash(REFERENCE) != REFERENCE_HASH: raise ValueError("Short/deep control reference changed")
    manifest_path = ROOT / "artifacts/player-agents/baseline-manifest.json"
    for path, digest in json.loads(manifest_path.read_text())["files"].items():
        if file_hash(ROOT / path) != digest: raise ValueError("Frozen baseline changed")
    for key, path in (("protocolHash", "config/player-agents/evaluation-v1.json"),
                      ("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                      ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json")):
        if metadata[key] != file_hash(ROOT / path): raise ValueError("Actor environment changed")
    unity_state(source, idle=True)
    if shutil.disk_usage(ROOT).free < 1024**3:
        raise RuntimeError("Less than 1 GiB is free. Do not start new evaluation artifacts or remove existing evidence.")
    folder = ROOT / "artifacts/player-agents" / ("stage-evaluation-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False); (folder / "source").mkdir()
    frozen = {str(actor): file_hash(actor), str(REFERENCE): REFERENCE_HASH}
    for name in SOURCES:
        path = ROOT / "scripts" / name
        shutil.copy2(path, folder / "source" / name); frozen[str(path)] = file_hash(path)
    plan = dict(version="player-stage-evaluation-v1", actor=str(actor), actorHash=file_hash(actor), sourceHash=source,
        split="development", serveCases=36, returnCases=64, gameSeedBase=SEED,
        samplingModes=[False, True], gamesPerMode=8, frozen=frozen,
        limitation="Fixed development checks only. Keep final seeds unused. No scene replacement or automatic promotion.")
    (folder / "plan.json").write_text(json.dumps(plan, indent=2))
    progress = dict(status="running", planHash=file_hash(folder / "plan.json"), actorHash=file_hash(actor),
        sourceHash=source, stage="starting", results={})
    def save(): (folder / "progress.json").write_text(json.dumps(progress, indent=2))
    def check_frozen():
        if source_hash() != source or any(file_hash(p) != digest for p, digest in frozen.items()):
            raise ValueError("Stage source, actor or control input changed")
    def store_result(name, result):
        target = folder / (name + "-audit.json")
        with target.open("x") as out: json.dump(result, out, indent=2)
        progress["results"][name] = dict(path=str(target), sha256=file_hash(target))
        progress.pop("activeReport", None); progress.pop("activeDriver", None); progress.pop("childPid", None)
        save()
    save(); print(folder, flush=True)
    try:
        for name, key, script, callback in (
                ("serves", "Picklebot.ServeReturn.ActorPath", "player-serve-return-probe.cs", "TickServeReturn"),
                ("returns", "Picklebot.TeacherGap.ActorPath", "player-teacher-gap.cs", "TickTeacherGap")):
            check_frozen(); unity_state(source, idle=True)
            progress["stage"] = name; save()
            unity("eval", "UnityEditor.SessionState.SetString(" + json.dumps(key) + "," + json.dumps(str(actor)) + "); return true;")
            target = artifact_path(unity("eval_file", "scripts/" + script))
            progress["activeReport"] = str(target); save(); print(name + ": " + str(target), flush=True)
            wait_probe(source, callback)
            result = serve_audit(target) if name == "serves" else return_audit(target, REFERENCE)
            if result["actorHash"] != plan["actorHash"]: raise ValueError("Probe used a different actor")
            if name == "returns": result["verifiedTraceCount"] = len(result.pop("traces"))
            check_frozen(); store_result(name, result); print(name + " audit passed", flush=True)
        for sampled in (False, True):
            name = "sampled-games" if sampled else "fixed-games"
            check_frozen(); unity_state(source, idle=True)
            progress["stage"] = name; save()
            command = [sys.executable, "scripts/player-compare-models.py", str(actor), "--seed", str(SEED)]
            if sampled: command.append("--sampled-actor")
            child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            progress["childPid"] = child.pid; save(); child_folder = None
            with (folder / (name + ".log")).open("x") as log:
                for line in child.stdout:
                    log.write(line); log.flush(); print(line.rstrip(), flush=True)
                    if child_folder is None and line.strip().startswith(str(ROOT / "artifacts/player-agents/model-comparison-")):
                        child_folder = artifact_path(line.strip(), "model-comparison-")
                        progress["activeDriver"] = str(child_folder); save()
            if child.wait() or child_folder is None:
                raise RuntimeError("Match driver stopped; inspect its saved log and same Unity job before restarting")
            child_progress = json.loads((child_folder / "progress.json").read_text())
            if child_progress["status"] != "complete" or len(child_progress["runs"]) != 1:
                raise ValueError("Incomplete match driver")
            run = child_progress["runs"][0]
            verified = comparison.verify_run(Path(run["folder"]), actor, SEED, source, sampled_actor=sampled)
            if verified != run: raise ValueError("Match result changed on independent replay")
            check_frozen(); store_result(name, add_game_outcomes(verified))
        check_frozen(); unity_state(source, idle=True)
        progress.update(status="complete", stage="complete"); save()
        print("complete: " + str(folder), flush=True)
    except BaseException as error:
        progress.update(status="stopped", error=str(error)); save()
        raise


if __name__ == "__main__": main()
