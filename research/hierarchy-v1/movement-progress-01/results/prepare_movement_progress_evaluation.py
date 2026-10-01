"""Select the fixed final reward-arm endpoint and generate five preserved-recipe evaluations.

No work on import. Run only after training verification completes. Stages an
exclusive model/snapshot and generated scripts; never runs Unity or changes seeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import torch

BASE = "artifacts/hierarchy-v1/movement-progress-01"
MODEL = "ExecutionV1MovementProgressFinal01"
PARENT = "ExecutionV1SmoothContinuedFinal01"
OLD_SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
CONTROL_SOURCE = "557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f"
CONTROL_MODEL = "ExecutionV1AxesRecoveryFinal01"
PARENT_MODEL_HASH = "40047704eaf92ae933e861abfbe4c6f262a4595685ca985e3c1a185804ed13cb"
PARENT_SNAPSHOT_HASH = "93029a5bfe5a13815f47d1487ff15c3e9455516ee3b5609d9e38f0c0f82e778d"
TEMPLATES = {
    "narrow/A": ("research/hierarchy-v1/fresh-placement-01/fresh-final-A.cs", "db9052b7a65648e0aeee221dc62686ada36830ca4855a8fe9d4af48573f777d4"),
    "narrow/B": ("research/hierarchy-v1/fresh-placement-01/fresh-final-B.cs", "b514d4774fda239b57241f6817dc442f0c973760e07c56090c4fb707f61b748e"),
    "narrow/random": ("research/hierarchy-v1/fresh-placement-01/fresh-final-random.cs", "1e506afe706eac3a155eb7c1e11f5567e6f5c4dff597523290466edad8f48864"),
    "wide/A": ("research/hierarchy-v1/wide-movement-01/wide-final-A.cs", "762f7182d2b8e3c8b39a73116ca7b919c2ab8f8c22741db0a09e096d19323579"),
    "wide/B": ("research/hierarchy-v1/wide-movement-01/wide-final-B.cs", "e94401fee21defbf7b66fb14c249a21c7d843c71dc174a3bc8aa5edbefa75b84"),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inside(root, relative):
    path = (root/relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(root), "Path escapes repository")
    return path


def same_state(a, b):
    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and a.dtype == b.dtype and torch.equal(a,b)
    if isinstance(a, dict):
        return isinstance(b,dict) and a.keys() == b.keys() and all(same_state(a[key],b[key]) for key in a)
    if isinstance(a,(list,tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(same_state(x,y) for x,y in zip(a,b))
    return type(a) is type(b) and a == b


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path("F:/dev/picklebot"))
    args=parser.parse_args()
    root=args.root.resolve()
    base=root/BASE
    plan_path=base/"plan.json"
    plan=read(plan_path)
    proof_path=base/"training/verification.json"
    proof=read(proof_path)
    require(plan["version"] == "execution-movement-progress-01" and plan["initialStep"] == 1048609
            and plan["targetGlobalStep"] == 2097152 and plan["sourceIdentity"] not in (OLD_SOURCE,CONTROL_SOURCE), "Wrong movement-progress campaign")
    require(proof["status"] == "completed_continuation_check" and proof["resumeStateExact"] is True
            and proof["parentRunUnchanged"] is True and proof["rewardFormulaVerified"] is True, "Training verification did not pass")
    require(proof["sourceIdentity"] == plan["sourceIdentity"] and proof["initialStep"] == plan["initialStep"], "Training identity mismatch")
    require(proof["rewardChange"] == plan["rewardChange"] and len(proof["movementProgressRewardAudit"]) == 8
            and all(row["scopeAndCapVerified"] for row in proof["movementProgressRewardAudit"]), "Focus reward audit incomplete")
    require(plan["rewardChange"]["evaluationFlag"] is False and plan["evaluation"]["evaluateMidpoint"] is False,
            "Final evaluation must disable reward shaping and use the fixed endpoint")
    selection=plan["evaluation"]["finalSelection"]
    require(selection["model"] == MODEL and selection["minimumStep"] == 2097152 and selection["exclusiveMaximumStep"] == 2105344, "Final endpoint declaration changed")
    step=proof["experiences"]
    require(type(step) is int and selection["minimumStep"] <= step < selection["exclusiveMaximumStep"], "Final export outside fixed budget")
    source=read(inside(root,plan["sourceRecordPath"]))
    require(source["sourceIdentity"] == plan["sourceIdentity"] and source["parentSourceIdentity"] == CONTROL_SOURCE, "Current source manifest mismatch")
    require(set(plan["evaluation"]["batteries"]) == {"narrow","wide"},"Unexpected evaluation batteries")
    for name,expected_first,expected_count,expected_conditions in (("narrow",1109593,256,["A","B","random"]),("wide",1109849,512,["A","B"])):
        battery=plan["evaluation"]["batteries"][name]
        old_plan=read(root/battery["baselineCampaign"]/"plan.json")
        require(battery["firstSeed"] == expected_first and battery["baseResets"] == expected_count
                and battery["conditions"] == expected_conditions and battery["physicalRecipe"] == old_plan["physicalRecipe"]
                and battery["evaluationMovementForwardProgressReward"] is False,"Frozen evaluation recipe differs from preserved template")
    baseline_identities=plan["evaluation"]["baselineModelIdentities"]
    require(set(baseline_identities) == {"ExecutionV1Initial",PARENT,CONTROL_MODEL}, "Three comparison identities required")
    for name,identity in baseline_identities.items():
        require(identity["sourceIdentity"] == (CONTROL_SOURCE if name == CONTROL_MODEL else OLD_SOURCE), "Historical model source relabelled")
        for path_key,hash_key in (("assetPath","modelHash"),("checkpoint","checkpointHash")):
            require(sha(inside(root,identity[path_key])) == identity[hash_key],"Preserved comparison model changed")
    frozen=dict(plan["evaluation"]["baselineInputs"])
    for relative,expected in {**source["files"],**frozen}.items():
        require(sha(inside(root,relative)) == expected,"Frozen source/baseline changed: "+relative)
    result=root/"artifacts/mlagents"/plan["runId"]
    folder=result/"PicklebotExecutionV1"
    checkpoint=folder/"checkpoint.pt"
    model=result/"PicklebotExecutionV1.onnx"
    require(sha(checkpoint) == proof["checkpointHash"] and sha(model) == proof["modelHash"], "Framework final outputs changed")
    state=torch.load(checkpoint,map_location="cpu",weights_only=False)
    steps=list(state["global_step"].values())
    require(len(steps) == 1 and steps[0].numel() == 1 and steps[0].item() == step, "Stored checkpoint step mismatch")
    numbered=folder/f"PicklebotExecutionV1-{step}.pt"
    numbered_model=numbered.with_suffix(".onnx")
    require(numbered.is_file() and numbered_model.is_file() and sha(numbered_model) == sha(model), "Final numbered export pair missing/different")
    require(same_state(state,torch.load(numbered,map_location="cpu",weights_only=False)), "Final numbered checkpoint differs from mutable final state")
    require(tuple(state["Policy"]["network_body._body_endoder.seq_layers.0.weight"].shape) == (128,136), "Executor shape changed")
    asset=root/f"Assets/Picklebot/PlayerLearning/Models/{MODEL}.onnx"
    snapshot=root/"training/snapshots/execution-v1-movement-progress-final-01.pt"
    selected_path=base/"selected-models.json"
    require(not asset.exists() and not snapshot.exists() and not selected_path.exists(), "Endpoint already staged; preserve existing outputs")
    identity=dict(model=MODEL,step=step,assetPath=asset.relative_to(root).as_posix(),checkpoint=snapshot.relative_to(root).as_posix(),
                  modelHash=sha(model),checkpointHash=sha(numbered),sourceIdentity=plan["sourceIdentity"])
    generated={}
    for key,(template_relative,expected) in TEMPLATES.items():
        battery,condition=key.split("/")
        path=inside(root,template_relative)
        require(sha(path) == expected,"Preserved evaluation template changed")
        code=path.read_text(encoding="utf-8-sig")
        baseline_campaign=plan["evaluation"]["batteries"][battery]["baselineCampaign"]
        old_output=baseline_campaign+"/evaluation/"
        require(old_output in code,"Template output prefix missing")
        code=code.replace(old_output,BASE+f"/evaluation/{battery}/")
        code=code.replace(PARENT,MODEL).replace(PARENT_MODEL_HASH,identity["modelHash"]).replace(PARENT_SNAPSHOT_HASH,identity["checkpointHash"])
        code=code.replace(OLD_SOURCE,plan["sourceIdentity"]).replace("step=1048609,",f"step={step},")
        # Templates contain original Windows root literals; only paths change.
        code=code.replace("F:/dev/picklebot",root.as_posix())
        configure="    run.AutoRun=false;run.RequireTrainer=false;run.Task=\"movement-maintenance\";"
        require(code.count(configure) == 1,"Reward configuration hook changed")
        code=code.replace(configure,configure+"\n    run.MovementForwardProgressReward=false;")
        progress_guard='''        if(run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Forward-progress reward must remain disabled in evaluation");
        foreach(var rewardArena in run.ActiveArenas)
            if(rewardArena.Drill.MovementForwardProgressRewardEnabled||rewardArena.Drill.MovementForwardProgressReward!=0f||rewardArena.Drill.MovementForwardProgressRewardedSteps!=0)
                throw new System.InvalidOperationException("Evaluation drill accumulated disabled forward-progress reward");
'''
        require(code.count("        run.StepOneTick();") == 1,"Evaluation tick hook changed")
        code=code.replace("        run.StepOneTick();",progress_guard+"        run.StepOneTick();")
        require(code.count('    System.IO.File.WriteAllText(output+"/first-decisions.json"') == 1,"Evaluation final guard hook changed")
        code=code.replace('    System.IO.File.WriteAllText(output+"/first-decisions.json"',progress_guard+'    System.IO.File.WriteAllText(output+"/first-decisions.json"')
        creation="var root=new UnityEngine.GameObject(\"Two-region evaluation\");root.SetActive(false);"
        require(code.count(creation) == 1,"Evaluation output guard hook changed")
        code=code.replace(creation,'if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing evaluation directory");\n'+creation)
        guard=f'''string progressRepo=@"{root.as_posix()}";
System.Func<string,string> progressHash=path=>{{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}};
System.Action verifyProgressInputs=()=>{{
    if(progressHash(@"{plan_path.as_posix()}")!="{sha(plan_path)}")throw new System.InvalidOperationException("Frozen movement-progress plan changed");
    if(progressHash(@"{snapshot.as_posix()}")!="{identity['checkpointHash']}")throw new System.InvalidOperationException("Selected checkpoint changed");
    if(progressHash(@"{inside(root,plan['sourceRecordPath']).as_posix()}")!="{sha(inside(root,plan['sourceRecordPath']))}")throw new System.InvalidOperationException("Frozen source manifest changed");
    var progressSource=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(@"{inside(root,plan['sourceRecordPath']).as_posix()}"));
    if((string)progressSource["sourceIdentity"]!="{plan['sourceIdentity']}")throw new System.InvalidOperationException("Movement-progress source identity changed");
    foreach(var file in ((Newtonsoft.Json.Linq.JObject)progressSource["files"]).Properties())if(progressHash(System.IO.Path.Combine(progressRepo,file.Name))!=(string)file.Value)throw new System.InvalidOperationException("Movement-progress source file changed: "+file.Name);
}};
verifyProgressInputs();
'''
        code=guard+code
        needle="    result=Newtonsoft.Json.JsonConvert.SerializeObject"
        require(code.count(needle) == 1,"Evaluation result hook changed")
        code=code.replace(needle,"    verifyProgressInputs();\n"+needle)
        generated_path=Path(__file__).with_name(f"progress-final-{battery}-{condition}.cs")
        require(not generated_path.exists(),"Generated evaluation script already exists")
        generated[key]=(generated_path,code,template_relative,expected)
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(numbered,snapshot)
    shutil.copy2(model,asset)
    require(sha(snapshot) == identity["checkpointHash"] and sha(asset) == identity["modelHash"],"Staged endpoint differs")
    scripts={}
    for key,(path,code,template_relative,expected) in generated.items():
        with path.open("x",encoding="utf-8",newline="\n") as handle: handle.write(code)
        scripts[key]=dict(path=str(path.resolve()),sha256=sha(path),template=template_relative,templateSha256=expected)
    record=dict(final=identity,selection="Mandatory framework final endpoint; no performance-based checkpoint selection",scripts=scripts,
                planHash=sha(plan_path),trainingVerificationHash=sha(proof_path),preparerHash=sha(Path(__file__)),
                frameworkFinalCheckpoint=checkpoint.relative_to(root).as_posix(),frameworkFinalCheckpointHash=sha(checkpoint),
                numberedFinalCheckpoint=numbered.relative_to(root).as_posix(),numberedFinalCheckpointHash=sha(numbered),
                finalNumberedAndMutableStateEqual=True,baselineModelIdentities=baseline_identities,
                baselineSourceIdentities=plan["evaluation"]["baselineSourceIdentities"],candidateSourceIdentity=plan["sourceIdentity"],
                evaluationMovementForwardProgressReward=False,
                optionalMidpointEvaluationsPrepared=False,midpointRequestedByPlan=plan["evaluation"]["evaluateMidpoint"],
                evaluationsLaunched=False,finalSeedsConsumed=False,masteryAccepted=False)
    with selected_path.open("x",encoding="utf-8") as handle:
        json.dump(record,handle,indent=2)
        handle.write("\n")
    print(json.dumps(record,indent=2))


if __name__ == "__main__":
    main()
