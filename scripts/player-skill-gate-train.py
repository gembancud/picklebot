#!/usr/bin/env python3
"""Bounded supervised selector bootstrap, not team-win RL or model promotion."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import torch
from torch.nn import functional as F

from player_actor import ROOT, file_hash, source_hash, teacher_data
from player_skill_gate import SkillGate, load_experts, source_label, selected_outputs
from player_ppo import validate_motor_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if plan["version"] != "player-skill-gate-bootstrap-v1" or plan["sourceHash"] != source_hash():
        raise ValueError("Changed bootstrap plan or runtime")
    if (plan["seed"] != 1000000 or plan["epochs"] != 30 or plan["batch"] != 1024
            or plan["learningRate"] != .001 or any(len(plan[s]) != 3 for s in ("training", "development"))):
        raise ValueError("Changed bounded bootstrap settings")
    torch.manual_seed(plan["seed"]); torch.set_num_threads(2)
    banks = {}
    sources = []
    for split in ("training", "development"):
        banks[split] = []
        for spec in plan[split]:
            path = ROOT / spec["report"]
            x, _, report, digest = teacher_data(path, split)
            if (digest != spec["dataHash"] or report["seed"] != spec["seed"]
                    or source_label(report) != spec["label"]):
                raise ValueError("Changed selector data identity")
            for key in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
                if report[key] != plan[key]:
                    raise ValueError("Selector bank provenance differs: " + key)
            validate_motor_metrics(dict(games=report["gameResults"]))
            banks[split].append((x, torch.full((len(x),), float(spec["label"]))))
            sources.append(dict(split=split, **spec, reportHash=file_hash(path), rows=len(x)))
    if len({s["dataHash"] for s in sources}) != len(sources):
        raise ValueError("Duplicate selector bank")
    metadata = {k: plan[k] for k in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash", "experts")}
    experts = load_experts(metadata)
    gate = SkillGate()
    optimizer = torch.optim.Adam(gate.parameters(), lr=plan["learningRate"])
    x = torch.cat([v[0] for v in banks["training"]]); y = torch.cat([v[1] for v in banks["training"]])
    source_ids = torch.cat([torch.full((len(v[0]),), i, dtype=torch.long) for i, v in enumerate(banks["training"])])
    weights = torch.cat([torch.full((len(v[0]),), 1/len(v[0]), dtype=torch.float64) for v in banks["training"]])
    folder = ROOT / "artifacts/player-agents" / ("skill-gate-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    shutil.copy2(args.plan, folder / "plan.json")
    snapshot = folder / "trainer-source"; snapshot.mkdir()
    for name in ("player-skill-gate-train.py", "player_skill_gate.py", "player_actor.py", "player_ppo.py"):
        shutil.copy2(ROOT / "scripts" / name, snapshot / name)
    snapshot_hashes = {p.name: file_hash(p) for p in snapshot.iterdir()}
    metadata.update(createdUtc=datetime.now(timezone.utc).isoformat(), planHash=file_hash(args.plan),
                    method="profile-supervised selector bootstrap over frozen experts; not team-win RL",
                    sources=sources, trainerSources=snapshot_hashes)
    history = []; best = float("inf"); best_state = None; steps = 0
    started = time.perf_counter()
    for epoch in range(plan["epochs"]):
        order = torch.multinomial(weights, len(x), replacement=True)
        for ids in order.split(plan["batch"]):
            optimizer.zero_grad(set_to_none=True)
            loss = F.binary_cross_entropy_with_logits(gate(x[ids]), y[ids])
            loss.backward(); torch.nn.utils.clip_grad_norm_(gate.parameters(), 1.0); optimizer.step(); steps += 1
        with torch.no_grad():
            metrics = []
            for vx, vy in banks["development"]:
                logits = gate(vx)
                metrics.append(dict(loss=F.binary_cross_entropy_with_logits(logits, vy).item(),
                                    accuracy=((logits >= 0) == vy.bool()).float().mean().item(),
                                    shortSelectionRate=(logits >= 0).float().mean().item()))
            selection_loss = sum(r["loss"] for r in metrics)/len(metrics)
        history.append(dict(epoch=epoch+1, development=metrics, equalSourceLoss=selection_loss,
                            sampledRowsPerSource=torch.bincount(source_ids[order], minlength=3).tolist()))
        if selection_loss < best:
            best = selection_loss; best_state = copy.deepcopy(gate.state_dict())
            metadata.update(trainingSteps=steps, selectedEpoch=epoch+1)
    gate.load_state_dict(best_state); gate.eval()
    if source_hash() != metadata["sourceHash"] or file_hash(args.plan) != metadata["planHash"]:
        raise ValueError("Inputs changed during selector fitting")
    load_experts(metadata)
    (folder / "gate.json").write_text(json.dumps(gate.export(metadata)))
    with torch.no_grad():
        probes = torch.cat([v[0][:16] for v in banks["development"]])
        logits, choices, output = selected_outputs(gate, experts, probes)
        (folder / "parity.json").write_text(json.dumps(dict(observations=probes.tolist(), logits=logits.tolist(),
                                                           choices=choices.tolist(), outputs=output.tolist())))
    result = dict(status="complete", gatePath=str((folder / "gate.json").relative_to(ROOT)),
                  gateHash=file_hash(folder / "gate.json"), elapsedSeconds=time.perf_counter()-started,
                  selectedEpoch=metadata["selectedEpoch"], optimizerUpdates=steps, history=history,
                  limitation="Source classification only; not physical return or competitive game evidence.")
    (folder / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != "history"}, indent=2))


if __name__ == "__main__": main()
