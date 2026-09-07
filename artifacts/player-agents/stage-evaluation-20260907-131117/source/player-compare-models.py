#!/usr/bin/env python3
"""Run the same eight development games for each saved actor. Never final seeds."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from player_actor import ROOT, file_hash, source_hash
from player_acceptance import validate_runner_artifacts, validate_player_identities
from player_ppo import validate_motor_metrics
from player_contact_outcomes import validate_contact_override

spec = importlib.util.spec_from_file_location("player_train_loop", ROOT / "scripts/player-agents-train-loop.py")
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


def actor_provenance(metadata, source, allow_historical=False):
    training_source = metadata.get("sourceHash")
    if not isinstance(training_source, str) or not training_source:
        raise ValueError("Actor training source is missing")
    historical = training_source != source
    if historical and not allow_historical:
        raise ValueError("Historical actor requires explicit development permission")
    return dict(trainingSourceHash=training_source, historicalCandidate=historical)


def validate_schedule(plan, seed, sampled_actor=False):
    if (type(sampled_actor) is not bool or not 1100000 <= seed <= 1199992 or plan["split"] != "development"
            or plan["sampledActor"] is not sampled_actor or plan["gamesPerGroup"] != 1
            or plan["seedList"] != list(range(seed, seed + 8)) or len(plan["groups"]) != 8):
        raise ValueError("Expected eight development games with the requested actor sampling mode")
    for group, item in enumerate(plan["groups"]):
        expected = dict(group=group, candidateTeam=(group // 2) % 2,
                        sampleBaseline=group >= 4, swapPartnerIdentities=bool(group & 1), seeds=[seed + group])
        if item != expected:
            raise ValueError("Paired development schedule differs")


def validate_comparison_override(plan, report, expected_offset):
    if not math.isfinite(expected_offset) or abs(expected_offset) > 6:
        raise ValueError("Invalid development contact correction")
    for record in (plan, report):
        if (record.get("flatPitchOffsetDegrees", 0) != expected_offset
                or record.get("experimentalContactOverride", False) is not (expected_offset != 0)):
            raise ValueError("Comparison contact correction differs from the request")
    if plan.get("candidateContactParameters") != report.get("candidateContactParameters"):
        raise ValueError("Comparison contact parameters differ from the reserved plan")


def verify_run(folder, actor, seed, source, flat_pitch_offset=0, sampled_actor=False):
    provenance = actor_provenance(json.loads(actor.read_text()), source, True)
    plan = json.loads((folder / "evaluation-plan.json").read_text())
    validate_schedule(plan, seed, sampled_actor)
    completion = json.loads((folder / "completion.json").read_text())
    protocol = json.loads((ROOT / "config/player-agents/evaluation-v1.json").read_text())
    if (completion["status"] != "complete" or completion["games"] != 8
            or completion["actorHash"] != file_hash(actor) or completion["sourceHash"] != source
            or set(completion["reportHashes"]) != {f"group-{g}.json" for g in range(8)}):
        raise ValueError("Incomplete or changed comparison run")
    results = []
    for group in range(8):
        path = folder / f"group-{group}.json"
        report = json.loads(path.read_text())
        validate_comparison_override(plan, report, flat_pitch_offset)
        validate_contact_override(report, json.loads((ROOT / "Assets/Picklebot/Doubles/Models/contact.json").read_text()))
        validate_runner_artifacts(path, report, ROOT, file_hash)
        validate_motor_metrics(report)
        if (file_hash(path) != completion["reportHashes"][path.name] or report["status"] != "complete"
                or report["sourceHash"] != source or report["actorHash"] != file_hash(actor)
                or report["actorTrainingSourceHash"] != provenance["trainingSourceHash"]
                or report["historicalCandidate"] is not provenance["historicalCandidate"]
                or len(report["games"]) != 1 or report["split"] != "development"):
            raise ValueError("Comparison report differs from the reserved run")
        game = report["games"][0]
        validate_player_identities(game, report["swapPartnerIdentities"], protocol)
        if not game["complete"]:
            raise ValueError("Comparison game did not complete; retain the failure")
        team = game["candidateTeam"]
        results.append(dict(group=group, seed=game["gameSeed"], candidateTeam=team,
                            sampledBaseline=group >= 4, won=game["winner"] == team, score=game["score"],
                            rallies=len(report["rallies"]),
                            rallyWins=sum(r["winner"] == team for r in report["rallies"]),
                            legalReturns=sum(game["metrics"]["legalHits"][team*2:team*2+2])))
    correction = dict(flatPitchOffsetDegrees=flat_pitch_offset, experimentalContactOverride=True) if flat_pitch_offset != 0 else {}
    return dict(folder=str(folder), actorHash=file_hash(actor), sourceHash=source, sampledActor=sampled_actor, **correction,
                **provenance,
                completionHash=file_hash(folder / "completion.json"),
                games=results, wins=sum(g["won"] for g in results),
                rallies=sum(g["rallies"] for g in results),
                rallyWins=sum(g["rallyWins"] for g in results),
                legalReturns=sum(g["legalReturns"] for g in results),
                wallSeconds=completion["wallSeconds"], evidenceChecksPassed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actors", type=Path, nargs="+")
    parser.add_argument("--seed", type=int, default=1141000)
    parser.add_argument("--sampled-actor", action="store_true",
                        help="Explicit development-only comparison of seeded sampled actions. Default remains fixed actions.")
    parser.add_argument("--flat-pitch-offset", type=float, default=0,
                        help="Temporary candidate-only development correction, at most six degrees; never final acceptance")
    parser.add_argument("--allow-historical-candidates", action="store_true",
                        help="Development only: preserve old training hashes while testing on the current runtime")
    args = parser.parse_args()
    if not 1 <= len(args.actors) <= 4 or not 1100000 <= args.seed <= 1199992:
        parser.error("Use one to four actors and an eight-seed development block")
    if not math.isfinite(args.flat_pitch_offset) or abs(args.flat_pitch_offset) > 6:
        parser.error("Development flat-pitch correction must be within six degrees")
    actors = [path.resolve() for path in args.actors]
    source = source_hash()
    hashes = [file_hash(path) for path in actors]
    provenance = [actor_provenance(json.loads(path.read_text()), source, args.allow_historical_candidates) for path in actors]
    folder = ROOT / "artifacts/player-agents" / ("model-comparison-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    for name in (Path(__file__).name, "player-agents-train-loop.py", "player_actor.py", "player_ppo.py", "player_acceptance.py", "player_contact_outcomes.py"):
        shutil.copy2(ROOT / "scripts" / name, folder / name)
    progress = dict(status="running", seed=args.seed, sourceHash=source, sampledActor=args.sampled_actor,
                    flatPitchOffsetDegrees=args.flat_pitch_offset, experimentalContactOverride=args.flat_pitch_offset != 0,
                    allowHistoricalCandidates=args.allow_historical_candidates,
                    actors=[dict(path=str(p), sha256=h, **record) for p, h, record in zip(actors, hashes, provenance)], runs=[],
                    limitation="Paired development only. No automatic promotion and no final acceptance.")
    def save():
        (folder / "progress.json").write_text(json.dumps(progress, indent=2))
    save(); print(folder, flush=True)
    try:
        for actor, actor_hash in zip(actors, hashes):
            if source_hash() != source or file_hash(actor) != actor_hash:
                raise ValueError("Comparison source or actor changed")
            state = loop.evaluate('return new { playing = UnityEditor.EditorApplication.isPlaying, running = '
                                  'Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || '
                                  'UnityEditor.EditorApplication.update.GetInvocationList().Any(d => '
                                  'd.Method.Name.Contains("TickFinal")) };')
            if not state["playing"] or state["running"]:
                raise RuntimeError("Finish the active job and enter Play before comparison")
            loop.evaluate('UnityEditor.SessionState.SetBool("Picklebot.Final.Development", true);'
                          'UnityEditor.SessionState.SetInt("Picklebot.Final.GamesPerGroup", 1);'
                          f'UnityEditor.SessionState.SetBool("Picklebot.Final.SampledActor", {str(args.sampled_actor).lower()});'
                          f'UnityEditor.SessionState.SetFloat("Picklebot.Final.FlatPitchOffset", {args.flat_pitch_offset}f);'
                          f'UnityEditor.SessionState.SetBool("Picklebot.Final.AllowHistoricalCandidate", {str(args.allow_historical_candidates).lower()});'
                          f'UnityEditor.SessionState.SetInt("Picklebot.Final.Seed", {args.seed});'
                          'UnityEditor.SessionState.SetString("Picklebot.Final.ActorPath", ' + json.dumps(str(actor)) + '); return true;')
            response = subprocess.run(["unity", "command", "eval_file", "scripts/player-final-evaluate.cs", "--format", "json"],
                                      cwd=ROOT, capture_output=True, text=True, timeout=45)
            target = (ROOT / loop.unity_value(json.loads(response.stdout))).resolve()
            target.relative_to(ROOT / "artifacts/player-agents")
            progress["activeRun"] = str(target); save()
            print("Started " + str(actor.parent.name) + ": " + str(target), flush=True)
            deadline = time.monotonic() + 1800
            while True:
                time.sleep(20)
                state = loop.evaluate('return new { running = UnityEditor.EditorApplication.update.GetInvocationList().Any(d => '
                                      'd.Method.Name.Contains("TickFinal")), status = UnityEditor.SessionState.GetString("Picklebot.Final.Status", "") };')
                print(state["status"], flush=True)
                if not state["running"]:
                    if state["status"] != "complete: " + str(target.relative_to(ROOT)):
                        raise RuntimeError("Comparison did not complete: " + state["status"])
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("Observation wait expired. Inspect this same run before any restart.")
            progress["runs"].append(verify_run(target, actor, args.seed, source, args.flat_pitch_offset, args.sampled_actor)); save()
        loop.evaluate('UnityEditor.SessionState.SetFloat("Picklebot.Final.FlatPitchOffset", 0);'
                      'UnityEditor.SessionState.SetBool("Picklebot.Final.SampledActor", false); return true;')
        progress["status"] = "complete"; progress.pop("activeRun", None); save()
    except BaseException as error:
        progress.update(status="stopped", error=str(error)); save()
        raise


if __name__ == "__main__": main()
