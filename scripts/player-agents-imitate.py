#!/usr/bin/env python3
"""Fit a disclosed imitation warm start, with separate development seeds."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import torch
from torch.nn import functional as F

from player_actor import Actor, ROOT, file_hash, source_hash, teacher_data


def loss_and_metrics(model, x, y):
    out = model(x)
    movement_error = (model.movement(out[:, :2]) - y[:, :2]).square().mean(dim=1)
    weight = 1 + 4 * y[:, 2] + 2 * torch.linalg.vector_norm(y[:, :2], dim=1)
    move_loss = (movement_error * weight).mean()
    hit_loss = F.binary_cross_entropy_with_logits(out[:, 2], y[:, 2], pos_weight=torch.tensor(3.0))
    hits = y[:, 2] > 0.5
    shot_loss = F.cross_entropy(out[hits, 3:], y[hits, 3].long()) if hits.any() else out.sum() * 0
    loss = 4 * move_loss + hit_loss + .2 * shot_loss
    return loss, {"loss": loss.item(), "movementMSE": movement_error.mean().item(),
                  "hitAccuracy": ((out[:, 2] >= 0) == hits).float().mean().item(),
                  "hitRecall": (out[hits, 2] >= 0).float().mean().item() if hits.any() else 0,
                  "shotAccuracyOnHit": (out[hits, 3:].argmax(dim=1) == y[hits, 3]).float().mean().item() if hits.any() else 0}


def initial_model(path, hidden, report, allow_historical=False):
    if not path:
        if allow_historical:
            raise ValueError("Historical initialization requires an initial actor")
        return Actor(hidden), None
    model, parent = Actor.load_export(path)
    if not isinstance(parent.get("sourceHash"), str) or not parent["sourceHash"]:
        raise ValueError("Initial actor is missing sourceHash")
    if parent["sourceHash"] != source_hash() and not allow_historical:
        raise ValueError("Initial actor provenance differs: sourceHash")
    for key, expected in (("configurationHash", report["configurationHash"]),
                          ("contactModelHash", report["contactModelHash"]), ("protocolHash", report["protocolHash"]),
                          ("baselineManifestHash", report["baselineManifestHash"])):
        if parent.get(key) != expected:
            raise ValueError("Initial actor provenance differs: " + key)
    if model.layers[0].out_features != hidden:
        raise ValueError("Initial actor width differs from --hidden")
    if type(parent.get("trainingSteps")) is not int or parent["trainingSteps"] < 1:
        raise ValueError("Initial actor has no recorded training")
    return model, parent


def source_sampling_weights(lengths):
    """Give each training source equal expected mass, not each stored row."""
    if not lengths or any(type(n) is not int or n <= 0 for n in lengths):
        raise ValueError("Training source lengths must be positive integers")
    return torch.cat([torch.full((n,), 1.0 / n, dtype=torch.float64) for n in lengths])


def serve_flight_subset(x, y):
    """Select the pre-return phase only after the complete source bank is validated."""
    if x.ndim != 2 or x.shape[1] != 54 or y.shape != (len(x), 4) or not torch.isfinite(x).all():
        raise ValueError("Invalid serve-flight source tensors")
    phases = x[:, 39:44]
    if not (((phases == 0) | (phases == 1)).all() and (phases.sum(-1) == 1).all()):
        raise ValueError("Invalid phase indicators")
    indices = (x[:, 40] == 1).nonzero(as_tuple=False).flatten()
    if not len(indices): raise ValueError("No serve-flight examples")
    provenance = dict(originalRows=len(x), selectedPhase="phase.serveFlight", observationIndex=40,
        selectedIndicesHash=hashlib.sha256(json.dumps(indices.tolist(), separators=(",", ":")).encode()).hexdigest())
    return x[indices].clone(), y[indices].clone(), provenance


def average_source_metrics(metrics):
    if not metrics or any(set(m) != set(metrics[0]) for m in metrics):
        raise ValueError("Validation sources need matching metric fields")
    return {key: sum(m[key] for m in metrics) / len(metrics) for key in metrics[0]}


def validate_retention_options(weight, initial_actor):
    if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
        raise ValueError("Retention weight must be finite and non-negative")
    if weight > 0 and not initial_actor:
        raise ValueError("Retention requires an initial trained actor")


def retention_from_outputs(current, reference):
    """A soft training penalty, not a guarantee that skills or wins are retained."""
    if (current.shape != reference.shape or current.ndim != 2 or current.shape[1] != 12
            or not len(current) or not torch.isfinite(current).all() or not torch.isfinite(reference).all()):
        raise ValueError("Expected finite matching actor outputs")
    reference = reference.detach()
    movement_latent = (current[:, :2] - reference[:, :2]).square().mean()
    old_hit, new_hit = reference[:, 2], current[:, 2]
    probability = old_hit.sigmoid()
    hit_kl = (probability * (F.softplus(-new_hit) - F.softplus(-old_hit))
              + (1-probability) * (F.softplus(new_hit) - F.softplus(old_hit))).mean().clamp_min(0)
    shot_kl = F.kl_div(current[:, 3:].log_softmax(-1), reference[:, 3:].softmax(-1), reduction="batchmean").clamp_min(0)
    loss = 4 * movement_latent + hit_kl + .2 * shot_kl
    return loss, dict(retentionLoss=loss.item(), retentionMovementLatentMSE=movement_latent.item(),
        retentionMovementMSE=(Actor.movement(current[:, :2])-Actor.movement(reference[:, :2])).square().mean().item(),
        retentionHitKL=hit_kl.item(), retentionShotKL=shot_kl.item(),
        retentionHitFlipRate=((new_hit >= 0) != (old_hit >= 0)).float().mean().item(),
        retentionShotFlipRate=(current[:, 3:].argmax(-1) != reference[:, 3:].argmax(-1)).float().mean().item())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_report", type=Path)
    parser.add_argument("development_report", type=Path)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch", type=int, default=1024)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=.001)
    parser.add_argument("--neutral-paddle-probability", type=float, default=0.8)
    parser.add_argument("--additional-training-report", type=Path, action="append", default=[])
    parser.add_argument("--additional-development-report", type=Path, action="append", default=[])
    parser.add_argument("--balance-training-sources", action="store_true",
                        help="Sample sources equally with replacement; record per-source sampled counts")
    parser.add_argument("--primary-serve-flight-only", action="store_true",
                        help="Use only serve-flight rows from the primary training/development reports; leave additional banks unchanged")
    parser.add_argument("--initial-actor", type=Path, help="Saved actor for supervised corrective fine-tuning")
    parser.add_argument("--allow-historical-initial", action="store_true",
                        help="Explicitly reuse older-runtime weights; all training data must still match the current runtime")
    parser.add_argument("--retention-weight", type=float, default=0,
                        help="Optional soft penalty against initial-actor outputs on recorded training observations; not a skill guarantee")
    args = parser.parse_args()
    try:
        validate_retention_options(args.retention_weight, args.initial_actor)
    except ValueError as error:
        parser.error(str(error))
    if args.epochs < 1 or args.batch < 1 or args.hidden < 1 or args.hidden > 256:
        parser.error("Invalid training size")
    if not 0 <= args.neutral_paddle_probability <= 1:
        parser.error("Paddle neutralization probability must be between zero and one")
    torch.manual_seed(1000000); torch.set_num_threads(2)
    x, y, report, data_hash = teacher_data(args.training_report, "training")
    primary_subset = {}
    if args.primary_serve_flight_only: x, y, primary_subset = serve_flight_subset(x, y)
    training_sources = [{"report": str(args.training_report), "dataHash": data_hash, "rows": len(x), **primary_subset}]
    for extra_path in args.additional_training_report:
        ex, ey, extra, extra_hash = teacher_data(extra_path, "training")
        if extra["configurationHash"] != report["configurationHash"]:
            raise ValueError("Training configurations differ")
        training_sources.append({"report": str(extra_path), "dataHash": extra_hash, "rows": len(ex)})
        x, y = torch.cat((x, ex)), torch.cat((y, ey))
    if len(training_sources) > 1:
        data_hash = hashlib.sha256(json.dumps(training_sources, sort_keys=True).encode()).hexdigest()
    dx, dy, development, dev_hash = teacher_data(args.development_report, "development")
    if development["configurationHash"] != report["configurationHash"]:
        raise ValueError("Training and development configurations differ")
    development_subset = {}
    if args.primary_serve_flight_only: dx, dy, development_subset = serve_flight_subset(dx, dy)
    development_sources = [{"report": str(args.development_report), "dataHash": dev_hash, "rows": len(dx), **development_subset}]
    validation_tensors = [(dx, dy)]
    for extra_path in args.additional_development_report:
        ex, ey, extra, extra_hash = teacher_data(extra_path, "development")
        if extra["configurationHash"] != report["configurationHash"]:
            raise ValueError("Training and development configurations differ")
        development_sources.append({"report": str(extra_path), "dataHash": extra_hash, "rows": len(ex)})
        validation_tensors.append((ex, ey))
    for sources in (training_sources, development_sources):
        if len({item["dataHash"] for item in sources}) != len(sources):
            raise ValueError("Duplicate data source; use explicit source balancing instead")
    if len(development_sources) > 1:
        dev_hash = hashlib.sha256(json.dumps(development_sources, sort_keys=True).encode()).hexdigest()
    sampling_weights = source_sampling_weights([s["rows"] for s in training_sources]) if args.balance_training_sources else None
    source_ids = torch.cat([torch.full((s["rows"],), i, dtype=torch.long) for i, s in enumerate(training_sources)])
    model, parent = initial_model(args.initial_actor, args.hidden, report, args.allow_historical_initial)
    reference = copy.deepcopy(model).eval().requires_grad_(False) if args.retention_weight > 0 else None
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = ROOT / "artifacts/player-agents" / ("imitation-" + stamp); folder.mkdir(exist_ok=False)
    snapshot = folder / "trainer-source"; snapshot.mkdir()
    if reference is not None:
        shutil.copy2(args.initial_actor, folder / "retention-reference.json")
    for name in ("player-agents-imitate.py", "player_actor.py"):
        shutil.copy2(ROOT / "scripts" / name, snapshot / name)
    for path in (ROOT / "Assets/Picklebot/PlayerAgents").rglob("*.cs"):
        if "/Tests/" in str(path):
            continue
        target = folder / "runtime-source" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    started = time.perf_counter(); history = []; best = float("inf"); updates = 0
    trainer_hash = hashlib.sha256(Path(__file__).read_bytes() + (ROOT / "scripts/player_actor.py").read_bytes()).hexdigest()
    metadata = dict(sourceHash=source_hash(), configurationHash=report["configurationHash"], contactModelHash=report["contactModelHash"],
                    protocolHash=report["protocolHash"], trainerHash=trainer_hash, dataHash=data_hash, baselineManifestHash=report["baselineManifestHash"],
                    createdUtc=datetime.now(timezone.utc).isoformat(), method="supervised imitation warm start; not competitive RL", trainingSteps=0)
    if parent is not None:
        metadata.update(method="supervised corrective fine-tune on current-runtime teacher labels; not competitive RL",
                        parentActorHash=file_hash(args.initial_actor), parentTrainingSteps=parent["trainingSteps"],
                        parentSourceHash=parent["sourceHash"], historicalParent=parent["sourceHash"] != metadata["sourceHash"])
    if reference is not None:
        metadata.update(retentionWeight=args.retention_weight, retentionReferenceHash=metadata["parentActorHash"],
                        retentionMethod="soft output penalty on original recorded observations; not competitive RL or a retention guarantee")
    for epoch in range(args.epochs):
        model.train()
        order = torch.randperm(len(x)) if sampling_weights is None else torch.multinomial(sampling_weights, len(x), replacement=True)
        sampled_counts = torch.bincount(source_ids[order], minlength=len(training_sources)).tolist()
        for index in order.split(args.batch):
            optimizer.zero_grad(set_to_none=True)
            batch = x[index].clone()
            # Teacher paddles already point toward the selected shot. Without
            # augmentation the actor can infer "hit" from that consequence,
            # then refuse to start a swing from its own neutral paddle state.
            neutral = torch.rand(len(index)) < args.neutral_paddle_probability
            batch[neutral, 25:37] = torch.tensor([.19, .55, .46, 0, 0, 1, 0, 0, 0, 0, 0, 0])
            loss, _ = loss_and_metrics(model, batch, y[index])
            if reference is not None:
                # Keep the original observed paddle state for retention. Teacher
                # augmentation must not replace the reference model's input.
                with torch.no_grad(): reference_output = reference(x[index])
                retained_loss, _ = retention_from_outputs(model(x[index]), reference_output)
                loss = loss + args.retention_weight * retained_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step(); updates += 1
        model.eval()
        with torch.no_grad():
            per_source_metrics = []; selection_losses = []
            for vx, vy in validation_tensors:
                _, source_metrics = loss_and_metrics(model, vx, vy)
                neutral_dx = vx.clone(); neutral_dx[:, 25:37] = torch.tensor([.19, .55, .46, 0, 0, 1, 0, 0, 0, 0, 0, 0])
                _, neutral_metrics = loss_and_metrics(model, neutral_dx, vy)
                source_metrics["neutralPaddleHitRecall"] = neutral_metrics["hitRecall"]
                selection_loss = source_metrics["loss"] + neutral_metrics["loss"]
                if reference is not None:
                    retained_loss, retained_metrics = retention_from_outputs(model(vx), reference(vx))
                    source_metrics.update(retained_metrics)
                    selection_loss += args.retention_weight * retained_loss.item()
                per_source_metrics.append(source_metrics)
                selection_losses.append(selection_loss)
            metrics = average_source_metrics(per_source_metrics)
            selection_loss = sum(selection_losses) / len(selection_losses)
        metrics.update(epoch=epoch + 1, elapsedSeconds=time.perf_counter() - started,
                       sampledRowsPerSource=sampled_counts, validationSources=per_source_metrics,
                       selectionLoss=selection_loss); history.append(metrics)
        if selection_loss < best:
            best = selection_loss; metadata["trainingSteps"] = updates
            (folder / "actor.json").write_text(json.dumps(model.export(metadata)))
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            print(json.dumps(metrics), flush=True)
    accepted, _ = Actor.load_export(folder / "actor.json")
    if source_hash() != metadata["sourceHash"]:
        raise RuntimeError("Unity source changed during fitting; do not accept this run")
    if reference is not None and (file_hash(args.initial_actor) != metadata["retentionReferenceHash"]
            or file_hash(folder / "retention-reference.json") != metadata["retentionReferenceHash"]):
        raise RuntimeError("Retention reference changed during fitting; do not accept this run")
    with torch.no_grad():
        outputs = accepted(dx[:32]).tolist()
    (folder / "parity-input.json").write_text(json.dumps({"observations": [{"values": row.tolist()} for row in dx[:32]], "expected": [{"values": row} for row in outputs]}))
    final = dict(metadata, actorHash=file_hash(folder / "actor.json"), developmentDataHash=dev_hash,
                 bestSelectionLoss=best,
                 trainingReport=str(args.training_report), developmentReport=str(args.development_report),
                 trainingSources=training_sources, developmentSources=development_sources,
                 trainingRows=len(x), developmentRows=sum(len(vx) for vx, _ in validation_tensors), epochs=args.epochs, optimizerUpdates=updates,
                 configuration=dict(hidden=args.hidden, batch=args.batch, learningRate=args.learning_rate, neutralPaddleProbability=args.neutral_paddle_probability, torch=torch.__version__, seed=1000000,
                                    initialActor=str(args.initial_actor) if args.initial_actor else None,
                                    allowHistoricalInitial=args.allow_historical_initial,
                                    retentionWeight=args.retention_weight,
                                    retentionScope="original recorded observations; validation is selection only; default zero preserves the old training path",
                                    balancedTrainingSources=args.balance_training_sources,
                                    primaryServeFlightOnly=args.primary_serve_flight_only,
                                    validationAggregation="equal source mean"),
                 elapsedSeconds=time.perf_counter() - started, history=history,
                 limits="Prediction loss only; not evidence of return success, useful coverage or match wins.")
    (folder / "training.json").write_text(json.dumps(final, indent=2))
    print(folder, flush=True)


if __name__ == "__main__":
    main()
