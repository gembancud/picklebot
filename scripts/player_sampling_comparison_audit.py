"""Audit paired fixed/sampled policy results without treating sampling as a training gain."""
import argparse
import importlib.util
import json
from pathlib import Path
from player_actor import ROOT, file_hash, source_hash
from player_skill_gate_games import validate_game_outcome

spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/player-compare-models.py")
comparison = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparison)


def audit(folder, plan_path):
    plan = json.loads(plan_path.read_text()); progress = json.loads((folder / "progress.json").read_text())
    source = source_hash()
    if (plan["version"] != "sampled-policy-comparison-v1" or plan["sourceHash"] != source
            or plan["split"] != "development" or plan["sampledActor"] is not True
            or plan["seedBase"] != 1141000 or plan["gamesPerActor"] != 8 or plan["gamesPerGroup"] != 1
            or plan["sampleBaselineGroups"] != [4, 5, 6, 7]
            or plan["candidateTeams"] != [0, 0, 1, 1, 0, 0, 1, 1]
            or plan["swapPartnerIdentities"] != [False, True, False, True, False, True, False, True]
            or plan["flatPitchOffsetDegrees"] != 0 or len(plan["actors"]) != 2):
        raise ValueError("Comparison protocol differs")
    if (progress["status"] != "complete" or progress["sampledActor"] is not True
            or progress["sourceHash"] != source or progress["seed"] != plan["seedBase"]
            or progress["flatPitchOffsetDegrees"] != 0 or progress["experimentalContactOverride"] is not False
            or progress["allowHistoricalCandidates"] is not False
            or len(progress["actors"]) != 2 or len(progress["runs"]) != 2):
        raise ValueError("Incomplete or different sampled comparison")
    if file_hash(ROOT / "config/player-agents/evaluation-v1.json") != plan["protocolHash"]:
        raise ValueError("Final protocol changed")
    manifest_path = ROOT / "artifacts/player-agents/baseline-manifest.json"
    for path, digest in json.loads(manifest_path.read_text())["files"].items():
        if file_hash(ROOT / path) != digest: raise ValueError("Frozen baseline changed")
    names = ("player-compare-models.py", "player-agents-train-loop.py", "player_actor.py", "player_ppo.py",
             "player_acceptance.py", "player_contact_outcomes.py")
    for name in names:
        if file_hash(folder / name) != file_hash(ROOT / "scripts" / name):
            raise ValueError("Comparison driver dependency differs from its snapshot")
    results = []
    for entry, requested, run in zip(plan["actors"], progress["actors"], progress["runs"]):
        actor = ROOT / entry["path"]
        if (file_hash(actor) != entry["sha256"] or requested["sha256"] != entry["sha256"]
                or Path(requested["path"]).resolve() != actor.resolve()
                or run["actorHash"] != entry["sha256"]):
            raise ValueError("Actor order or identity differs")
        metadata = json.loads(actor.read_text())
        for key, path in (("protocolHash", "config/player-agents/evaluation-v1.json"),
                          ("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                          ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json")):
            if metadata[key] != file_hash(ROOT / path): raise ValueError("Actor environment changed")
        modes = []
        for sampled, target in ((False, ROOT / entry["fixedActionReference"]), (True, Path(run["folder"]))):
            verified = comparison.verify_run(target, actor, plan["seedBase"], source, sampled_actor=sampled)
            if sampled and verified != run: raise ValueError("Saved comparison summary differs from replay")
            if not sampled and verified["completionHash"] != entry["fixedActionCompletionHash"]:
                raise ValueError("Fixed-action reference changed")
            outcomes = [validate_game_outcome(json.loads((target / f"group-{g}.json").read_text())) for g in range(8)]
            verified["truncatedRallies"] = sum(o["truncatedRallies"] for o in outcomes)
            verified["truncatedFraction"] = verified["truncatedRallies"] / verified["rallies"]
            modes.append(verified)
        results.append(dict(role=entry["role"], actorHash=entry["sha256"], fixed=modes[0], sampled=modes[1]))
    return dict(folder=str(folder), sourceHash=source, planHash=file_hash(plan_path),
        progressHash=file_hash(folder / "progress.json"), driverHash=file_hash(folder / "player-compare-models.py"),
        results=results, evidenceChecksPassed=True,
        limitation="Paired development comparisons only. Compare training changes within each sampling mode. No final seeds, promotion or full-goal acceptance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path); parser.add_argument("plan", type=Path)
    args = parser.parse_args(); print(json.dumps(audit(args.folder, args.plan), indent=2))
