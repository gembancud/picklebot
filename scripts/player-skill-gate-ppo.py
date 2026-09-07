#!/usr/bin/env python3
"""One bounded policy-gradient update on verified complete team-game outcomes."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import torch

from player_actor import ROOT, file_hash, source_hash
from player_skill_gate import load_experts, selected_outputs
from player_skill_gate_rl import verify, likelihood
from player_ppo import clipped_loss


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("rollout",type=Path)
    args=parser.parse_args()
    gate,metadata,rows,(rewards,weights),audit=verify(args.rollout)
    plan=json.loads((args.rollout/"training-plan.json").read_text())
    expected=dict(epochs=4,batch=1024,learningRate=.0003,clip=.2,maximumKl=.02,
                  baseline="zero, no advantage normalization",weighting="equal mass per complete game")
    if plan["plannedOptimizer"] != expected: raise ValueError("Optimizer differs from pre-collection plan")
    torch.manual_seed(1071000); torch.set_num_threads(2)
    source=source_hash(); parent=ROOT/plan["gatePath"]
    folder=ROOT/"artifacts/player-agents"/("skill-gate-ppo-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    # Preserve the bootstrap provenance and add the separate RL source record.
    shutil.copy2(parent.parent/"plan.json",folder/"plan.json")
    shutil.copytree(parent.parent/"trainer-source",folder/"trainer-source")
    snapshot=folder/"rl-trainer-source"; snapshot.mkdir()
    for name in ("player-skill-gate-ppo.py","player_skill_gate_rl.py","player_skill_gate_games.py",
                 "player_skill_gate.py","player_actor.py","player_ppo.py","player_acceptance.py",
                 "player_skill_retention.py","player-compare-models.py"):
        shutil.copy2(ROOT/"scripts"/name,snapshot/name)
    (folder/"rollout-audit.json").write_text(json.dumps(audit,indent=2))
    shutil.copy2(parent,folder/"initial-gate.json")
    x=torch.tensor([r["observation"] for r in rows]); choice=torch.tensor([r["selectedExpert"] for r in rows])
    old_logp=torch.tensor([r["selectorLogProbability"] for r in rows])
    optimizer=torch.optim.Adam(gate.parameters(),lr=expected["learningRate"])
    history=[]; accepted=0; attempted=0; started=time.perf_counter()
    for epoch in range(expected["epochs"]):
        before=copy.deepcopy(gate.state_dict()); steps=0
        order=torch.multinomial(weights,len(x),replacement=True)
        for ids in order.split(expected["batch"]):
            optimizer.zero_grad(set_to_none=True)
            logp,_=likelihood(gate(x[ids]),choice[ids]); loss,_=clipped_loss(logp,old_logp[ids],rewards[ids])
            loss.backward(); torch.nn.utils.clip_grad_norm_(gate.parameters(),1.0); optimizer.step()
            steps+=1; attempted+=1
        with torch.no_grad():
            logp,p=likelihood(gate(x),choice); delta=logp-old_logp; ratio=delta.exp()
            kl=float((((ratio-1)-delta)*weights).sum()/weights.sum())
            loss=float((-torch.minimum(ratio*rewards,ratio.clamp(.8,1.2)*rewards)*weights).sum()/weights.sum())
        kept=math_is_valid(kl,loss) and kl<=expected["maximumKl"]
        history.append(dict(epoch=epoch+1,loss=loss,approximateKl=kl,accepted=kept))
        if not kept:
            gate.load_state_dict(before); break
        accepted+=steps
    if not accepted: raise RuntimeError("No policy update passed the declared KL bound; keep the parent")
    if source_hash()!=source or file_hash(parent)!=plan["gateHash"]: raise ValueError("Training input changed")
    experts=load_experts(metadata)
    metadata.update(createdUtc=datetime.now(timezone.utc).isoformat(),
        method="clipped policy-gradient selector update on complete team-game rewards against a frozen older actor",
        trainingSteps=metadata["trainingSteps"]+accepted,
        gameWinTraining=dict(parentGateHash=plan["gateHash"],rolloutFolder=str(args.rollout),rolloutPlanHash=audit["planHash"],
            rolloutCompletionHash=audit["completionHash"],games=4,wins=audit["wins"],rows=len(rows),
            acceptedUpdates=accepted,attemptedUpdates=attempted,configuration=expected,
            sampling=dict(logitScale=.5,explorationFloor=.05),history=history,
            trainerSources={p.name:file_hash(p) for p in snapshot.iterdir()}))
    gate.eval(); (folder/"gate.json").write_text(json.dumps(gate.export(metadata)))
    probes=json.loads((parent.parent/"parity.json").read_text())["observations"]
    with torch.no_grad():
        logits,choices,outputs=selected_outputs(gate,experts,torch.tensor(probes))
    (folder/"parity.json").write_text(json.dumps(dict(observations=probes,logits=logits.tolist(),choices=choices.tolist(),outputs=outputs.tolist())))
    result=dict(status="complete",gatePath=str((folder/"gate.json").relative_to(ROOT)),gateHash=file_hash(folder/"gate.json"),
                elapsedSeconds=time.perf_counter()-started,acceptedUpdates=accepted,history=history,
                limitation="One four-game training update. No evidence of improved held-out or baseline performance yet.")
    (folder/"result.json").write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))


def math_is_valid(*values):
    import math
    return all(math.isfinite(v) for v in values)


if __name__=="__main__": main()
