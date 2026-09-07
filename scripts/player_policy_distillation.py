"""Training-only teachers for a single standard player actor. No runtime selector."""
import json
import math

import torch
from torch.nn import functional as F

from player_actor import Actor, ROOT, file_hash, source_hash, teacher_data

NEUTRAL_PADDLE = [.19, .55, .46, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def neutral_paddle(observations):
    result = observations.clone()
    result[:, 25:37] = result.new_tensor(NEUTRAL_PADDLE)
    return result


def distillation_loss(output, target):
    if (output.shape != target.shape or output.ndim != 2 or output.shape[1] != 12
            or not len(output) or not torch.isfinite(output).all() or not torch.isfinite(target).all()):
        raise ValueError("Expected finite matching player outputs")
    target = target.detach()
    movement = (output[:, :2]-target[:, :2]).square().mean()
    probability = target[:, 2].sigmoid()
    hit = (probability*(F.softplus(-output[:, 2])-F.softplus(-target[:, 2]))
           + (1-probability)*(F.softplus(output[:, 2])-F.softplus(target[:, 2]))).mean().clamp_min(0)
    shot = F.kl_div(output[:, 3:].log_softmax(-1), target[:, 3:].softmax(-1), reduction="batchmean").clamp_min(0)
    return 4*movement + hit + .2*shot


def metrics(output, target):
    hits = target[:, 2] >= 0
    return dict(loss=float(distillation_loss(output, target)),
        movementMSE=float((Actor.movement(output[:, :2])-Actor.movement(target[:, :2])).square().mean()),
        hitAgreement=float(((output[:, 2] >= 0) == hits).float().mean()),
        shotAgreementOnTeacherHit=float((output[hits, 3:].argmax(-1) == target[hits, 3:].argmax(-1)).float().mean()) if hits.any() else None)


def source_weights(lengths):
    if not lengths or any(type(n) is not int or n <= 0 for n in lengths):
        raise ValueError("Nonempty positive source lengths required")
    return torch.cat([torch.full((n,), 1/n, dtype=torch.float64) for n in lengths])


def validate_plan(plan):
    if (plan.get("version") != "player-policy-distillation-v1" or plan.get("sourceHash") != source_hash()
            or plan.get("epochs") != 60 or plan.get("batch") != 1024 or plan.get("seed") != 1000000
            or plan.get("learningRate") != .0003 or plan.get("neutralPaddleProbability") != .5):
        raise ValueError("Unexpected distillation protocol")
    expected_hashes = {
        "contactModelHash": "Assets/Picklebot/Doubles/Models/contact.json",
        "protocolHash": "config/player-agents/evaluation-v1.json",
        "baselineManifestHash": "artifacts/player-agents/baseline-manifest.json"}
    for key, path in expected_hashes.items():
        if plan[key] != file_hash(ROOT/path):
            raise ValueError("Changed plan input: " + key)
    if [p["role"] for p in plan["teachers"]] != ["older", "short-return"]:
        raise ValueError("Unexpected training teachers")
    hashes = []
    for split in ("training", "development"):
        banks = plan[split]
        if len(banks) != 3 or [b["teacher"] for b in banks] != [0, 1, 0]:
            raise ValueError("Expected normal/short/deep sources with one teacher each")
        low, high = (1000000, 1100000) if split == "training" else (1100000, 1200000)
        if any(not low <= b["seed"] < high for b in banks):
            raise ValueError("Training and development seeds must stay separate")
        hashes.extend(b["dataHash"] for b in banks)
    if len(set(hashes)) != len(hashes):
        raise ValueError("Duplicate source data across banks")


def load_teachers(plan):
    teachers = []
    for entry in plan["teachers"]:
        path = ROOT/entry["path"]
        if file_hash(path) != entry["sha256"]:
            raise ValueError("Teacher checkpoint changed")
        actor, metadata = Actor.load_export(path)
        for key in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
            if metadata[key] != plan[key]:
                raise ValueError("Teacher physics/protocol mismatch")
        if metadata["sourceHash"] != entry["trainingSourceHash"] or metadata["trainingSteps"] <= 0:
            raise ValueError("Teacher training provenance mismatch")
        teachers.append(actor.eval().requires_grad_(False))
    return teachers


def load_banks(plan, split, teachers):
    result = []
    for entry in plan[split]:
        path = ROOT/entry["report"]
        x, _, report, digest = teacher_data(path, split)
        if (digest != entry["dataHash"] or report["seed"] != entry["seed"]
                or report["configurationHash"] != plan["configurationHash"]):
            raise ValueError("Source bank provenance changed")
        expected_profile = "kitchen" if entry["teacher"] == 1 else "deep"
        if "incoming-" in path.name and report.get("skillProfile") != expected_profile:
            raise ValueError("Source profile does not match its sole teacher")
        with torch.no_grad():
            target = teachers[entry["teacher"]](x)
            target_neutral = teachers[entry["teacher"]](neutral_paddle(x))
        result.append(dict(x=x, target=target, target_neutral=target_neutral,
            provenance=dict(**entry, reportHash=file_hash(path), rows=len(x),
                            inputRule="own 54 observations only; source id is training-only")))
    return result
