"""Replay movement-fit selection and verify that the complete actor keeps all other parameters."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash, source_hash

spec=importlib.util.spec_from_file_location("movement_fit",ROOT/"scripts/player-agents-fit-movement.py")
fit=importlib.util.module_from_spec(spec); spec.loader.exec_module(fit)


def audit(folder):
    torch.set_num_threads(2)
    report=json.loads((folder/"training.json").read_text())
    plan=json.loads((folder/"plan.json").read_text())
    if (report["status"]!="complete" or report["sourceHash"]!=source_hash()
            or file_hash(folder/"plan.json")!=report["planHash"]
            or file_hash(folder/"actor.json")!=report["actorHash"]
            or file_hash(folder/"parent.json")!=report["parentActorHash"]
            or report["parentActorHash"]!=plan["parentActorHash"]):
        raise ValueError("Fit identity changed")
    for path,digest in report["frozen"].items():
        if file_hash(path)!=digest: raise ValueError("Frozen input changed: "+path)
    for snapshot in (folder/"trainer-source").iterdir():
        if file_hash(snapshot)!=report["frozen"][str(ROOT/"scripts"/snapshot.name)]:
            raise ValueError("Trainer snapshot changed")
    parent,_=Actor.load_export(folder/"parent.json"); actor,metadata=Actor.load_export(folder/"actor.json")
    fit.validate_frozen_parameters(parent,actor)
    if (metadata["parentActorHash"]!=report["parentActorHash"] or metadata["planHash"]!=report["planHash"]
            or metadata["sourceHash"]!=report["sourceHash"]): raise ValueError("Actor lineage changed")
    data_hash=hashlib.sha256(json.dumps(report["trainingSources"],sort_keys=True).encode()).hexdigest()
    if metadata["dataHash"]!=data_hash: raise ValueError("Training data identity changed")
    history=report["history"]
    if len(history)!=plan["fit"]["epochs"] or len(history)!=200: raise ValueError("Incomplete fit")
    steps=math.ceil(sum(r["rows"] for r in report["trainingSources"])/plan["fit"]["batch"])
    for index,row in enumerate(history):
        if (row["epoch"]!=index+1 or row["updates"]!=(index+1)*steps
                or len(row["sampledRowsPerSource"])!=4 or any(n<=0 for n in row["sampledRowsPerSource"])
                or sum(row["sampledRowsPerSource"])!=sum(r["rows"] for r in report["trainingSources"])
                or not all(math.isfinite(v) and v>=0 for v in row["developmentLosses"])
                or abs(row["selectionLoss"]-sum(row["developmentLosses"])/4)>1e-10):
            raise ValueError("Training schedule changed")
    selected=min(history,key=lambda r:r["selectionLoss"])
    if (selected["updates"]!=report["selectedUpdates"] or selected["updates"]!=metadata["trainingSteps"]
            or report["optimizerUpdates"]!=steps*200 or selected["selectionLoss"]!=report["bestSelectionLoss"]):
        raise ValueError("Saved checkpoint is not selected by development loss")
    records=[]; all_hashes=[]
    for split in ("training","development"):
        sources=report[split+"Sources"]
        expected_extra=plan["additionalTraining" if split=="training" else "additionalDevelopment"]
        if len(sources)!=4 or [str(Path(r["report"]).resolve()) for r in sources[1:]]!=[str(ROOT/p) for p in expected_extra]:
            raise ValueError("Source schedule changed")
        for index,record in enumerate(sources):
            x,y,collection,measured=fit.load_bank(Path(record["report"]),split)
            if measured!=record: raise ValueError("Source record changed")
            all_hashes.append(record["dataHash"])
            if index==0:
                expected=dict(seed=plan["collection"][split+"Seed"],rallies=plan["collection"][split+"Rallies"],
                    teacherDecisions=0,teacherProbability=0,actorDecisions=len(x),actorHash=plan["parentActorHash"],
                    baselineOpponent=False,fixedShot=-1)
                if any(collection.get(k)!=v for k,v in expected.items()): raise ValueError("Actor state collection differs")
            with torch.no_grad():
                a=parent(x); b=actor(x)
                if not torch.equal(a[:,2:],b[:,2:]): raise ValueError("Hit or shot output changed on the same input")
                parent_loss=float(fit.movement_loss(a[:,:2],y)); candidate_loss=float(fit.movement_loss(b[:,:2],y))
            if split=="development":
                if abs(parent_loss-report["parentDevelopmentLosses"][index])>1e-6 or abs(candidate_loss-selected["developmentLosses"][index])>1e-6:
                    raise ValueError("Development selection replay differs")
            records.append(dict(split=split,index=index,rows=len(x),phases=record["phases"],
                parentWeightedMovementLoss=parent_loss,candidateWeightedMovementLoss=candidate_loss,
                teacherDecisions=collection["teacherDecisions"],actorDecisions=collection["actorDecisions"],
                collectionSeconds=collection["wallSeconds"],decisionsPerSecond=len(x)/collection["wallSeconds"]))
    if len(set(all_hashes))!=len(all_hashes): raise ValueError("Duplicate source")
    return dict(folder=str(folder),actorHash=report["actorHash"],parentActorHash=report["parentActorHash"],
        sourceHash=report["sourceHash"],planHash=report["planHash"],trainingHash=file_hash(folder/"training.json"),
        selectedEpoch=selected["epoch"],selectedUpdates=selected["updates"],optimizerUpdates=report["optimizerUpdates"],
        fittingSeconds=report["elapsedSeconds"],frozenNonMovementParametersVerified=True,
        sameInputHitShotOutputsExact=True,motorChecksPassed=True,sources=records,
        limitation="Supervised movement correction only. Unchanged parameters do not guarantee identical actions on changed trajectories or better games.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("folder",type=Path)
    print(json.dumps(audit(parser.parse_args().folder),indent=2))
