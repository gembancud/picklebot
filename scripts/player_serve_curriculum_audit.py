"""Verify serve-flight corrective fitting without using diagnostic cases as training data."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash, source_hash, teacher_data


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/"scripts"/filename)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def validate_source_schedule(sources, plan, split):
    key = "additionalTraining" if split == "training" else "additionalDevelopment"
    if len(sources) != 1 + len(plan[key]) or [s["report"] for s in sources[1:]] != plan[key]:
        raise ValueError("Source schedule differs from frozen plan")
    primary = plan.get("trainingReport" if split == "training" else "developmentReport")
    if primary is not None and sources[0]["report"] != primary:
        raise ValueError("Primary source differs from frozen plan")


def phase_coverage(tensors, required):
    names = ("serve", "serveFlight", "returnFlight", "rally", "dead")
    counts = {name: 0 for name in names}
    for x, _ in tensors:
        phases = x[:, 39:44]
        if not (((phases == 0) | (phases == 1)).all() and (phases.sum(-1) == 1).all()):
            raise ValueError("Invalid phase indicators")
        for name, count in zip(names, phases.sum(0).int().tolist()):
            counts[name] += count
    if any(name not in counts or counts[name] == 0 for name in required):
        raise ValueError("Required training phase has no examples")
    return counts


def audit(folder, plan_path):
    torch.set_num_threads(2)
    imitation = module("serve_imitation", "player-agents-imitate.py")
    refresh = module("serve_refresh", "player-agents-refresh.py")
    plan = json.loads(plan_path.read_text()); training = json.loads((folder/"training.json").read_text())
    actor, metadata = Actor.load_export(folder/"actor.json")
    parent, parent_meta = Actor.load_export(ROOT/plan["parentActor"])
    config = training["configuration"]; fit = plan["fit"]
    for key in ("hidden", "batch", "learningRate", "neutralPaddleProbability", "retentionWeight"):
        if config[key] != fit[key]: raise ValueError("Fit differs from frozen plan")
    if (not config["primaryServeFlightOnly"] or not config["balancedTrainingSources"]
            or training["epochs"] != fit["epochs"] or training["actorHash"] != file_hash(folder/"actor.json")
            or plan["parentActorHash"] != file_hash(ROOT/plan["parentActor"])
            or metadata["parentActorHash"] != plan["parentActorHash"]
            or metadata["parentTrainingSteps"] != parent_meta["trainingSteps"]):
        raise ValueError("Actor lineage, schedule, or phase selection differs")
    if any(m["sourceHash"] != source_hash() for m in (plan, training, metadata, parent_meta)):
        raise ValueError("Runtime source changed")
    digest = hashlib.sha256((folder/"trainer-source/player-agents-imitate.py").read_bytes()
                           + (folder/"trainer-source/player_actor.py").read_bytes()).hexdigest()
    if metadata["trainerHash"] != digest or training["trainerHash"] != digest:
        raise ValueError("Trainer snapshot changed")
    banks = {}; ownership = {}; hashes = []; coverage = {}
    for split, key in (("training", "trainingSources"), ("development", "developmentSources")):
        sources = training[key]
        validate_source_schedule(sources, plan, split)
        tensors = []; details = []
        for i, entry in enumerate(sources):
            x,y,report,digest = teacher_data(ROOT/entry["report"],split)
            refresh.validate_teacher_motors(report)
            if digest != entry["dataHash"]: raise ValueError("Source data changed")
            hashes.append(digest)
            if i == 0:
                expected_seed = plan["collection"]["trainingSeed" if split=="training" else "developmentSeed"]
                if (report["seed"] != expected_seed or report["baselineOpponent"]
                        or report["teacherProbability"] != 1 or report["fixedShot"] != -1
                        or report["rallies"] != plan["collection"]["trainingRallies" if split=="training" else "developmentRallies"]):
                    raise ValueError("Wrong real-serve teacher distribution")
                x,y,subset = imitation.serve_flight_subset(x,y)
                if any(entry[k] != value for k,value in subset.items()):
                    raise ValueError("Selected serve-flight row identity differs")
                ownership[split] = dict(totalRows=subset["originalRows"], selectedRows=len(x),
                    receiverRows=int((x[:,45]>.5).sum()), attemptingRows=int((y[:,2]>.5).sum()),
                    servingTeamPerspectiveRows=int((x[:,47]>.5).sum()), collectionSeconds=report["wallSeconds"],
                    subsetIndicesHash=subset["selectedIndicesHash"])
            if len(x) != entry["rows"]: raise ValueError("Selected row count differs")
            if any(report[k] != metadata[k] for k in ("configurationHash","contactModelHash","protocolHash","baselineManifestHash")):
                raise ValueError("Source physics/protocol differs from model")
            tensors.append((x,y)); details.append(dict(entry,reportHash=file_hash(ROOT/entry["report"])))
        combined = hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
        if combined != training["dataHash" if split=="training" else "developmentDataHash"]:
            raise ValueError("Combined source identity differs")
        banks[split] = tensors
        coverage[split] = phase_coverage(tensors, plan.get("requiredTrainingPhases", []))
    if len(hashes) != len(set(hashes)): raise ValueError("Duplicate data across partitions")
    rows = sum(len(x) for x,y in banks["training"]); steps_per_epoch = math.ceil(rows/fit["batch"])
    history = training["history"]
    if (len(history) != fit["epochs"] or training["optimizerUpdates"] != steps_per_epoch*fit["epochs"]
            or training["trainingRows"] != rows
            or training["developmentRows"] != sum(len(x) for x,y in banks["development"])):
        raise ValueError("Fit size differs")
    for epoch, record in enumerate(history,1):
        if record["epoch"] != epoch or sum(record["sampledRowsPerSource"]) != rows:
            raise ValueError("Epoch sampling size differs")
    selected = min(history,key=lambda h:h["selectionLoss"])
    if metadata["trainingSteps"] != selected["epoch"]*steps_per_epoch:
        raise ValueError("Saved model is not the selected epoch")
    metrics = []
    with torch.no_grad():
        for x,y in banks["development"]:
            _, original = imitation.loss_and_metrics(actor,x,y)
            neutral = x.clone(); neutral[:,25:37] = neutral.new_tensor([.19,.55,.46,0,0,1,0,0,0,0,0,0])
            _, cleared = imitation.loss_and_metrics(actor,neutral,y)
            metrics.append(dict(original=original,neutral=cleared))
    loss = sum(m["original"]["loss"]+m["neutral"]["loss"] for m in metrics)/len(metrics)
    if abs(loss-selected["selectionLoss"]) > 1e-6 or abs(loss-training["bestSelectionLoss"]) > 1e-6:
        raise ValueError("Selected development loss does not replay")
    parity = json.loads((folder/"unity-parity.json").read_text())
    if (not parity["passed"] or parity["actorHash"] != file_hash(folder/"actor.json")
            or parity["sourceHash"] != source_hash() or parity["cases"] != 32
            or not 0 <= parity["maximumError"] < .0001
            or parity["inputHash"] != file_hash(folder/"parity-input.json")):
        raise ValueError("Unity export parity differs")
    return dict(folder=str(folder),actorHash=file_hash(folder/"actor.json"),planHash=file_hash(plan_path),
        trainingHash=file_hash(folder/"training.json"),sourceHash=source_hash(),parentActorHash=plan["parentActorHash"],
        selectedEpoch=selected["epoch"],selectedTrainingSteps=metadata["trainingSteps"],optimizerUpdates=training["optimizerUpdates"],
        trainingRows=rows,developmentRows=training["developmentRows"],serveSources=ownership,phaseCoverage=coverage,
        selectionLossReplayed=loss,developmentMetrics=metrics,parity=parity,fitSeconds=training["elapsedSeconds"],
        limitation="Verified supervised corrective fit on real-serve labels. No diagnostic examples enter fitting. Physical serve/return tests and competitive game strength are separate requirements.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder",type=Path); parser.add_argument("plan",type=Path)
    args=parser.parse_args(); print(json.dumps(audit(args.folder,args.plan),indent=2))
