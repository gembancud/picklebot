#!/usr/bin/env python3
"""Fit movement output rows on actor-visited states. No runtime overrides or promotion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

import torch

from player_actor import Actor, ROOT, file_hash, source_hash, teacher_data
from player_ppo import validate_motor_metrics


def features(actor, observations):
    with torch.no_grad():
        result = observations
        for layer in actor.layers[:-1]: result = layer(result).tanh()
        return result.detach()


def critical_contact_mask(observations, labels):
    if observations.ndim != 2 or observations.shape[1] != 54 or labels.shape != (len(observations),4):
        raise ValueError("Invalid contact-weighting tensors")
    if not torch.isfinite(observations).all() or not torch.isfinite(labels).all():
        raise ValueError("Non-finite contact-weighting tensors")
    height = observations[:,5]*3
    distance2 = (observations[:,4]*8.4).square()+(observations[:,6]*16.2).square()
    return (observations[:,46]==1)&(labels[:,2]==1)&(height>=.1)&(height<=2)&(distance2<=1.5**2)


def movement_loss(output, labels):
    error = (Actor.movement(output) - labels[:, :2]).square().mean(-1)
    weight = 1 + 4 * labels[:, 2] + 2 * torch.linalg.vector_norm(labels[:, :2], dim=-1)
    return (error * weight * labels[:,4]).mean()


def validate_frozen_parameters(parent, candidate):
    if len(parent.layers) != len(candidate.layers): raise ValueError("Layer count changed")
    for i, (a, b) in enumerate(zip(parent.layers, candidate.layers)):
        start = 2 if i == len(parent.layers)-1 else 0
        if not torch.equal(a.weight[start:], b.weight[start:]) or not torch.equal(a.bias[start:], b.bias[start:]):
            raise ValueError("Non-movement parameters changed")
    if not torch.equal(parent.log_std, candidate.log_std): raise ValueError("Exploration changed")


def load_bank(path, split):
    x, y, report, digest = teacher_data(path, split)
    games = []
    for game in report.get("gameResults", []):
        teams = (0, 1) if game["candidateTeam"] == -1 else (game["candidateTeam"],)
        games.extend(dict(game, candidateTeam=team) for team in teams)
    if not games: raise ValueError("Missing motor evidence")
    validate_motor_metrics(dict(games=games))
    phase = x[:, 39:44]
    if not (((phase == 0) | (phase == 1)).all() and (phase.sum(-1) == 1).all()):
        raise ValueError("Invalid phase observations")
    record = dict(report=str(path), reportHash=file_hash(path), dataPath=report["dataPath"], dataHash=digest,
                  rows=len(x), phases=dict(zip(("serveSetup", "serveFlight", "returnFlight", "rally", "dead"),
                                             phase.sum(0).int().tolist())))
    critical = critical_contact_mask(x,y)
    indices = critical.nonzero(as_tuple=False).flatten().tolist()
    record.update(criticalRows=len(indices),criticalIndicesHash=hashlib.sha256(json.dumps(indices,separators=(",",":")).encode()).hexdigest())
    y = torch.cat((y,torch.where(critical,16.,1.).unsqueeze(1)),dim=1)
    return x, y, report, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_report", type=Path)
    parser.add_argument("development_report", type=Path)
    parser.add_argument("--plan", type=Path, default=ROOT/"config/player-agents/near-contact-movement-v1.json")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text()); settings = plan["fit"]
    if plan["version"] != "near-contact-movement-v1" or plan["sourceHash"] != source_hash():
        raise ValueError("Wrong movement plan or runtime")
    parent_path = ROOT/plan["parentActor"]
    if file_hash(parent_path) != plan["parentActorHash"]: raise ValueError("Parent changed")
    if settings != dict(epochs=200, batch=1024, learningRate=.001, seed=1000000,
            sourceSampling="equal source mass, with replacement",
            trainableParameters="Only the two movement output rows and biases. Freeze both hidden layers, hit and shot outputs, and log standard deviation.",
            loss="The original movement loss multiplied by 16 for expected-team teacher-attempt rows with ball height 0.1 to 2 metres and horizontal ball distance at most 1.5 metres. Select minimum equal-source development loss.",
            augmentation="None. Preserve actual observed paddle state."):
        raise ValueError("Unreviewed movement fitting settings")
    torch.set_num_threads(2); torch.manual_seed(settings["seed"])
    parent, metadata = Actor.load_export(parent_path)
    if metadata["sourceHash"] != plan["sourceHash"]: raise ValueError("Parent runtime changed")
    parent.eval().requires_grad_(False)
    candidate, _ = Actor.load_export(parent_path)
    frozen = {str(args.plan): file_hash(args.plan), str(parent_path): file_hash(parent_path)}
    banks = {}; provenance = {}
    for split, primary, extra in (("training", args.training_report, plan["additionalTraining"]),
                                  ("development", args.development_report, plan["additionalDevelopment"])):
        banks[split] = []; provenance[split] = []
        for index, path in enumerate([primary]+[ROOT/p for p in extra]):
            x, y, report, record = load_bank(path, split)
            if index == 0:
                collection = plan["collection"]
                expected = dict(seed=collection[split+"Seed"], rallies=collection[split+"Rallies"],
                    baselineOpponent=False, teacherProbability=0, teacherDecisions=0, fixedShot=-1,
                    actorHash=plan["parentActorHash"], actorDecisions=len(x))
                if any(report.get(k) != v for k,v in expected.items()): raise ValueError("Actor-state collection changed")
            for key in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
                if report[key] != metadata[key]: raise ValueError("Bank differs from parent: "+key)
            frozen[str(path)] = record["reportHash"]; frozen[str(ROOT/record["dataPath"])] = record["dataHash"]
            banks[split].append((features(parent,x),y)); provenance[split].append(record)
    digests = [r["dataHash"] for records in provenance.values() for r in records]
    if len(set(digests)) != len(digests): raise ValueError("Duplicate or overlapping source bank")
    output = torch.nn.Linear(parent.layers[-1].in_features,2)
    with torch.no_grad():
        output.weight.copy_(parent.layers[-1].weight[:2]); output.bias.copy_(parent.layers[-1].bias[:2])
    optimizer = torch.optim.Adam(output.parameters(), lr=settings["learningRate"])
    h = torch.cat([a for a,b in banks["training"]]); y = torch.cat([b for a,b in banks["training"]])
    weights = torch.cat([torch.full((len(a),),1/len(a),dtype=torch.float64) for a,b in banks["training"]])
    source_ids = torch.cat([torch.full((len(a),),i,dtype=torch.long) for i,(a,b) in enumerate(banks["training"])])
    folder = ROOT/"artifacts/player-agents"/("contact-movement-fit-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False); snapshot = folder/"trainer-source"; snapshot.mkdir()
    for name in ("player-agents-fit-contact-movement.py", "player_actor.py", "player_ppo.py"):
        path = ROOT/"scripts"/name; shutil.copy2(path,snapshot/name); frozen[str(path)] = file_hash(path)
    shutil.copy2(args.plan,folder/"plan.json"); shutil.copy2(parent_path,folder/"parent.json")
    new_metadata = dict(sourceHash=metadata["sourceHash"], configurationHash=metadata["configurationHash"],
        contactModelHash=metadata["contactModelHash"], protocolHash=metadata["protocolHash"],
        baselineManifestHash=metadata["baselineManifestHash"], createdUtc=datetime.now(timezone.utc).isoformat(),
        method="supervised near-contact-weighted actor-state movement output correction; frozen hidden, hit and shot parameters; not competitive RL",
        trainerHash=file_hash(__file__), dataHash=hashlib.sha256(json.dumps(provenance["training"],sort_keys=True).encode()).hexdigest(),
        parentActorHash=plan["parentActorHash"], parentTrainingSteps=metadata["trainingSteps"],
        planHash=file_hash(args.plan), trainingSteps=0)
    history = []; best = float("inf"); updates = 0; start = time.perf_counter()
    print(folder,flush=True)
    with torch.no_grad():
        parent_losses = [float(movement_loss(output(vx),vy)) for vx,vy in banks["development"]]
    for epoch in range(settings["epochs"]):
        order = torch.multinomial(weights,len(h),replacement=True)
        for indices in order.split(settings["batch"]):
            optimizer.zero_grad(set_to_none=True)
            loss = movement_loss(output(h[indices]),y[indices]); loss.backward()
            torch.nn.utils.clip_grad_norm_(output.parameters(),1); optimizer.step(); updates += 1
        with torch.no_grad():
            losses = [float(movement_loss(output(vx),vy)) for vx,vy in banks["development"]]
        selected = sum(losses)/len(losses)
        history.append(dict(epoch=epoch+1, updates=updates, developmentLosses=losses, selectionLoss=selected,
            sampledRowsPerSource=torch.bincount(source_ids[order],minlength=len(banks["training"])).tolist()))
        if selected < best:
            best = selected
            with torch.no_grad():
                candidate.layers[-1].weight[:2].copy_(output.weight); candidate.layers[-1].bias[:2].copy_(output.bias)
            validate_frozen_parameters(parent,candidate)
            new_metadata["trainingSteps"] = updates
            (folder/"actor.json").write_text(json.dumps(candidate.export(new_metadata)))
        if epoch % 25 == 0 or epoch == settings["epochs"]-1: print(json.dumps(history[-1]),flush=True)
    accepted, accepted_meta = Actor.load_export(folder/"actor.json")
    validate_frozen_parameters(parent,accepted)
    if source_hash() != plan["sourceHash"] or any(file_hash(path)!=digest for path,digest in frozen.items()):
        raise ValueError("Frozen inputs changed during fit")
    x, _, _, _ = teacher_data(args.development_report,"development")
    with torch.no_grad(): result = accepted(x[:32])
    (folder/"parity-input.json").write_text(json.dumps(dict(observations=[dict(values=row.tolist()) for row in x[:32]],
        expected=[dict(values=row.tolist()) for row in result])))
    report = dict(status="complete", actorHash=file_hash(folder/"actor.json"), sourceHash=source_hash(),
        parentActorHash=plan["parentActorHash"], planHash=file_hash(args.plan), frozen=frozen,
        trainingSources=provenance["training"], developmentSources=provenance["development"],
        parentDevelopmentLosses=parent_losses, bestSelectionLoss=best, selectedUpdates=accepted_meta["trainingSteps"],
        optimizerUpdates=updates, elapsedSeconds=time.perf_counter()-start, history=history,
        frozenNonMovementParametersVerified=True, limits="Prediction loss only. No proof of contact success, useful coverage or match improvement.")
    (folder/"training.json").write_text(json.dumps(report,indent=2))
    print(folder,flush=True)


if __name__ == "__main__": main()
