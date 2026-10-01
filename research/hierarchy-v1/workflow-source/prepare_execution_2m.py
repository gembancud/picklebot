"""DRAFT: freeze one unchanged-recipe continuation after the wide baseline review.

No work on import. Requires --freeze-after-wide-review when the campaign owner has
reviewed the completed wide assessment and chosen this experiment. Does not launch
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

import yaml

import run_execution_2m as campaign


def baseline_inputs(root):
    """Require completed before-assessments; freeze their raw evidence and plans."""
    inputs, batteries = {}, {}
    models = ["ExecutionV1Initial", "ExecutionV1SmoothContinuedFinal01"]
    for name, directory, first, count, conditions in (
        ("narrow", "fresh-placement-01", 1109593, 256, ["A", "B", "random"]),
        ("wide", "wide-movement-fixture-01", 1109849, 512, ["A", "B"]),
    ):
        folder = root / "artifacts/hierarchy-v1" / directory
        plan_path, analysis_path = folder / "plan.json", folder / "audit/analysis.json"
        plan = campaign.read(plan_path)
        campaign.require(plan["sourceIdentity"] == campaign.SOURCE and plan["firstSeed"] == first
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
            for condition in conditions:
                evaluation = folder / "evaluation" / model / condition
                report = campaign.read(evaluation / "report.json")
                identity = campaign.read(evaluation / "model-identity.json")
                expected = plan["modelIdentities"][model]
                campaign.require(all(identity[k] == expected[k] for k in ("model", "modelHash", "checkpointHash", "step", "sourceIdentity")),
                                 f"{name}/{model}/{condition}: model identity mismatch")
                campaign.require(report["status"] == "seed_budget_complete" and not report["failure"]
                                 and not report["trainerConnected"] and report["sourceIdentity"] == campaign.SOURCE
                                 and report["contract"] == campaign.CONTRACT and report["split"] == "development"
                                 and report["firstSeed"] == first and report["seedCount"] == count
                                 and report["completedEpisodes"] == count, f"{name}/{model}/{condition}: incomplete baseline")
                for filename in ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "model-identity.json"):
                    path = evaluation / filename
                    campaign.require(path.is_file(), f"Missing baseline evidence: {path}")
                    paths.append(path)
        inputs.update({path.relative_to(root).as_posix(): campaign.sha(path) for path in paths})
        batteries[name] = {"firstSeed": first, "baseResets": count, "conditions": conditions,
                           "physicalRecipe": plan["physicalRecipe"], "rewardMode": "linear-radius",
                           "baselineCampaign": folder.relative_to(root).as_posix(),
                           "baselineModels": models, "finalModel": "ExecutionV1Smooth2mFinal01",
                           "interpretation": "Repeated development anchor; not unused test cases or mastery evidence"}
        if name == "narrow":
            batteries[name]["existingScreen"] = plan["screening"]
        else:
            batteries[name]["interpretation"] += "; wide physical recipe is assessed but is not added to this training distribution"
    return inputs, batteries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--freeze-after-wide-review", action="store_true", help="Campaign owner chose unchanged continuation after reviewing complete wide baseline")
    parser.add_argument("--evaluate-midpoint", action="store_true", help="Predeclare the fixed midpoint as a descriptive trajectory evaluation")
    args = parser.parse_args()
    campaign.require(args.freeze_after_wide_review, "Draft only: review the completed wide baseline before freezing this choice")
    root = args.root.resolve()
    campaign.require(Path(sys.executable).resolve() == (root / "tools/mlagents-training/.pixi/envs/default/python.exe").resolve(),
                     "Use the project's pinned Python")
    base, config = root / campaign.BASE, root / campaign.CONFIG
    campaign.require(not base.exists() and not config.exists() and not (root / "artifacts/mlagents" / campaign.RUN).exists(),
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
    campaign.require(source["sourceIdentity"] == build["sourceIdentity"] == campaign.SOURCE, "Source/build mismatch")
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
    inputs, batteries = baseline_inputs(root)
    parent_inputs = [checkpoint, model, parent / "verification.json", parent / "launch.json", parent / "manifest.json", old_config,
                     root / campaign.SOURCE_BASE / "source-records.json", root / campaign.SOURCE_BASE / "build-verification.json",
                     root / campaign.HELPER]
    inputs.update({path.relative_to(root).as_posix(): campaign.sha(path) for path in parent_inputs})
    runner = Path(campaign.__file__).resolve()
    plan = {
        "status": "frozen_after_wide_review", "version": "execution-smooth-2m-01",
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hypothesis": "One further fixed training budget tests whether the observed partial target response improves while familiar and wider returns are retained. This unchanged recipe does not teach new wide reset coverage directly.",
        "parentRun": campaign.PARENT_RUN, "runId": campaign.RUN, "sourceIdentity": campaign.SOURCE,
        "buildIdentity": build["buildIdentity"], "parentCheckpointHash": campaign.PARENT_CHECKPOINT_HASH,
        "parentModelHash": campaign.PARENT_MODEL_HASH, "initialStep": campaign.START, "targetGlobalStep": campaign.TARGET,
        "trainingSeed": campaign.TRAINING_SEED, "parentTrainingSeed": campaign.PARENT_SEED,
        "basePort": campaign.BASE_PORT, "workerCount": campaign.WORKERS, "arenasPerWorker": campaign.ARENAS,
        "configPath": campaign.CONFIG, "configHash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "sourceRecordPath": f"{campaign.SOURCE_BASE}/source-records.json",
        "buildRecordPath": f"{campaign.SOURCE_BASE}/build-verification.json",
        "parentManifest": campaign.read(parent / "manifest.json"), "runnerHash": campaign.sha(runner),
        "prepareScriptHash": campaign.sha(Path(__file__)), "helperPath": campaign.HELPER, "helperHash": campaign.HELPER_HASH,
        "resume": {"framework": "Pinned ML-Agents --resume, no init_path or initialize-from",
                   "preserved": ["actor", "critic", "normalization", "Adam optimizer", "global step"],
                   "notPreserved": ["live Unity state", "in-flight rollout buffer", "process RNG progression"],
                   "trainingResetReuse": {"firstSeed": campaign.FIRST_SEED, "seedsPerWorker": campaign.SEEDS_PER_WORKER, "workers": campaign.WORKERS},
                   "checkpointPaths": "Byte-copy complete parent results into isolated run; remap every checkpoint-manager path before loading or retention"},
        "evaluation": {"baselineInputs": inputs, "batteries": batteries, "evaluateMidpoint": args.evaluate_midpoint,
                       "midpointSelection": {"targetStep": campaign.MID, "maximumDistance": campaign.BUFFER, "tieBreak": "lower step", "rule": "Nearest retained numbered checkpoint by step before evaluating performance"},
                       "midpointUse": "Optional descriptive trajectory only; never substitutes for mandatory final endpoint",
                       "finalSelection": {"minimumStep": campaign.TARGET, "exclusiveMaximumStep": campaign.TARGET+campaign.BUFFER,
                                          "model": "ExecutionV1Smooth2mFinal01", "rule": "Final exported checkpoint, never best-of-checkpoints"},
                       "comparisons": ["same-cohort initializer", "1048609-experience immediate parent"],
                       "report": ["Legal/all and target/all by drill, side, direction, distance and player with denominators",
                                  "Paired goal assignment gain and actual landing response; retain illegal and no-contact attempts",
                                  "Paired intervals and duplicate-observation clusters; report sparse wide cells",
                                  "Root path and accepted-contact displacement; distinguish no-contact cases"],
                       "acceptance": "Apply the existing narrow screen descriptively against both baselines; wide changes are paired measurements without a new posthoc pass threshold. No automatic promotion or mastery claim."},
        "limits": {"wallSeconds": campaign.WALL_TIMEOUT, "restartAttempts": 0, "automaticExtension": False,
                   "automaticPromotion": False, "architectureChanges": False, "rewardChanges": False, "scriptedActions": False},
        "stopCondition": "Stop after the fixed final endpoint and before/after assessments. If movement or retention remains weak, review that coverage gap rather than automatically adding more unchanged training.",
        "limitations": ["One continuing lineage, not independent replication.", "Both evaluation batteries reuse development situations and final seeds remain reserved.",
                        "Wide coverage remains sparse in some direction/distance/player cells.", "Training process RNG restarts at19017; numerical trajectory continuation is not claimed."],
        "finalSeedsConsumed": False, "masteryAccepted": False,
    }
    # All dependencies and before-assessments must exist before either mutation.
    base.mkdir()
    with config.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    campaign.require(campaign.sha(config) == plan["configHash"], "Written YAML hash differs")
    campaign.write(base / "plan.json", plan)
    print(json.dumps({"plan": str(base / "plan.json"), "configHash": campaign.sha(config),
                      "targetGlobalStep": campaign.TARGET, "trainingLaunched": False}))


if __name__ == "__main__":
    main()
