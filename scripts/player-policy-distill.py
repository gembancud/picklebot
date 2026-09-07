#!/usr/bin/env python3
"""One bounded multi-teacher warm start. Exports one ordinary player-actor-v1."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_policy_distillation import (distillation_loss, load_banks, load_teachers,
                                       metrics, neutral_paddle, source_weights, validate_plan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    plan_hash = file_hash(args.plan)
    plan = json.loads(args.plan.read_text()); validate_plan(plan)
    torch.manual_seed(plan["seed"]); torch.set_num_threads(2)
    teachers = load_teachers(plan)
    training = load_banks(plan, "training", teachers)
    development = load_banks(plan, "development", teachers)
    x = torch.cat([b["x"] for b in training])
    targets = torch.cat([b["target"] for b in training])
    neutral_targets = torch.cat([b["target_neutral"] for b in training])
    source_ids = torch.cat([torch.full((len(b["x"]),), i, dtype=torch.long) for i, b in enumerate(training)])
    weights = source_weights([len(b["x"]) for b in training])
    student = copy.deepcopy(teachers[0]).train().requires_grad_(True)
    optimizer = torch.optim.Adam(student.parameters(), lr=plan["learningRate"])
    folder = ROOT/"artifacts/player-agents"/("policy-distillation-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False); (folder/"trainer-source").mkdir()
    shutil.copy2(args.plan, folder/"plan.json")
    names = ["player-policy-distill.py", "player_policy_distillation.py", "player_actor.py"]
    trainer_hashes = {}
    for name in names:
        shutil.copy2(ROOT/"scripts"/name, folder/"trainer-source"/name)
        trainer_hashes[name] = file_hash(ROOT/"scripts"/name)
    for i, teacher in enumerate(plan["teachers"]):
        shutil.copy2(ROOT/teacher["path"], folder/f"teacher-{i}.json")
    metadata = {k: plan[k] for k in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash")}
    metadata.update(method=plan["method"], planHash=plan_hash, trainerSources=trainer_hashes,
                    trainerHash=hashlib.sha256(json.dumps(trainer_hashes, sort_keys=True).encode()).hexdigest(),
                    parentActorHash=plan["teachers"][0]["sha256"], teachers=plan["teachers"],
                    createdUtc=datetime.now(timezone.utc).isoformat(), trainingSteps=0,
                    trainingSources=[b["provenance"] for b in training], developmentSources=[b["provenance"] for b in development],
                    runtime="one standard feed-forward actor per player; no source id or teacher selection input")
    history = []; updates = 0; best = float("inf"); best_epoch = 0
    watch = time.perf_counter()
    try:
        for epoch in range(1, plan["epochs"]+1):
            order = torch.multinomial(weights, len(x), replacement=True)
            student.train()
            for index in order.split(plan["batch"]):
                batch = x[index].clone(); target = targets[index].clone()
                mask = torch.rand(len(index)) < plan["neutralPaddleProbability"]
                batch[mask] = neutral_paddle(batch[mask]); target[mask] = neutral_targets[index][mask]
                optimizer.zero_grad(set_to_none=True)
                loss = distillation_loss(student(batch), target)
                loss.backward(); torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
                optimizer.step(); updates += 1
            student.eval(); validation = []
            with torch.no_grad():
                for bank in development:
                    original = metrics(student(bank["x"]), bank["target"])
                    neutral = metrics(student(neutral_paddle(bank["x"])), bank["target_neutral"])
                    validation.append(dict(original=original, neutral=neutral))
            selection_loss = sum(v["original"]["loss"]+v["neutral"]["loss"] for v in validation)/(2*len(validation))
            row = dict(epoch=epoch, updates=updates, selectionLoss=selection_loss, validation=validation,
                       sampledRowsPerSource=torch.bincount(source_ids[order], minlength=len(training)).tolist(),
                       elapsedSeconds=time.perf_counter()-watch)
            history.append(row)
            if selection_loss < best:
                best = selection_loss; best_epoch = epoch
                metadata["trainingSteps"] = updates; metadata["selectedEpoch"] = epoch
                (folder/"actor.json").write_text(json.dumps(student.export(metadata)))
            if epoch == 1 or epoch % 10 == 0:
                print(json.dumps(row), flush=True)
        validate_plan(plan)
        if file_hash(args.plan) != plan_hash or source_hash() != metadata["sourceHash"]:
            raise ValueError("Plan or runtime changed during training")
        for name, digest in trainer_hashes.items():
            if file_hash(ROOT/"scripts"/name) != digest:
                raise ValueError("Trainer changed during training")
        for split in (training, development):
            for bank in split:
                record = bank["provenance"]; report = json.loads((ROOT/record["report"]).read_text())
                if file_hash(ROOT/record["report"]) != record["reportHash"] or file_hash(ROOT/report["dataPath"]) != record["dataHash"]:
                    raise ValueError("Input data changed during training")
        load_teachers(plan)
        saved, saved_metadata = Actor.load_export(folder/"actor.json"); saved.eval()
        parity_x = torch.cat([b["x"][:16] for b in development])
        with torch.no_grad(): parity_y = saved(parity_x)
        (folder/"parity-input.json").write_text(json.dumps(dict(observations=[dict(values=r.tolist()) for r in parity_x],
                                                               expected=[dict(values=r.tolist()) for r in parity_y])))
        result = dict(status="complete", folder=str(folder.relative_to(ROOT)), actorHash=file_hash(folder/"actor.json"),
                      sourceHash=metadata["sourceHash"], planHash=plan_hash, selectedEpoch=best_epoch, selectionLoss=best,
                      trainingRows=len(x), developmentRows=sum(len(b["x"]) for b in development), updates=updates,
                      selectedTrainingSteps=saved_metadata["trainingSteps"], wallSeconds=time.perf_counter()-watch,
                      torchVersion=torch.__version__, threads=2, history=history,
                      limitation="Supervised skill transfer only. No game-win update, physical success claim, or promotion.")
        (folder/"result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps({k: v for k, v in result.items() if k != "history"}), flush=True)
    except Exception as error:
        (folder/"failure.json").write_text(json.dumps(dict(status="failed", error=repr(error), updates=updates, history=history)))
        raise


if __name__ == "__main__":
    main()
