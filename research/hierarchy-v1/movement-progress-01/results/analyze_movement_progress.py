"""Compare the fixed progress-reward endpoint against three preserved baselines.

Old evaluations retain their original source/model identities. Comparisons require
paired physical observations and targets. No new threshold or mastery declaration.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.dont_write_bytecode=True
BASE="artifacts/hierarchy-v1/movement-progress-01"
INITIAL="ExecutionV1Initial"
PARENT="ExecutionV1SmoothContinuedFinal01"
FINAL="ExecutionV1MovementProgressFinal01"
CONTROL="ExecutionV1AxesRecoveryFinal01"
BASELINES=(INITIAL,PARENT,CONTROL)
MODELS=(*BASELINES,FINAL)
OLD_SOURCE="5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
CONTROL_SOURCE="557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f"
CONTROL_BASE="artifacts/hierarchy-v1/axes-recovery-01"
PROGRESS_FIELDS=("movementForwardProgressRewardEnabled","movementForwardProgressReward","movementForwardProgressRewardedSteps")
WIDE_HELPER="research/hierarchy-v1/wide-movement-01/analyze_wide_movement.py"
WIDE_HELPER_HASH="4dd61ae3a1fb072567ddbfd0c8600f0798dc7d016057763b2ef7b77fd09750f1"


def require(ok,message):
    if not ok: raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def record(root,path,inputs,expected=None):
    path=path.resolve()
    require(path.is_file(),"Missing input: "+str(path))
    digest=sha(path)
    require(expected is None or digest == expected,"Input hash mismatch: "+str(path))
    key=path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    inputs[key]=digest


def load_helpers(root,inputs):
    path=root/WIDE_HELPER
    record(root,path,inputs,WIDE_HELPER_HASH)
    spec=importlib.util.spec_from_file_location("preserved_wide_diagnostic",path)
    require(spec is not None and spec.loader is not None,"Cannot load preserved analyzer")
    w=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    f,h=w.load_helpers(root,inputs)
    return w,f,h


def verify_endpoint(root,base,plan,inputs):
    import torch

    selection_path=base/"selected-models.json"
    proof_path=base/"training/verification.json"
    record(root,selection_path,inputs)
    record(root,proof_path,inputs)
    selected,proof=read(selection_path),read(proof_path)
    record(root,Path(__file__).with_name("prepare_movement_progress_evaluation.py"),inputs,selected["preparerHash"])
    require(selected["planHash"] == sha(base/"plan.json") and selected["trainingVerificationHash"] == sha(proof_path),"Selection predates a different plan/training proof")
    require(proof["status"] == "completed_continuation_check" and proof["resumeStateExact"] is True
            and proof["parentRunUnchanged"] is True and proof["rewardFormulaVerified"] is True,"Training proof did not pass")
    require(proof["rewardChange"] == plan["rewardChange"] and len(proof["movementProgressRewardAudit"]) == 8
            and all(row["scopeAndCapVerified"] for row in proof["movementProgressRewardAudit"]),"Focus reward verification incomplete")
    require(selected["baselineModelIdentities"] == plan["evaluation"]["baselineModelIdentities"]
            and selected["baselineSourceIdentities"] == plan["evaluation"]["baselineSourceIdentities"]
            and selected["evaluationMovementForwardProgressReward"] is False,"Staged evaluation changed baseline/reward declarations")
    identity=selected["final"]
    require(identity["model"] == FINAL and identity["sourceIdentity"] == plan["sourceIdentity"] == proof["sourceIdentity"],"Final model/source mismatch")
    endpoint=plan["evaluation"]["finalSelection"]
    require(identity["step"] == proof["experiences"] and endpoint["minimumStep"] <= identity["step"] < endpoint["exclusiveMaximumStep"],"Fixed final endpoint violated")
    require(identity["modelHash"] == proof["modelHash"] and selected["frameworkFinalCheckpointHash"] == proof["checkpointHash"],"Endpoint is not the verified final export")
    for key,digest in (("assetPath","modelHash"),("checkpoint","checkpointHash")):
        record(root,root/identity[key],inputs,identity[digest])
    mutable=root/selected["frameworkFinalCheckpoint"]
    numbered=root/selected["numberedFinalCheckpoint"]
    record(root,mutable,inputs,selected["frameworkFinalCheckpointHash"])
    record(root,numbered,inputs,selected["numberedFinalCheckpointHash"])
    record(root,numbered.with_suffix(".onnx"),inputs,identity["modelHash"])
    states=[torch.load(path,map_location="cpu",weights_only=False) for path in (root/identity["checkpoint"],mutable,numbered)]
    def equal(a,b):
        if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and a.dtype == b.dtype and torch.equal(a,b)
        if isinstance(a,dict):return isinstance(b,dict) and a.keys() == b.keys() and all(equal(a[k],b[k]) for k in a)
        if isinstance(a,(list,tuple)):return type(a) is type(b) and len(a) == len(b) and all(equal(x,y) for x,y in zip(a,b))
        return type(a) is type(b) and a == b
    require(all(equal(states[0],state) for state in states[1:]),"Numbered/mutable/snapshot final state differs")
    steps=list(states[0]["global_step"].values())
    require(len(steps) == 1 and steps[0].numel() == 1 and steps[0].item() == identity["step"],"Stored final step differs")
    require(tuple(states[0]["Policy"]["network_body._body_endoder.seq_layers.0.weight"].shape) == (128,136),"Executor dimensions changed")
    for key,item in selected["scripts"].items():
        record(root,Path(item["path"]),inputs,item["sha256"])
        record(root,root/item["template"],inputs,item["templateSha256"])
    return identity,selected


def with_source(module,source,callback):
    """Parameterize only a validator's expected source; immutable file is untouched.

    The imported legacy validator exposes source as a module constant rather than
    an argument. Calls are serial and the constant is restored in a finally block.
    Its physical recipe, observed controls and outcome checks remain unchanged.
    """
    original=module.SOURCE
    module.SOURCE=source
    try:return callback()
    finally:module.SOURCE=original


def verify_disabled_reward(rows,report,current):
    """New telemetry must be zero; historical records remain unmodified."""
    if current or "movementForwardProgressReward" in report:
        require(report.get("movementForwardProgressReward") is False,"Evaluation enabled training-only progress shaping")
    present=0
    for row in rows.values():
        fields=set(PROGRESS_FIELDS)&set(row)
        require(not fields or fields == set(PROGRESS_FIELDS),"Partial progress telemetry schema")
        require(not current or fields == set(PROGRESS_FIELDS),"Current evaluator omitted progress telemetry")
        if fields:
            require(row[PROGRESS_FIELDS[0]] is False and row[PROGRESS_FIELDS[1]] == 0
                    and row[PROGRESS_FIELDS[2]] == 0,"Progress shaping leaked into evaluation")
            present+=1
    return dict(attempts=len(rows),explicitDisabledTelemetryAttempts=present,
                historicalTelemetryAbsentAttempts=len(rows)-present,allRecordedProgressBonusesZero=True)


def physical_episode(row):
    # Only the paired negative-control comparison omits pure reward accounting.
    # Raw rows/files retain all fields; verify_disabled_reward checks additions.
    return {key:value for key,value in row.items() if key not in ("reward",*PROGRESS_FIELDS)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path("F:/dev/picklebot"))
    args=parser.parse_args()
    root=args.root.resolve()
    base=root/BASE
    output=base/"audit/analysis.json"
    require(not output.exists(),"Refusing to overwrite analysis")
    inputs={}
    record(root,base/"plan.json",inputs)
    plan=read(base/"plan.json")
    require(plan["version"] == "execution-movement-progress-01" and plan["initialStep"] == 1048609
            and plan["targetGlobalStep"] == 2097152,"Unexpected campaign")
    expected_sources={INITIAL:OLD_SOURCE,PARENT:OLD_SOURCE,CONTROL:CONTROL_SOURCE}
    require(plan["parentSourceIdentity"] == OLD_SOURCE and plan["controlSourceIdentity"] == CONTROL_SOURCE
            and plan["controlCampaign"] == CONTROL_BASE and plan["evaluation"]["baselineSourceIdentities"] == expected_sources
            and plan["evaluation"]["candidateSourceIdentity"] == plan["sourceIdentity"] not in (OLD_SOURCE,CONTROL_SOURCE),"Source provenance declaration mismatch")
    require(plan["finalSeedsConsumed"] is False and plan["masteryAccepted"] is False
            and plan["limits"]["automaticPromotion"] is False,"Unexpected acceptance/final-seed declaration")
    w,f,h=load_helpers(root,inputs)
    for relative,expected in plan["evaluation"]["baselineInputs"].items():
        record(root,f.inside(root,relative),inputs,expected)
    for key in ("sourceRecordPath","buildRecordPath"):
        record(root,root/plan[key],inputs)
    source,build=(read(root/plan[key]) for key in ("sourceRecordPath","buildRecordPath"))
    require(source["sourceIdentity"] == build["sourceIdentity"] == plan["sourceIdentity"]
            and source["parentSourceIdentity"] == CONTROL_SOURCE and build["buildIdentity"] == plan["buildIdentity"],"Source/build proof mismatch")
    require(hashlib.sha256(json.dumps(source["files"],sort_keys=True,separators=(",",":")).encode()).hexdigest() == plan["sourceIdentity"],"Source contents do not hash to identity")
    for relative,expected in source["files"].items():record(root,root/relative,inputs,expected)
    tests_path=Path(source["testsPath"])
    record(root,tests_path,inputs,source["testsHash"])
    test_paths=[tests_path]
    for item in source["additionalTests"]:
        path=Path(item["path"])
        record(root,path,inputs,item["sha256"])
        test_paths.append(path)
    cases=[]
    for path in test_paths:
        result=ET.parse(path).getroot()
        require(result.attrib.get("result") == "Passed","Preserved reward/default tests did not pass")
        cases.extend(result.iter("test-case"))
    require(source["totalPassedTestCases"] == len(cases) == 50 and all(case.attrib.get("result") == "Passed" for case in cases),"Expected 50 preserved reward/default checks")
    ledger_path=root/"artifacts/player-v3/seed-ledger.json"
    record(root,ledger_path,inputs)
    require(read(ledger_path)["finalSeedsConsumed"] == [],"Final evaluation seeds consumed")
    final_identity,selection=verify_endpoint(root,base,plan,inputs)
    require(set(selection["scripts"]) == {"narrow/A","narrow/B","narrow/random","wide/A","wide/B"},"Mandatory final evaluation set differs")
    batteries={}
    all_identities={**plan["evaluation"]["baselineModelIdentities"],FINAL:final_identity}
    require(set(all_identities) == set(MODELS),"Missing comparison model identity")
    control_base=root/CONTROL_BASE
    control_selected=read(control_base/"selected-models.json")
    control_analysis=read(control_base/"audit/analysis.json")
    require(control_analysis["status"] == "complete_axes_recovery_final_assessment"
            and control_selected["final"] == control_analysis["modelIdentities"][CONTROL] == all_identities[CONTROL],"Completed axes-control identity differs")
    for model in BASELINES:
        identity=all_identities[model]
        require(identity["sourceIdentity"] == expected_sources[model],"Historical model runtime identity relabelled")
        for path_key,hash_key in (("assetPath","modelHash"),("checkpoint","checkpointHash")):
            record(root,root/identity[path_key],inputs,identity[hash_key])
    for name,battery in plan["evaluation"]["batteries"].items():
        require(name in ("narrow","wide"),"Unexpected extra evaluation battery")
        first,count=(1109593,256) if name == "narrow" else (1109849,512)
        conditions=("A","B","random") if name == "narrow" else ("A","B")
        require(battery["firstSeed"] == first and battery["baseResets"] == count and tuple(battery["conditions"]) == conditions
                and battery["baselineModels"] == list(BASELINES) and battery["finalModel"] == FINAL
                and battery["evaluationMovementForwardProgressReward"] is False,"Battery/reset selection changed")
        old_base=root/battery["baselineCampaign"]
        old_plan,old_analysis=read(old_base/"plan.json"),read(old_base/"audit/analysis.json")
        require(old_plan["sourceIdentity"] == OLD_SOURCE and old_plan["physicalRecipe"] == battery["physicalRecipe"],"Baseline recipe/identity changed")
        for model in (INITIAL,PARENT):
            identity=old_plan["modelIdentities"][model]
            require(identity == all_identities[model],"Common baseline identity differs from original battery")
        require(control_analysis["batteries"][name]["physicalRecipe"] == battery["physicalRecipe"]
                and control_analysis["batteries"][name]["physicalObservationAndGoalParity"] is True,"Axes-control physical anchor differs")
        seeds=list(range(first,first+count))
        fixture,descriptors={},{}
        if name == "wide":
            frozen=read(old_base/"fixture-hashes.json")
            for ordinal in range(0,512,64):
                filename=f"wide-fixture-{ordinal:04d}.json"
                path=old_base/"fixture"/filename
                record(root,path,inputs,frozen[filename])
                batch=read(path)
                require(batch["sourceIdentity"] == OLD_SOURCE and batch["policyActions"] == batch["physicsTicks"] == 0,"Original fixture identity changed")
                fixture.update({row["seed"]:row for row in batch["rows"]})
                if not descriptors: descriptors={row["seed"]:row for row in batch["planned"]}
            require(sorted(fixture) == sorted(descriptors) == seeds,"Wide fixture coverage mismatch")
        runs={}
        disabled={}
        for model in MODELS:
            identity=all_identities[model]
            if model == FINAL:
                folder_base=base/"evaluation"/name/model
            else:
                folder_base=f.inside(root,battery["baselineEvaluationRoots"][model])
                expected_folder=control_base/"evaluation"/name/model if model == CONTROL else old_base/"evaluation"/model
                require(folder_base.resolve() == expected_folder.resolve(),"Historical evaluation root changed")
            for condition in conditions:
                folder=folder_base/condition
                # Existing raw rows are protected by the frozen plan. Additional
                # summary metadata consumed by the wide validator is protected by
                # the prior completed analysis, not newly relabelled as current.
                if model != FINAL:
                    summary_path=folder/"summary.json"
                    record(root,summary_path,inputs,plan["evaluation"]["baselineInputs"][summary_path.relative_to(root).as_posix()])
                if name == "narrow":
                    runs[model,condition]=with_source(f,identity["sourceIdentity"],lambda: f.validate_run(h,root,folder,model,condition,identity,seeds,inputs))
                else:
                    runs[model,condition]=with_source(w,identity["sourceIdentity"],lambda: w.validate_run(f,h,root,folder,model,condition,identity,seeds,descriptors,fixture,inputs))
                disabled[f"{model}/{condition}"]=verify_disabled_reward(runs[model,condition][0],runs[model,condition][3],model == FINAL)
                if model == FINAL and name == "narrow":
                    record(root,folder/"summary.json",inputs)
                    summary=read(folder/"summary.json")
                    expected=dict(model=FINAL,condition=condition,episodes=count,
                                  legal=sum(row["legalLanding"] for row in runs[model,condition][1].values()),
                                  targets=sum(row["targetHit"] for row in runs[model,condition][1].values()))
                    require(summary == expected,"New narrow summary differs from raw outcomes")
        keys={}
        negative=dict(resetPairs=count,identicalInitializerActions=0,identicalInitializerPhysicalEpisodes=0)
        for seed in seeds:
            keys[seed]=f.physical_key(runs[INITIAL,"A"][2][seed]["observation"])
            for model in MODELS:
                for condition in conditions:
                    ep,goals,decisions,_=runs[model,condition]
                    ref=runs[INITIAL,condition]
                    require(f.physical_key(decisions[seed]["observation"]) == keys[seed],f"{name}/{model}/{condition}/{seed}: physical observation mismatch")
                    require(np.array_equal(np.asarray(decisions[seed]["observation"],dtype=np.float32),np.asarray(ref[2][seed]["observation"],dtype=np.float32)),"Goal or physical observation changed between sources/models")
                    require(h.group_key(ep[seed]) == h.group_key(ref[0][seed]),"Physical reset descriptor changed")
                    require(np.array_equal(np.asarray(h.target(goals[seed]),dtype=np.float32),np.asarray(h.target(ref[1][seed]),dtype=np.float32))
                            and goals[seed]["radius"] == ref[1][seed]["radius"],"Requested target changed")
            a,b=runs[INITIAL,"A"],runs[INITIAL,"B"]
            require(np.array_equal(a[2][seed]["physical"],b[2][seed]["physical"]),"Initializer action negative control failed")
            require(physical_episode(a[0][seed]) == physical_episode(b[0][seed]),"Initializer physical negative control failed")
            negative["identicalInitializerActions"]+=1
            negative["identicalInitializerPhysicalEpisodes"]+=1
        groups={"all":seeds}
        base_eps=runs[INITIAL,"A"][0]
        for task in f.DRILLS:groups[f"drill/{task}"]=[seed for seed in seeds if base_eps[seed]["task"] == task]
        for player in range(4):groups[f"player/{player}"]=[seed for seed in seeds if base_eps[seed]["player"] == player]
        for side,value in (("left",True),("right",False)):
            groups[f"serve/{side}"]=[seed for seed in seeds if base_eps[seed]["task"] == "stationary-serve" and base_eps[seed]["serveFromLeft"] is value]
        if name == "wide":
            for direction in w.DIRECTIONS:groups[f"axis/{direction}"]=[seed for seed in seeds if descriptors[seed]["direction"] == direction]
            for cm in (25,50,75,100):groups[f"nominal-shift/{cm}cm"]=[seed for seed in seeds if descriptors[seed]["centimetres"] == cm]
            for label,challenge in (("familiar",False),("axis-challenge",True)):
                groups[f"schedule/{label}"]=[seed for seed in seeds if descriptors[seed]["challenge"] is challenge]
        else:
            for category in ("actual-movement","central-or-familiar"):
                groups[f"movement/{category}"]=[seed for seed in seeds if h.group_key(base_eps[seed])[2] == category]
        groups={key:value for key,value in groups.items() if value}
        summaries,causal,clustered,matrices,telemetry,changes={},{},{},{},{},{}
        for group,chosen in groups.items():
            summaries[group],causal[group],clustered[group],matrices[group],telemetry[group],changes[group]={},{},{},{},{},{}
            gains={}
            for model in MODELS:
                summaries[group][model]={condition:h.metrics([runs[model,condition][1][seed] for seed in chosen]) for condition in conditions}
                causal[group][model],gains[model]=h.causal([runs[model,"A"][1][seed] for seed in chosen],[runs[model,"B"][1][seed] for seed in chosen])
                clustered[group][model]=f.unique_cluster_ci(h,gains[model],chosen,keys)
                matrices[group][model]=f.target_matrix(h,runs,model,chosen)
                telemetry[group][model]={condition:w.telemetry(f,[runs[model,condition][0][seed] for seed in chosen]) for condition in conditions}
            require(np.all(gains[INITIAL] == 0),"Target-blind causal control failed")
            for baseline in BASELINES:
                changes[group][baseline]={"assignmentGainResetWeighted":h.ci(gains[FINAL]-gains[baseline]),
                    "assignmentGainUniqueClusterWeighted":f.unique_cluster_ci(h,gains[FINAL]-gains[baseline],chosen,keys),
                    "conditions":{condition:h.paired_changes_for([runs[baseline,condition][1][seed] for seed in chosen],[runs[FINAL,condition][1][seed] for seed in chosen]) for condition in conditions},
                    "telemetry":{condition:w.paired_telemetry(h,[runs[baseline,condition][0][seed] for seed in chosen],[runs[FINAL,condition][0][seed] for seed in chosen]) for condition in conditions}}
        screens={}
        if name == "narrow":
            existing=battery["existingScreen"]
            require(existing == old_plan["screening"] and existing["maximumPerDrillLegalDrop"] == .05,"Existing narrow screen changed")
            for baseline in BASELINES:
                retention=[{"drill":task,"condition":condition,**changes[f"drill/{task}"][baseline]["conditions"][condition]["legalRateChange"]} for task in f.DRILLS for condition in conditions]
                tests=dict(resetWeightedAssignmentGainCiLowerAboveZero=causal["all"][FINAL]["assignmentGain"]["ci95"][0]>0,
                           uniqueClusterWeightedAssignmentGainCiLowerAboveZero=clustered["all"][FINAL]["ci95"][0]>0,
                           bothRegionTargetRatesExceedBaseline=all(changes["all"][baseline]["conditions"][condition]["targetRateChange"]["mean"]>0 for condition in ("A","B")),
                           noDrillLegalDropGreaterThanFivePercentagePoints=all(row["mean"]>=-.05-1e-12 for row in retention))
                screens[baseline]=dict(existingCriteria=existing,tests=tests,descriptivePass=all(tests.values()),retentionChecks=retention,
                                       interpretation="Existing narrow screen applied descriptively against this baseline; point-estimate retention limit, not statistical noninferiority or promotion.")
        cluster_members={}
        for seed,key in keys.items():cluster_members.setdefault(key,[]).append(seed)
        joint=[]
        if name == "wide":
            for task in f.DRILLS[2:]:
                for direction in w.DIRECTIONS:
                    for cm in (25,50,75,100):
                        for player in range(4):
                            chosen=[seed for seed in seeds if (descriptors[seed]["task"],descriptors[seed]["direction"],descriptors[seed]["centimetres"],descriptors[seed]["player"]) == (task,direction,cm,player)]
                            counts={model:{condition:w.compact([runs[model,condition][0][seed] for seed in chosen],[runs[model,condition][1][seed] for seed in chosen]) for condition in conditions} for model in MODELS}
                            joint.append(dict(drill=task,direction=direction,nominalShiftCm=cm,player=player,attempts=len(chosen),counts=counts))
        batteries[name]=dict(firstSeed=first,baseResets=count,conditions=list(conditions),physicalRecipe=battery["physicalRecipe"],
            baselineCampaign=battery["baselineCampaign"],baselineSourceIdentities=expected_sources,candidateSourceIdentity=plan["sourceIdentity"],
            baselineEvaluationRoots=battery["baselineEvaluationRoots"],evaluationMovementForwardProgressReward=False,
            disabledRewardTelemetry=disabled,
            physicalObservationAndGoalParity=True,negativeControl=negative,summaries=summaries,causalResetWeighted=causal,
            causalUniqueClusterWeighted=clustered,pairedFinalMinusBaseline=changes,targetConfusionMatrices=matrices,
            actualContactAndMovementTelemetry=telemetry,existingNarrowScreen=screens,descriptiveWideJointCells=joint,
            physicalObservationClusters=dict(resetPairs=count,uniqueClusters=len(cluster_members),duplicateInstances=count-len(cluster_members),
                clusters=[dict(fingerprintSha256=hashlib.sha256(np.asarray(key,dtype="<f4").tobytes()).hexdigest(),seeds=members,resetCount=len(members)) for key,members in cluster_members.items()]))
    require(set(batteries) == {"narrow","wide"},"Required evaluation battery is missing")
    result=dict(status="complete_movement_progress_final_assessment",modelIdentities=all_identities,sourceIdentity=plan["sourceIdentity"],
                baselineSourceIdentities=expected_sources,initialTrainingStep=1048609,finalTrainingStep=final_identity["step"],
                models=list(MODELS),comparisonModels=list(BASELINES),controlCampaign=CONTROL_BASE,
                evaluationMovementForwardProgressReward=False,
                endpointSelection="Verified framework final export; no performance-based selection",batteries=batteries,
                inputSha256=inputs,analysisScriptSha256=sha(Path(__file__)),
                baselineReuse="Initializer/common-parent records retain original5f identity; axes-control records retain557040f9 identity. New reward remains disabled in final evaluation. Original raw records are unchanged; only pure reward accounting fields are omitted from the paired physical negative-control comparison after verifying recorded additions are disabled/zero. Passed default/reward tests and exact first124/full136 observation pairing protect the comparison.",
                bootstrap=dict(seed=h.BOOTSTRAP_SEED,replicates=h.BOOTSTRAP_DRAWS,pointwiseOnly=True,
                    resetWeighted="Matched base-reset bootstrap preserves model/instruction correspondence.",
                    clusterWeighted="Paired gains averaged within exact physical-observation clusters; clusters resampled equally."),
                limitations=["One matched-seed reward arm versus an already completed axes control, both initialized from common parent1048609; not replicated causal proof or independent training replication.",
                             "Both batteries reuse development anchors. Distinct seed IDs and observation clusters do not prove generalization.",
                             "Axes training focus ends at25cm;50-100cm wide cases are transfer probes. Nominal feed displacement is not required or actual root travel.",
                             "Conditional contact-displacement and landing-response summaries omit noncontacts/illegal landings only in explicitly labelled conditional estimands; outcome rates retain all attempts.",
                             "Rally-bounce feed names do not impose a bounce requirement. Actual contact flags separate volleys, bounced rally contacts and required-bounce opening returns.",
                             "Existing narrow checks are descriptive. No new wide pass threshold, automatic promotion, architecture recommendation or mastery claim is inferred."],
                promoted=False,automaticExtension=False,masteryAccepted=False,finalSeedsConsumed=False)
    for key,expected in inputs.items():
        path=Path(key) if Path(key).is_absolute() else root/key
        require(sha(path) == expected,"Input changed during analysis: "+key)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as handle:
        json.dump(result,handle,indent=2,allow_nan=False)
        handle.write("\n")
    print(json.dumps(dict(analysis=str(output),finalStep=final_identity["step"],batteries=list(batteries),masteryAccepted=False),indent=2))


if __name__ == "__main__":main()
