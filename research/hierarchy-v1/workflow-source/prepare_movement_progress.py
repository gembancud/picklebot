"""Freeze one focus-progress reward arm after the completed axes control review.

No work on import. Requires --freeze-after-axes-review when the campaign owner has
reviewed the completed axes assessment and chosen this experiment. Does not launch
training or evaluations, copy result trees, edit Unity sources, or consume seeds.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import yaml

import run_movement_progress as campaign


def baseline_inputs(root):
    """Require completed before-assessments; freeze their raw evidence and plans."""
    inputs, batteries, identities = {}, {}, {}
    models = ["ExecutionV1Initial", "ExecutionV1SmoothContinuedFinal01"]
    control = root / campaign.CONTROL_BASE
    control_plan = campaign.read(control / "plan.json")
    control_analysis = campaign.read(control / "audit/analysis.json")
    control_selection = campaign.read(control / "selected-models.json")
    control_archive = campaign.read(root / "docs/research/execution-v1-evidence/axes-recovery-01/results/archive-manifest.json")
    campaign.require(control_analysis["status"] == "complete_axes_recovery_final_assessment"
                     and control_analysis["sourceIdentity"] == control_plan["sourceIdentity"] == campaign.CONTROL_SOURCE
                     and control_archive["status"] == "complete_axes_results_archive"
                     and control_archive["analysisHash"] == campaign.sha(control / "audit/analysis.json")
                     and control_archive["planHash"] == campaign.sha(control / "plan.json"), "Completed axes control is not preserved")
    axes_identity = control_selection["final"]
    campaign.require(axes_identity == control_analysis["modelIdentities"][campaign.CONTROL_MODEL]
                     and axes_identity["step"] >= campaign.TARGET
                     and axes_identity["step"] < campaign.TARGET + campaign.BUFFER,
                     "Axes control is not its predeclared final endpoint")
    identities[campaign.CONTROL_MODEL] = axes_identity
    common_control_inputs = [control / name for name in ("plan.json", "audit/analysis.json", "selected-models.json", "training/verification.json", "training/manifest.json", "training/launch.json", "source-records.json", "build-verification.json")]
    common_control_inputs.append(root / control_plan["configPath"])
    for key, hash_key in (("assetPath", "modelHash"), ("checkpoint", "checkpointHash")):
        path = root / axes_identity[key]
        campaign.require(campaign.sha(path) == axes_identity[hash_key], "Axes control model changed")
        common_control_inputs.append(path)
    inputs.update({path.relative_to(root).as_posix(): campaign.sha(path) for path in common_control_inputs})
    for name, directory, first, count, conditions in (
        ("narrow", "fresh-placement-01", 1109593, 256, ["A", "B", "random"]),
        ("wide", "wide-movement-fixture-01", 1109849, 512, ["A", "B"]),
    ):
        folder = root / "artifacts/hierarchy-v1" / directory
        plan_path, analysis_path = folder / "plan.json", folder / "audit/analysis.json"
        plan = campaign.read(plan_path)
        campaign.require(plan["sourceIdentity"] == campaign.PARENT_SOURCE and plan["firstSeed"] == first
                         and plan["seedCount"] == count and plan["models"] == models
                         and plan["conditions"] == conditions and plan["evaluationRewardMode"] == "linear-radius",
                         f"{name}: baseline plan differs")
        campaign.require(isinstance(campaign.read(analysis_path), dict), f"{name}: completed analysis missing")
        paths = [plan_path, analysis_path]
        if name == "wide":
            summary_path = folder / "fixture-summary.json"
            summary = campaign.read(summary_path)
            campaign.require(summary["outcomeAllowed"] and summary["seedCount"] == count
                             and summary["physicsTicks"] == 0 and summary["policyActions"] == 0,
                             "Wide fixture is not ready for the planned diagnostic")
            paths.extend([summary_path, folder / "fixture-hashes.json", folder / "fixture-script-revision-01.json"])
        for model in models:
            identity = plan["modelIdentities"][model]
            campaign.require(model not in identities or identity == identities[model], "Common baseline identity differs by battery")
            identities[model] = identity
            for key, hash_key in (("assetPath", "modelHash"), ("checkpoint", "checkpointHash")):
                path = root / identity[key]
                campaign.require(campaign.sha(path) == identity[hash_key], "Common baseline model changed")
                paths.append(path)
            for condition in conditions:
                evaluation = folder / "evaluation" / model / condition
                report = campaign.read(evaluation / "report.json")
                identity = campaign.read(evaluation / "model-identity.json")
                expected = plan["modelIdentities"][model]
                campaign.require(all(identity[k] == expected[k] for k in ("model", "modelHash", "checkpointHash", "step", "sourceIdentity")),
                                 f"{name}/{model}/{condition}: model identity mismatch")
                campaign.require(report["status"] == "seed_budget_complete" and not report["failure"]
                                 and not report["trainerConnected"] and report["sourceIdentity"] == campaign.PARENT_SOURCE
                                 and report["contract"] == campaign.CONTRACT and report["split"] == "development"
                                 and report["firstSeed"] == first and report["seedCount"] == count
                                 and report["completedEpisodes"] == count, f"{name}/{model}/{condition}: incomplete baseline")
                for filename in ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "model-identity.json", "summary.json"):
                    path = evaluation / filename
                    campaign.require(path.is_file(), f"Missing baseline evidence: {path}")
                    paths.append(path)
        old_battery = control_analysis["batteries"][name]
        campaign.require(old_battery["physicalObservationAndGoalParity"] and old_battery["physicalRecipe"] == plan["physicalRecipe"]
                         and old_battery["firstSeed"] == first and old_battery["baseResets"] == count
                         and old_battery["conditions"] == conditions, "Axes-control anchor differs from common baselines")
        for condition in conditions:
            evaluation = control / "evaluation" / name / campaign.CONTROL_MODEL / condition
            report = campaign.read(evaluation / "report.json")
            identity = campaign.read(evaluation / "model-identity.json")
            campaign.require(all(identity[k] == axes_identity[k] for k in ("model", "modelHash", "checkpointHash", "step", "sourceIdentity")), "Control evaluation model differs")
            campaign.require(report["status"] == "seed_budget_complete" and not report["failure"]
                             and not report["trainerConnected"] and report["sourceIdentity"] == campaign.CONTROL_SOURCE
                             and report["completedEpisodes"] == count and report["firstSeed"] == first,
                             "Control evaluation incomplete")
            for filename in ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "model-identity.json", "summary.json"):
                path = evaluation / filename
                campaign.require(control_analysis["inputSha256"][path.relative_to(root).as_posix()] == campaign.sha(path), "Control raw evidence changed")
                paths.append(path)
        inputs.update({path.relative_to(root).as_posix(): campaign.sha(path) for path in paths})
        batteries[name] = {"firstSeed": first, "baseResets": count, "conditions": conditions,
                           "physicalRecipe": plan["physicalRecipe"], "rewardMode": "linear-radius",
                           "baselineCampaign": folder.relative_to(root).as_posix(),
                           "baselineModels": models + [campaign.CONTROL_MODEL], "finalModel": campaign.FINAL_MODEL,
                           "baselineEvaluationRoots": {**{model: (folder / "evaluation" / model).relative_to(root).as_posix() for model in models},
                                                       campaign.CONTROL_MODEL: (control / "evaluation" / name / campaign.CONTROL_MODEL).relative_to(root).as_posix()},
                           "evaluationMovementForwardProgressReward": False,
                           "interpretation": "Repeated development anchor; not unused test cases or mastery evidence"}
        if name == "narrow":
            batteries[name]["existingScreen"] = plan["screening"]
        else:
            batteries[name]["interpretation"] += "; training adds graded axes only through25cm, while50-100cm remain wider transfer probes"
    return inputs, batteries, identities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--freeze-after-axes-review", action="store_true", help="Campaign owner chose a single reward-only arm after reviewing all axes-control outcomes")
    args = parser.parse_args()
    campaign.require(args.freeze_after_axes_review, "Review the completed axes control before freezing this choice")
    root = args.root.resolve()
    campaign.require(Path(sys.executable).resolve() == (root / "tools/mlagents-training/.pixi/envs/default/python.exe").resolve(),
                     "Use the project's pinned Python")
    base, config = root / campaign.BASE, root / campaign.CONFIG
    campaign.require(base.is_dir() and not (base / "plan.json").exists() and not (base / "training").exists()
                     and not config.exists() and not (root / "artifacts/mlagents" / campaign.RUN).exists(),
                     "Use fresh campaign/config/result paths; existing evidence is preserved")
    campaign.require(campaign.sha(root / campaign.HELPER) == campaign.HELPER_HASH, "Continuation helper changed")
    parent = root / campaign.PARENT_BASE / "training"
    parent_result = root / "artifacts/mlagents" / campaign.PARENT_RUN
    checkpoint, model = parent_result / campaign.BEHAVIOR / "checkpoint.pt", parent_result / f"{campaign.BEHAVIOR}.onnx"
    campaign.require(campaign.sha(checkpoint) == campaign.PARENT_CHECKPOINT_HASH and campaign.sha(model) == campaign.PARENT_MODEL_HASH,
                     "Parent checkpoint/model changed")
    verified = campaign.read(parent / "verification.json")
    campaign.require(verified["status"] == "completed_continuation_check" and verified["experiences"] == campaign.START
                     and verified["checkpointHash"] == campaign.PARENT_CHECKPOINT_HASH and verified["modelHash"] == campaign.PARENT_MODEL_HASH,
                     "Parent completion proof differs")
    source = campaign.read(root / campaign.SOURCE_BASE / "source-records.json")
    build = campaign.read(root / campaign.SOURCE_BASE / "build-verification.json")
    campaign.require(source["sourceIdentity"] == build["sourceIdentity"] and source["sourceIdentity"] not in (campaign.PARENT_SOURCE, campaign.CONTROL_SOURCE)
                     and source["parentSourceIdentity"] == campaign.CONTROL_SOURCE, "A newly verified reward source/build descended from axes control is required")
    campaign.require(build["buildIdentity"] != campaign.read(root / campaign.CONTROL_BASE / "build-verification.json")["buildIdentity"],
                     "Axes control build identity cannot be reused")
    tests_path = Path(source["testsPath"])
    if not tests_path.is_absolute(): tests_path = root / tests_path
    campaign.require(campaign.sha(tests_path) == source["testsHash"]
                     and ET.parse(tests_path).getroot().attrib.get("result") == "Passed", "Reward/default-scope tests did not pass")
    helper = campaign.load_helper(root)
    helper.verify_hashes(root, source["files"])
    helper.verify_hashes(Path(build["directory"]), build["files"])
    old_config = root / campaign.PARENT_CONFIG
    parent_launch = campaign.read(parent / "launch.json")
    campaign.require(campaign.sha(old_config) == parent_launch["configHash"]
                     and campaign.sha(parent / "manifest.json") == parent_launch["manifestHash"], "Parent recipe changed")
    text = old_config.read_text(encoding="utf-8-sig")
    old_settings = yaml.safe_load(text)
    behavior = old_settings["behaviors"][campaign.BEHAVIOR]
    campaign.require(behavior.get("init_path") is None and behavior["max_steps"] == 1048576
                     and behavior["checkpoint_interval"] == 262144 and behavior["keep_checkpoints"] == 4,
                     "Unexpected parent trainer budget or initialization")
    needle = "    max_steps: 1048576"
    campaign.require(text.count(needle) == 1, "Unexpected parent YAML layout")
    text = text.replace(needle, "    max_steps: 2097152")
    proposed = copy.deepcopy(old_settings)
    proposed["behaviors"][campaign.BEHAVIOR]["max_steps"] = campaign.TARGET
    campaign.require(yaml.safe_load(text) == proposed, "Config changed beyond maximum global steps")
    inputs, batteries, baseline_identities = baseline_inputs(root)
    parent_inputs = [checkpoint, model, parent / "verification.json", parent / "launch.json", parent / "manifest.json", old_config,
                     root / campaign.SOURCE_BASE / "source-records.json", root / campaign.SOURCE_BASE / "build-verification.json",
                     root / campaign.HELPER]
    inputs.update({path.relative_to(root).as_posix(): campaign.sha(path) for path in parent_inputs})
    parent_manifest = campaign.read(parent / "manifest.json")
    campaign.require(parent_manifest["sourceIdentity"] == campaign.PARENT_SOURCE and parent_manifest["movementPattern"] == "lateral"
                     and parent_manifest["movementRange"] == .025 and parent_manifest["movementRehearsalRange"] == .1
                     and parent_manifest["movementRecoveryMix"] and parent_manifest["interleavedRecovery"], "Parent physical recipe differs")
    training_manifest = copy.deepcopy(parent_manifest)
    training_manifest.update(evidenceRoot=str(base / "training"), basePort=campaign.BASE_PORT,
                             sourceIdentity=source["sourceIdentity"], buildIdentity=build["buildIdentity"],
                             movementPattern="axes", movementRange=.0625, movementForwardProgressReward=True)
    control_plan = campaign.read(root / campaign.CONTROL_BASE / "plan.json")
    campaign.require(control_plan["trainingSeed"] == campaign.TRAINING_SEED and control_plan["initialStep"] == campaign.START
                     and control_plan["targetGlobalStep"] == campaign.TARGET and control_plan["parentCheckpointHash"] == campaign.PARENT_CHECKPOINT_HASH
                     and control_plan["parentModelHash"] == campaign.PARENT_MODEL_HASH, "Control did not start at the same checkpoint/budget/RNG seed")
    matched = copy.deepcopy(control_plan["trainingManifest"])
    matched.update(evidenceRoot=str(base / "training"), basePort=campaign.BASE_PORT,
                   sourceIdentity=source["sourceIdentity"], buildIdentity=build["buildIdentity"], movementForwardProgressReward=True)
    campaign.require(matched == training_manifest, "Reward arm differs from axes-control physical/distribution recipe")
    campaign.require(yaml.safe_load(text) == yaml.safe_load((root / control_plan["configPath"]).read_text()), "PPO/config differs from the axes control")
    runner = Path(campaign.__file__).resolve()
    plan = {
        "status": "frozen_movement_progress_after_axes_review", "version": "execution-movement-progress-01",
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hypothesis": "On the unchanged6.25-25cm axes mixture, capped actual post-contact forward progress during focus episodes may bridge accepted contact to cross-net legal returns while preserving familiar/prior skills and placement. Larger50-100cm shifts remain transfer probes.",
        "parentRun": campaign.PARENT_RUN, "runId": campaign.RUN, "sourceIdentity": source["sourceIdentity"],
        "parentSourceIdentity": campaign.PARENT_SOURCE,
        "controlCampaign": campaign.CONTROL_BASE, "controlSourceIdentity": campaign.CONTROL_SOURCE,
        "buildIdentity": build["buildIdentity"], "parentCheckpointHash": campaign.PARENT_CHECKPOINT_HASH,
        "parentModelHash": campaign.PARENT_MODEL_HASH, "initialStep": campaign.START, "targetGlobalStep": campaign.TARGET,
        "trainingSeed": campaign.TRAINING_SEED, "parentTrainingSeed": campaign.PARENT_SEED,
        "basePort": campaign.BASE_PORT, "workerCount": campaign.WORKERS, "arenasPerWorker": campaign.ARENAS,
        "configPath": campaign.CONFIG, "configHash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "sourceRecordPath": f"{campaign.SOURCE_BASE}/source-records.json",
        "buildRecordPath": f"{campaign.SOURCE_BASE}/build-verification.json",
        "testsProof": {"path": str(tests_path.resolve()), "sha256": source["testsHash"], "result": "Passed"},
        "parentManifest": parent_manifest, "trainingManifest": training_manifest,
        "curriculumChange": {"groupFractions": {"familiar": .25, "prior": .25, "focus": .5}, "interleaved": True,
                             "focusPattern": "axes", "maximumFocusRange": .0625, "focusNominalShiftCm": [6.25,12.5,18.75,25],
                             "priorRange": .1, "changedFromAxesControl": False, "bodyPpoObservationGoalChanges": False},
        "rewardChange": {"flag": campaign.REWARD_FLAG, "enabled": True, "focusOnly": True, "maximumPerEpisode": .25,
                         "scope": "NewMovementChallenge(index) only; solo positive-range rally movement focus. Familiar, prior-court, serves and required-bounce receives retain their previous reward.",
                         "mechanism": "Existing PlayerReturnProgressV3 accumulates actual post-contact canonical forward progress, capped0.25, stopping on terminal/fault/first legal landing. No retroactive removal of already earned bonus on a later fault.",
                         "placementRewardUnchanged": "smooth-distance-2m", "evaluationFlag": False,
                         "episodeFields": ["movementForwardProgressRewardEnabled", "movementForwardProgressReward", "movementForwardProgressRewardedSteps"]},
        "runnerHash": campaign.sha(runner),
        "prepareScriptHash": campaign.sha(Path(__file__)), "helperPath": campaign.HELPER, "helperHash": campaign.HELPER_HASH,
        "resume": {"framework": "Pinned ML-Agents --resume, no init_path or initialize-from",
                   "preserved": ["actor", "critic", "normalization", "Adam optimizer", "global step"],
                   "notPreserved": ["live Unity state", "in-flight rollout buffer", "process RNG progression"],
                   "trainingResetReuse": {"firstSeed": campaign.FIRST_SEED, "seedsPerWorker": campaign.SEEDS_PER_WORKER, "workers": campaign.WORKERS},
                   "checkpointPaths": "Byte-copy complete parent results into isolated run; remap every checkpoint-manager path before loading or retention"},
        "evaluation": {"baselineInputs": inputs, "batteries": batteries, "evaluateMidpoint": False,
                       "baselineModelIdentities": baseline_identities,
                       "baselineSourceIdentities": {model: identity["sourceIdentity"] for model, identity in baseline_identities.items()},
                       "candidateSourceIdentity": source["sourceIdentity"],
                       "baselineReuse": "Common-parent/initializer records retain original5f identities; completed axes-control records retain557040f9 identity. New reward is disabled for frozen evaluation. Require unchanged physical recipes and exact first124/full136 observation pairing before accepting comparisons; do not relabel old records as newly evaluated.",
                       "midpointSelection": {"targetStep": campaign.MID, "maximumDistance": campaign.BUFFER, "tieBreak": "lower step", "rule": "Nearest retained numbered checkpoint by step before evaluating performance"},
                       "midpointUse": "Optional descriptive trajectory only; never substitutes for mandatory final endpoint",
                       "finalSelection": {"minimumStep": campaign.TARGET, "exclusiveMaximumStep": campaign.TARGET+campaign.BUFFER,
                                          "model": "ExecutionV1MovementProgressFinal01", "rule": "Final exported checkpoint, never best-of-checkpoints"},
                       "comparisons": ["same-cohort initializer", "1048609-experience common parent", "completed no-progress axes-control fixed final endpoint"],
                       "report": ["Legal/all and target/all by drill, side, direction, distance and player with denominators",
                                  "Paired goal assignment gain and actual landing response; retain illegal and no-contact attempts",
                                  "Paired intervals and duplicate-observation clusters; report sparse wide cells",
                                  "Root path and accepted-contact displacement; distinguish no-contact cases"],
                       "acceptance": "Apply the existing narrow screen descriptively against all three comparison models: initializer, common parent and completed axes control. Wide changes are paired measurements without a new posthoc pass threshold. No automatic promotion or mastery claim."},
        "limits": {"wallSeconds": campaign.WALL_TIMEOUT, "restartAttempts": 0, "automaticExtension": False,
                   "automaticPromotion": False, "architectureChanges": False, "rewardChanges": True, "scriptedActions": False},
        "stopCondition": "Stop after the fixed final endpoint and before/after assessments. If movement or retention remains weak, review that coverage gap rather than automatically adding more unchanged training.",
        "limitations": ["One matched-seed reward arm compared with an already completed control; not replicated causal proof or independent training evidence.",
                        "Both branches resume common parent1048609; the regressed axes endpoint is a comparison only and never the initializer.",
                        "Both evaluation batteries reuse development situations and final seeds remain reserved.",
                        "Wide coverage remains sparse in some direction/distance/player cells.", "Training process RNG restarts at19017, matching control setup; bitwise trajectory equivalence is not claimed.",
                        "Recorded episode totals verify reward scope/cap; they do not reconstruct every post-contact tick. Source tests verify reward mechanics."],
        "finalSeedsConsumed": False, "masteryAccepted": False,
    }
    # All dependencies and before-assessments must exist before either mutation.
    # Base already contains the freshly verified source/build evidence.
    with config.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    campaign.require(campaign.sha(config) == plan["configHash"], "Written YAML hash differs")
    campaign.write(base / "plan.json", plan)
    print(json.dumps({"plan": str(base / "plan.json"), "configHash": campaign.sha(config),
                      "targetGlobalStep": campaign.TARGET, "trainingLaunched": False}))


if __name__ == "__main__":
    main()
