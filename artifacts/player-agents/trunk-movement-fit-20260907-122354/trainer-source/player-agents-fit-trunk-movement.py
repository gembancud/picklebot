#!/usr/bin/env python3
"""Fit hidden movement features with a measured soft hit/shot output constraint."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

import torch
from player_actor import Actor, ROOT, file_hash, source_hash

spec = importlib.util.spec_from_file_location("contact_fit", ROOT / "scripts/player-agents-fit-contact-movement.py")
contact_fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contact_fit)

DEPENDENCIES = ("player-agents-fit-trunk-movement.py", "player-agents-fit-contact-movement.py", "player_actor.py", "player_ppo.py")
SETTINGS = dict(epochs=100, batch=1024, learningRate=.0001, seed=1000000, retentionWeight=1,
    sourceSampling="equal source mass, with replacement",
    trainableParameters="Both hidden layers and the two movement output rows and biases. Freeze the final hit and shot rows and biases, and log standard deviation.",
    loss="Existing near-contact-weighted movement loss plus mean squared change in the ten non-movement output logits on the same original observations. Select minimum equal-source development objective.",
    augmentation="None")


def validate_plan(plan):
    if plan["version"] != "trunk-movement-v1" or plan["sourceHash"] != source_hash() or plan["fit"] != SETTINGS:
        raise ValueError("Unreviewed hidden movement fit")
    path = ROOT / plan["dataPlan"]
    if file_hash(path) != plan["dataPlanHash"]: raise ValueError("Data plan changed")
    data = json.loads(path.read_text())
    if data["version"] != "near-contact-movement-v1" or data["sourceHash"] != plan["sourceHash"]:
        raise ValueError("Wrong source data plan")
    if file_hash(ROOT / plan["parentActor"]) != plan["parentActorHash"]:
        raise ValueError("Parent changed")
    return data


def objective(output, labels, reference):
    if (output.ndim != 2 or output.shape[1] != 12 or output.shape != reference.shape
            or not len(output) or labels.shape != (len(output), 5)
            or not torch.isfinite(output).all() or not torch.isfinite(reference).all()
            or not torch.isfinite(labels).all()):
        raise ValueError("Invalid movement fitting tensors")
    movement = contact_fit.movement_loss(output[:, :2], labels)
    retention = (output[:, 2:] - reference.detach()[:, 2:]).square().mean()
    return movement + retention, movement, retention


def mask_output_gradient(gradient):
    masked = gradient.clone()
    masked[2:] = 0
    return masked


def configure_training(actor):
    actor.requires_grad_(True)
    actor.log_std.requires_grad_(False)
    actor.layers[-1].weight.register_hook(mask_output_gradient)
    actor.layers[-1].bias.register_hook(mask_output_gradient)


def validate_frozen_parameters(parent, candidate):
    if len(parent.layers) != len(candidate.layers): raise ValueError("Actor topology changed")
    for a, b in zip(parent.layers, candidate.layers):
        if a.weight.shape != b.weight.shape or a.bias.shape != b.bias.shape: raise ValueError("Actor topology changed")
    a, b = parent.layers[-1], candidate.layers[-1]
    if not torch.equal(a.weight[2:], b.weight[2:]) or not torch.equal(a.bias[2:], b.bias[2:]):
        raise ValueError("Frozen hit or shot output parameters changed")
    if not torch.equal(parent.log_std, candidate.log_std): raise ValueError("Exploration changed")


def source_paths(data_plan, split):
    return [ROOT / data_plan[split + "Report"]] + [ROOT / p for p in data_plan[
        "additionalTraining" if split == "training" else "additionalDevelopment"]]


def load_sources(data_plan, metadata, split):
    banks, records = [], []
    for index, path in enumerate(source_paths(data_plan, split)):
        x, y, report, record = contact_fit.load_bank(path, split)
        for key in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
            if report[key] != metadata[key]: raise ValueError("Collection differs from runtime: " + key)
        if index == 0:
            expected = dict(seed=data_plan["collection"][split + "Seed"],
                rallies=data_plan["collection"][split + "Rallies"], baselineOpponent=False,
                teacherProbability=0, teacherDecisions=0, fixedShot=-1,
                actorHash=data_plan["parentActorHash"], actorDecisions=len(x))
            if any(report.get(k) != v for k, v in expected.items()): raise ValueError("Actor-state bank changed")
        banks.append((x, y)); records.append(record)
    if len(banks) != 4: raise ValueError("Expected four source banks")
    return banks, records


def metrics(output, labels, reference):
    total, movement, retention = objective(output, labels, reference)
    return dict(objective=float(total), movementLoss=float(movement), nonMovementLogitMSE=float(retention),
        hitFlipRate=float(((output[:, 2] >= 0) != (reference[:, 2] >= 0)).float().mean()),
        shotFlipRate=float((output[:, 3:].argmax(-1) != reference[:, 3:].argmax(-1)).float().mean()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "config/player-agents/trunk-movement-v1.json")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text()); data_plan = validate_plan(plan)
    torch.set_num_threads(2); torch.manual_seed(SETTINGS["seed"])
    parent_path = ROOT / plan["parentActor"]
    parent, metadata = Actor.load_export(parent_path); parent.eval().requires_grad_(False)
    if metadata["sourceHash"] != plan["sourceHash"]: raise ValueError("Parent source changed")
    actor, _ = Actor.load_export(parent_path); configure_training(actor)
    frozen = {str(args.plan): file_hash(args.plan), str(parent_path): file_hash(parent_path),
              str(ROOT / plan["dataPlan"]): plan["dataPlanHash"]}
    banks, provenance = {}, {}
    for split in ("training", "development"):
        banks[split], provenance[split] = load_sources(data_plan, metadata, split)
        for row in provenance[split]:
            frozen[row["report"]] = row["reportHash"]; frozen[str(ROOT / row["dataPath"])] = row["dataHash"]
    hashes = [r["dataHash"] for rows in provenance.values() for r in rows]
    if len(set(hashes)) != len(hashes): raise ValueError("Duplicate training/development bank")
    with torch.no_grad():
        reference = {s: [parent(x) for x, y in values] for s, values in banks.items()}
        parent_metrics = [metrics(o, y, o) for (x, y), o in zip(banks["development"], reference["development"])]
    x = torch.cat([x for x, y in banks["training"]]); y = torch.cat([y for x, y in banks["training"]])
    ref = torch.cat(reference["training"])
    weights = torch.cat([torch.full((len(a),), 1 / len(a), dtype=torch.float64) for a, b in banks["training"]])
    ids = torch.cat([torch.full((len(a),), i, dtype=torch.long) for i, (a, b) in enumerate(banks["training"])])
    optimizer = torch.optim.Adam([p for p in actor.parameters() if p.requires_grad], lr=SETTINGS["learningRate"])
    folder = ROOT / "artifacts/player-agents" / ("trunk-movement-fit-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False); (folder / "trainer-source").mkdir()
    for name in DEPENDENCIES:
        path = ROOT / "scripts" / name; shutil.copy2(path, folder / "trainer-source" / name); frozen[str(path)] = file_hash(path)
    shutil.copy2(args.plan, folder / "plan.json"); shutil.copy2(ROOT / plan["dataPlan"], folder / "data-plan.json")
    shutil.copy2(parent_path, folder / "parent.json")
    export_meta = {k: metadata[k] for k in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash")}
    export_meta.update(createdUtc=datetime.now(timezone.utc).isoformat(),
        method="supervised hidden-feature movement correction with soft hit/shot logit retention; not team-win RL",
        trainerHash=file_hash(__file__), dataHash=hashlib.sha256(json.dumps(provenance["training"], sort_keys=True).encode()).hexdigest(),
        planHash=file_hash(args.plan), parentActorHash=plan["parentActorHash"], parentTrainingSteps=metadata["trainingSteps"])
    history = []; updates = 0; best = float("inf"); started = time.perf_counter()
    print(folder, flush=True)
    for epoch in range(SETTINGS["epochs"]):
        order = torch.multinomial(weights, len(x), replacement=True)
        for indices in order.split(SETTINGS["batch"]):
            optimizer.zero_grad(set_to_none=True)
            loss, _, _ = objective(actor(x[indices]), y[indices], ref[indices])
            loss.backward(); torch.nn.utils.clip_grad_norm_(actor.parameters(), 1); optimizer.step(); updates += 1
        validate_frozen_parameters(parent, actor)
        with torch.no_grad():
            measured = [metrics(actor(dx), dy, dr) for (dx, dy), dr in zip(banks["development"], reference["development"])]
        selection = sum(m["objective"] for m in measured) / 4
        row = dict(epoch=epoch + 1, updates=updates, developmentMetrics=measured, selectionLoss=selection,
            sampledRowsPerSource=torch.bincount(ids[order], minlength=4).tolist())
        history.append(row)
        if selection < best:
            best = selection; export_meta["trainingSteps"] = metadata["trainingSteps"] + updates
            export_meta["fitUpdates"] = updates
            (folder / "actor.json").write_text(json.dumps(actor.export(export_meta)))
        if epoch % 10 == 0 or epoch == SETTINGS["epochs"] - 1: print(json.dumps(row), flush=True)
    saved, saved_meta = Actor.load_export(folder / "actor.json"); validate_frozen_parameters(parent, saved)
    if source_hash() != plan["sourceHash"] or any(file_hash(p) != digest for p, digest in frozen.items()):
        raise ValueError("Frozen inputs changed during fitting")
    dx = banks["development"][0][0][:32]
    with torch.no_grad(): outputs = saved(dx)
    (folder / "parity-input.json").write_text(json.dumps(dict(observations=[dict(values=r.tolist()) for r in dx],
        expected=[dict(values=r.tolist()) for r in outputs])))
    report = dict(status="complete", actorHash=file_hash(folder / "actor.json"), sourceHash=source_hash(),
        parentActorHash=plan["parentActorHash"], planHash=file_hash(args.plan), frozen=frozen,
        trainingSources=provenance["training"], developmentSources=provenance["development"],
        parentDevelopmentMetrics=parent_metrics, selectedUpdates=saved_meta["fitUpdates"], optimizerUpdates=updates,
        bestSelectionLoss=best, history=history, elapsedSeconds=time.perf_counter() - started,
        frozenOutputHeadParametersVerified=True,
        limitation="A supervised movement trial. Frozen output parameters do not imply unchanged outputs when hidden features change. No runtime, match or final acceptance claim.")
    (folder / "training.json").write_text(json.dumps(report, indent=2))
    print(folder, flush=True)


if __name__ == "__main__": main()
