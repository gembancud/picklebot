"""Verify the saved hidden-feature movement trial against its frozen data and plan."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash, source_hash

spec = importlib.util.spec_from_file_location("trunk_fit", ROOT / "scripts/player-agents-fit-trunk-movement.py")
fit = importlib.util.module_from_spec(spec); spec.loader.exec_module(fit)


def audit(folder):
    torch.set_num_threads(2)
    report = json.loads((folder / "training.json").read_text())
    plan = json.loads((folder / "plan.json").read_text()); data_plan = fit.validate_plan(plan)
    if (report["status"] != "complete" or report["sourceHash"] != source_hash()
            or report["planHash"] != file_hash(folder / "plan.json")
            or report["actorHash"] != file_hash(folder / "actor.json")
            or report["parentActorHash"] != file_hash(folder / "parent.json")
            or report["parentActorHash"] != plan["parentActorHash"]
            or file_hash(folder / "data-plan.json") != plan["dataPlanHash"]):
        raise ValueError("Trial identity differs")
    for path, digest in report["frozen"].items():
        if file_hash(path) != digest: raise ValueError("Frozen input changed: " + path)
    for name in fit.DEPENDENCIES:
        if file_hash(folder / "trainer-source" / name) != report["frozen"][str(ROOT / "scripts" / name)]:
            raise ValueError("Trainer snapshot changed")
    parent, pm = Actor.load_export(folder / "parent.json"); actor, metadata = Actor.load_export(folder / "actor.json")
    fit.validate_frozen_parameters(parent, actor)
    for key in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
        if metadata[key] != pm[key]: raise ValueError("Model environment differs")
    if (metadata["parentActorHash"] != report["parentActorHash"] or metadata["planHash"] != report["planHash"]
            or metadata["trainerHash"] != file_hash(folder / "trainer-source" / fit.DEPENDENCIES[0])
            or metadata["parentTrainingSteps"] != pm["trainingSteps"]):
        raise ValueError("Actor lineage differs")
    digest = hashlib.sha256(json.dumps(report["trainingSources"], sort_keys=True).encode()).hexdigest()
    if metadata["dataHash"] != digest: raise ValueError("Training data identity differs")
    steps = math.ceil(sum(r["rows"] for r in report["trainingSources"]) / plan["fit"]["batch"])
    history = report["history"]
    if len(history) != plan["fit"]["epochs"]: raise ValueError("Incomplete fit")
    for index, row in enumerate(history):
        if (row["epoch"] != index + 1 or row["updates"] != (index + 1) * steps
                or len(row["sampledRowsPerSource"]) != 4 or any(n <= 0 for n in row["sampledRowsPerSource"])
                or sum(row["sampledRowsPerSource"]) != sum(r["rows"] for r in report["trainingSources"])
                or len(row["developmentMetrics"]) != 4): raise ValueError("Training schedule differs")
        for m in row["developmentMetrics"]:
            if not all(math.isfinite(v) and v >= 0 for v in m.values()): raise ValueError("Invalid fitting metric")
            if m["hitFlipRate"] > 1 or m["shotFlipRate"] > 1: raise ValueError("Invalid action-change fraction")
            if abs(m["objective"] - m["movementLoss"] - m["nonMovementLogitMSE"]) > 1e-6:
                raise ValueError("Loss components differ")
        if abs(row["selectionLoss"] - sum(m["objective"] for m in row["developmentMetrics"]) / 4) > 1e-10:
            raise ValueError("Selection metric differs")
    selected = min(history, key=lambda r: r["selectionLoss"])
    if (selected["updates"] != report["selectedUpdates"] or selected["updates"] != metadata["fitUpdates"]
            or metadata["trainingSteps"] != pm["trainingSteps"] + selected["updates"]
            or report["optimizerUpdates"] != steps * len(history)
            or report["bestSelectionLoss"] != selected["selectionLoss"]):
        raise ValueError("Wrong saved checkpoint")
    sources = []; hashes = []
    for split in ("training", "development"):
        banks, records = fit.load_sources(data_plan, pm, split)
        if records != report[split + "Sources"]: raise ValueError("Source provenance differs")
        for index, ((x, y), record) in enumerate(zip(banks, records)):
            hashes.append(record["dataHash"])
            with torch.no_grad():
                a, b = parent(x), actor(x)
                before, after = fit.metrics(a, y, a), fit.metrics(b, y, a)
            if split == "development":
                for expected, measured in ((report["parentDevelopmentMetrics"][index], before),
                                          (selected["developmentMetrics"][index], after)):
                    if expected.keys() != measured.keys() or any(abs(expected[k] - measured[k]) > 1e-6 for k in expected):
                        raise ValueError("Development checkpoint replay differs")
            sources.append(dict(split=split, index=index, rows=len(x), criticalRows=record["criticalRows"],
                dataHash=record["dataHash"], parent=before, candidate=after))
    if len(set(hashes)) != len(hashes): raise ValueError("Duplicate source bank")
    return dict(folder=str(folder), actorHash=report["actorHash"], parentActorHash=report["parentActorHash"],
        sourceHash=report["sourceHash"], planHash=report["planHash"], trainingHash=file_hash(folder / "training.json"),
        selectedEpoch=selected["epoch"], selectedUpdates=selected["updates"], optimizerUpdates=report["optimizerUpdates"],
        fittingSeconds=report["elapsedSeconds"], frozenOutputHeadParametersVerified=True,
        unchangedExplorationVerified=True, motorChecksPassed=True, sources=sources,
        limitation="Independent source, parameter and output replay checks. Soft hit/shot retention does not guarantee unchanged runtime actions. Supervised prediction loss is not match acceptance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder", type=Path)
    print(json.dumps(audit(parser.parse_args().folder), indent=2))
