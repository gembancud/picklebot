"""Verify a single-actor distillation artifact and recompute development selection loss."""
import argparse
import json
import math
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash
from player_policy_distillation import load_banks, load_teachers, metrics, neutral_paddle, validate_plan


def audit(folder):
    torch.set_num_threads(2)
    plan = json.loads((folder/"plan.json").read_text()); validate_plan(plan)
    result = json.loads((folder/"result.json").read_text())
    actor, metadata = Actor.load_export(folder/"actor.json"); actor.eval()
    if (result["status"] != "complete" or result["actorHash"] != file_hash(folder/"actor.json")
            or result["planHash"] != file_hash(folder/"plan.json") or metadata["planHash"] != result["planHash"]
            or metadata["method"] != plan["method"] or metadata["sourceHash"] != plan["sourceHash"]
            or result["sourceHash"] != plan["sourceHash"] or metadata["teachers"] != plan["teachers"]):
        raise ValueError("Distillation result/checkpoint provenance mismatch")
    for key in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
        if metadata[key] != plan[key]:
            raise ValueError("Physics or protocol metadata mismatch")
    for name, digest in metadata["trainerSources"].items():
        if file_hash(folder/"trainer-source"/name) != digest:
            raise ValueError("Trainer snapshot changed")
    for i, teacher in enumerate(plan["teachers"]):
        if file_hash(folder/f"teacher-{i}.json") != teacher["sha256"]:
            raise ValueError("Teacher snapshot changed")
    teachers = load_teachers(plan)
    training = load_banks(plan, "training", teachers)
    development = load_banks(plan, "development", teachers)
    for key, banks in (("trainingSources", training), ("developmentSources", development)):
        if metadata[key] != [b["provenance"] for b in banks]:
            raise ValueError("Data provenance mismatch")
    rows = sum(len(b["x"]) for b in training)
    updates_per_epoch = math.ceil(rows/plan["batch"])
    history = result["history"]
    if (len(history) != plan["epochs"] or result["updates"] != updates_per_epoch*plan["epochs"]
            or result["trainingRows"] != rows or result["developmentRows"] != sum(len(b["x"]) for b in development)):
        raise ValueError("Training size mismatch")
    for epoch, record in enumerate(history, 1):
        if (record["epoch"] != epoch or record["updates"] != epoch*updates_per_epoch
                or len(record["sampledRowsPerSource"]) != 3 or sum(record["sampledRowsPerSource"]) != rows):
            raise ValueError("Training schedule mismatch")
    selected = min(history, key=lambda row: row["selectionLoss"])
    if (metadata["selectedEpoch"] != selected["epoch"] or result["selectedEpoch"] != selected["epoch"]
            or metadata["trainingSteps"] != selected["updates"] or result["selectedTrainingSteps"] != selected["updates"]):
        raise ValueError("Saved model does not match development selection")
    measured = []
    with torch.no_grad():
        for bank in development:
            measured.append(dict(original=metrics(actor(bank["x"]), bank["target"]),
                                 neutral=metrics(actor(neutral_paddle(bank["x"])), bank["target_neutral"])))
    selection_loss = sum(v["original"]["loss"]+v["neutral"]["loss"] for v in measured)/(2*len(measured))
    if abs(selection_loss-selected["selectionLoss"]) > 1e-7 or abs(selection_loss-result["selectionLoss"]) > 1e-7:
        raise ValueError("Checkpoint validation loss does not replay")
    parity = json.loads((folder/"unity-parity.json").read_text())
    if (not parity["passed"] or parity["cases"] != 48 or parity["maximumError"] >= .0001
            or parity["actorHash"] != result["actorHash"] or parity["sourceHash"] != plan["sourceHash"]
            or parity["inputHash"] != file_hash(folder/"parity-input.json")):
        raise ValueError("Missing matching Unity parity proof")
    return dict(folder=str(folder), actorHash=result["actorHash"], sourceHash=plan["sourceHash"],
                planHash=result["planHash"], resultHash=file_hash(folder/"result.json"),
                schema=metadata["version"], layerShapes=[(l.in_features, l.out_features) for l in actor.layers],
                selectedEpoch=selected["epoch"], trainingSteps=metadata["trainingSteps"],
                selectionLossReplayed=selection_loss, trainingRows=rows, developmentRows=result["developmentRows"],
                developmentMetrics=measured, unityParity=parity, wallSeconds=result["wallSeconds"],
                limitation="Training-artifact proof only. One ordinary player actor, no runtime selector. Physical return and team-win tests are separate.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder", type=Path)
    print(json.dumps(audit(parser.parse_args().folder), indent=2))
