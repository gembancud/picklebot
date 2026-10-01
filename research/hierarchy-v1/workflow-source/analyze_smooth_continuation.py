"""Audit the frozen smooth-continued-01 development experiment; never promote.

Run with the pinned NumPy-capable Python and --root <picklebot repository>.
Imports only statistical primitives from the preserved smooth-distance analyzer;
its main(), baseline assumptions, and model globals are never reused. All input,
helper, plan, selection, and script digests are recorded. The only analysis output
is an exclusively created <campaign>/audit/analysis.json.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import numpy as np

sys.dont_write_bytecode = True
INITIAL = "ExecutionV1Initial"
PARENT = "ExecutionV1SmoothDistance01"
MID = "ExecutionV1SmoothContinuedMid01"
FINAL = "ExecutionV1SmoothContinuedFinal01"
MODELS = (INITIAL, PARENT, MID, FINAL)
CANDIDATES = (MID, FINAL)
REFERENCES = (INITIAL, PARENT)
CONDITIONS = ("A", "B", "random")
FILES = ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json")
SOURCE_INITIAL = "48190f51a4fd7bedeca31377ea909afdba476722483d250a9610585a50e95f4c"
SOURCE_CURRENT = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
CONTRACT = "execution-v1-136obs-16continuous-release"
FIRST_SEED, COUNT = 1108985, 256
SEEDS = list(range(FIRST_SEED, FIRST_SEED + COUNT))
HELPER = "research/hierarchy-v1/smooth-distance-01/analyze_smooth_distance.py"
HELPER_SHA256 = "69b627d8821a25fa249ff01ea4e070c47d26eb0221103981c62e4f06be4cf7e6"
CAMPAIGN = "artifacts/hierarchy-v1/smooth-continued-01"
BASES = {INITIAL: "artifacts/hierarchy-v1/two-regions-01", PARENT: "artifacts/hierarchy-v1/smooth-distance-01"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def inside(root, relative):
    candidate = root / relative
    require(not Path(relative).is_absolute() and candidate.resolve().is_relative_to(root),
            f"Path escapes repository: {relative}")
    return candidate


def load_helper(root):
    path = inside(root, HELPER)
    require(path.is_file(), f"Missing explicit analysis dependency: {path}")
    require(sha(path) == HELPER_SHA256, "Preserved validated statistical helper changed")
    spec = importlib.util.spec_from_file_location("preserved_smooth_distance_statistics", path)
    require(spec is not None and spec.loader is not None, "Cannot import preserved helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.FIRST_SEED == FIRST_SEED and module.COUNT == COUNT and module.SEEDS == SEEDS,
            "Helper reset contract changed")
    require(module.BOOTSTRAP_SEED == 20260912 and module.BOOTSTRAP_DRAWS == 10000,
            "Helper bootstrap protocol changed")
    return module


def verify_inputs(root, campaign, plan, inputs):
    # CPU-only reads of trusted, local, project-produced checkpoints. Torch is
    # used only for metadata/state parity, never to run or update a policy.
    import torch

    def equal_state(left, right):
        if isinstance(left, torch.Tensor):
            return isinstance(right, torch.Tensor) and left.dtype == right.dtype and torch.equal(left, right)
        if isinstance(left, dict):
            return isinstance(right, dict) and left.keys() == right.keys() and all(equal_state(left[k], right[k]) for k in left)
        if isinstance(left, (list, tuple)):
            return type(left) is type(right) and len(left) == len(right) and all(equal_state(a, b) for a, b in zip(left, right))
        return type(left) is type(right) and left == right

    def checkpoint_state(path, expected_step):
        state = torch.load(path, map_location="cpu", weights_only=False)
        steps = state["global_step"]
        require(len(steps) == 1, f"{path}: unexpected global-step structure")
        step = next(iter(steps.values())).item()
        require(step == expected_step, f"{path}: stored global step does not match selected step")
        return state

    frozen = plan["evaluation"]["baselineInputs"]
    required = {f"{BASES[model]}/evaluation/{model}/{condition}/{name}"
                for model in REFERENCES for condition in CONDITIONS for name in FILES}
    require(isinstance(frozen, dict) and required.issubset(frozen), "Frozen baseline manifest is incomplete")
    for relative, expected in frozen.items():
        path = inside(root, relative)
        require(is_digest(expected) and path.is_file() and sha(path) == expected,
                f"Frozen baseline hash mismatch: {relative}")
        inputs[relative] = expected
    selection_path = campaign / "selected-models.json"
    selected = read(selection_path)
    inputs[selection_path.relative_to(root).as_posix()] = sha(selection_path)
    run = inside(root, f"artifacts/mlagents/{plan['runId']}")
    checkpoint_dir = run / "PicklebotExecutionV1"
    available = {}
    for checkpoint in checkpoint_dir.glob("PicklebotExecutionV1-*.pt"):
        match = re.fullmatch(r"PicklebotExecutionV1-(\d+)\.pt", checkpoint.name)
        if match:
            available[int(match.group(1))] = checkpoint
    require(available, "No numbered continuation checkpoints remain for selection audit")
    eligible = [step for step in available if abs(step - 524288) <= 8192]
    require(eligible, "No retained midpoint within the predeclared 8192-step window")
    midpoint = min(eligible, key=lambda step: (abs(step - 524288), step))
    identities = {}
    selected_states = {}
    for label, model in (("mid", MID), ("final", FINAL)):
        record = selected[label]
        step = record["step"]
        require(record["model"] == model and type(step) is int, f"Invalid {label} identity")
        require(step == midpoint if label == "mid" else 1048576 <= step < 1056768,
                f"{label} violates fixed checkpoint selection")
        require(step in available, f"Selected {label} checkpoint is missing")
        require(record.get("sourceIdentity", SOURCE_CURRENT) == SOURCE_CURRENT, f"Selected {label} source mismatch")
        if "checkpoint" in record:
            require(inside(root, record["checkpoint"]).resolve() == available[step].resolve(), f"Selected {label} checkpoint path mismatch")
        files = {"checkpointHash": available[step], "modelHash": available[step].with_suffix(".onnx")}
        for key, path in files.items():
            require(is_digest(record[key]) and path.is_file() and sha(path) == record[key],
                    f"Selected {label} {key} does not match checkpoint bytes")
            inputs[path.relative_to(root).as_posix()] = record[key]
        selected_states[label] = checkpoint_state(available[step], step)
        asset = root / f"Assets/Picklebot/PlayerLearning/Models/{model}.onnx"
        require(asset.is_file() and sha(asset) == record["modelHash"], f"{model}: evaluation model asset mismatch")
        inputs[asset.relative_to(root).as_posix()] = record["modelHash"]
        identities[model] = {**record, "sourceIdentity": SOURCE_CURRENT}
    # The final choice must be the framework's final export, not a convenient
    # nearby regular checkpoint satisfying only the numeric window.
    require(sha(run / "PicklebotExecutionV1.onnx") == selected["final"]["modelHash"], "Final exported ONNX mismatch")
    mutable = checkpoint_dir / "checkpoint.pt"
    require(equal_state(selected_states["final"], checkpoint_state(mutable, selected["final"]["step"])),
            "Final mutable checkpoint and selected numbered checkpoint state mismatch")
    # torch.save's archive name can change file bytes for identical full state.
    inputs[mutable.relative_to(root).as_posix()] = sha(mutable)
    inputs[(run / "PicklebotExecutionV1.onnx").relative_to(root).as_posix()] = selected["final"]["modelHash"]
    verification_path = campaign / "training/verification.json"
    verification = read(verification_path)
    require(verification["status"] == "completed_continuation_check" and verification["resumeStateExact"] is True
            and verification["parentRunUnchanged"] is True, "Continuation verification did not pass")
    require(verification["sourceIdentity"] == SOURCE_CURRENT and verification["initialStep"] == plan["initialStep"]
            and verification["experiences"] == selected["final"]["step"], "Continuation identity/step verification mismatch")
    require(verification["checkpointHash"] == sha(mutable) and verification["modelHash"] == selected["final"]["modelHash"],
            "Selected final output is not the verified continuation output")
    inputs[verification_path.relative_to(root).as_posix()] = sha(verification_path)
    for key, path in (("parentCheckpointHash", root / f"artifacts/mlagents/{plan['parentRun']}/PicklebotExecutionV1/checkpoint.pt"),
                      ("parentModelHash", root / f"artifacts/mlagents/{plan['parentRun']}/PicklebotExecutionV1.onnx")):
        require(is_digest(plan[key]) and path.is_file() and sha(path) == plan[key], f"Immediate parent changed: {key}")
        inputs[path.relative_to(root).as_posix()] = plan[key]
    identities[PARENT] = {"model": PARENT, "step": plan["initialStep"], "modelHash": plan["parentModelHash"],
                          "checkpointHash": plan["parentCheckpointHash"], "sourceIdentity": SOURCE_CURRENT}
    identities[INITIAL] = {"model": INITIAL, "sourceIdentity": SOURCE_INITIAL,
                           "identityBasis": "Original frozen evaluation files, not a replay or a current asset inference"}
    parity = {"device": "cpu", "torchVersion": torch.__version__, "numberedCheckpointStepsMatchStoredState": True,
              "finalNumberedAndMutableFullStateEqual": True, "fileHashesNeedNotMatchForEqualTorchState": True}
    return frozen, identities, sorted(available), parity


def validate_run(h, folder, model, condition, source, inputs, root, frozen):
    paths = [folder / name for name in FILES]
    for path in paths:
        relative = path.relative_to(root).as_posix()
        require(path.is_file(), f"Missing evaluation input: {path}")
        digest = sha(path)
        if model in REFERENCES:
            require(digest == frozen[relative], f"Baseline changed after validation: {path}")
        inputs[relative] = digest
    episodes, goals = h.read_rows(paths[0]), h.read_rows(paths[1])
    raw_first = read(paths[2])
    first = {int(k): value for k, value in raw_first.items()}
    require(len(raw_first) == COUNT and len(first) == COUNT and sorted(first) == SEEDS, f"{folder}: first-decision seeds mismatch")
    report = read(paths[3])
    require(report["status"] == "seed_budget_complete" and not report.get("failure"), f"{folder}: failed or unfinished")
    require(report["completedEpisodes"] == COUNT and report["seedCount"] == COUNT and report["firstSeed"] == FIRST_SEED,
            f"{folder}: incomplete reset budget")
    require(report["nextSeedIndex"] == COUNT and report["split"] == "development", f"{folder}: reset/split mismatch")
    require(report["sourceIdentity"] == source and report["contract"] == CONTRACT, f"{folder}: source/contract mismatch")
    require(report["trainerConnected"] is False, f"{folder}: trainer attached during evaluation")
    require(report["movementRecoveryMix"] is True and report["interleavedRecovery"] is True and report["fixedServeSides"] == "both",
            f"{folder}: recovery curriculum mismatch")
    for seed in SEEDS:
        ep, row, decision = episodes[seed], goals[seed], first[seed]
        label = f"{model}/{condition}/{seed}"
        # Only the frozen initializer predates the rewardMode field.
        require(row.get("rewardMode", "linear-radius" if model == INITIAL else None) == "linear-radius", f"{label}: wrong evaluation reward mode")
        require(row["assigned"] is True and row["contract"] == CONTRACT, f"{label}: missing private goal")
        require(ep["player"] == row["player"] == decision["player"] and ep["player"] in range(4) and decision["seed"] == seed,
                f"{label}: private player/seed mismatch")
        obs, action = np.asarray(decision["observation"], dtype=float), np.asarray(decision["physical"], dtype=float)
        require(obs.shape == (136,) and action.shape == (18,) and np.isfinite(obs).all() and np.isfinite(action).all(), f"{label}: malformed first decision")
        require(np.array_equal(obs[124:132], [1, 0, 0, 0, 0, 0, 0, 0]), f"{label}: unintended intent/movement goal")
        require(row["outcome"] == ep["outcome"], f"{label}: outcome mismatch")
        legal = ep["outcome"] in ("legal_return", "legal_serve")
        require(row["legalLanding"] is legal and row["hasLanding"] is legal, f"{label}: legality/landing availability mismatch")
        radius = 1.5 if condition == "random" else 1.0
        require(abs(row["radius"] - radius) < 1e-6, f"{label}: wrong success radius")
        require(np.isfinite([row[k] for k in ("targetX", "targetZ", "radius", "distance", "bonus", "landingX", "landingZ")]).all(), f"{label}: nonfinite landing/goal")
        require(np.allclose(obs[132:136], [1, row["targetX"] / 3.048, row["targetZ"] / 6.7056, radius / 3], atol=2e-6, rtol=0), f"{label}: goal encoding mismatch")
        serve = ep["task"] == "stationary-serve"
        service_sign = 1 if ep["serveFromLeft"] else -1
        if condition == "random":
            require(row["targetLayout"] == "random", f"{label}: wrong random layout")
            require(abs(row["targetX"]) <= 2.3 + 2e-6 and 1 - 2e-6 <= row["targetZ"] <= 5.8 + 2e-6, f"{label}: random target bounds")
            if serve:
                require(.5 - 2e-6 <= service_sign * row["targetX"] <= 2.3 + 2e-6 and row["targetZ"] >= 2.8 - 2e-6, f"{label}: random serve service-box sign/bounds")
        else:
            require(row["targetLayout"] == "two-regions", f"{label}: wrong A/B layout")
            expected = [service_sign * 1.4, 3.3 if condition == "A" else 5.4] if serve else [-1.2 if condition == "A" else 1.2, 3.8]
            require(np.allclose(h.target(row), expected, atol=2e-6, rtol=0), f"{label}: wrong canonical region/serve-side sign")
        if legal:
            require(row["distance"] >= 0 and abs(np.linalg.norm(h.landing(row) - h.target(row)) - row["distance"]) < 2e-5, f"{label}: distance mismatch")
        else:
            require(row["distance"] == -1 and row["landingX"] == 0 and row["landingZ"] == 0, f"{label}: invalid-outcome landing sentinel mismatch")
        require(type(row["targetHit"]) is bool and row["targetHit"] == h.hit(row, row), f"{label}: target-hit boundary/evidence mismatch")
        expected_bonus = .25 * max(0, 1 - row["distance"] / radius) if legal else 0
        require(0 <= row["bonus"] <= .25 and abs(row["bonus"] - expected_bonus) < 2e-5, f"{label}: bonus mismatch")
    return episodes, goals, first, report


def groups(h, episodes):
    result = {"all": SEEDS}
    drills = sorted({row["task"] for row in episodes.values()})
    for drill in drills:
        result[f"drill/{drill}"] = [s for s in SEEDS if episodes[s]["task"] == drill]
        for side in ("left", "right"):
            result[f"drill/{drill}/serve-side/{side}"] = [s for s in SEEDS if episodes[s]["task"] == drill and h.group_key(episodes[s])[1] == side]
    for player in range(4):
        result[f"player/{player}"] = [s for s in SEEDS if episodes[s]["player"] == player]
    for movement in ("actual-movement", "central-or-familiar"):
        result[f"movement/{movement}"] = [s for s in SEEDS if h.group_key(episodes[s])[2] == movement]
    for region in sorted({int(row["movementRegion"]) for row in episodes.values()}):
        result[f"movement-region/{region}"] = [s for s in SEEDS if episodes[s]["movementRegion"] == region]
    for key in sorted({h.group_key(row) for row in episodes.values()}):
        result["cell/" + "/".join(map(str, key))] = [s for s in SEEDS if h.group_key(episodes[s]) == key]
    return {key: seeds for key, seeds in result.items() if seeds}, drills


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    args = parser.parse_args()
    root = args.root.resolve()
    require(root.is_dir(), "Repository root does not exist")
    campaign = root / CAMPAIGN
    output = campaign / "audit/analysis.json"
    require(not output.exists(), f"Refusing to overwrite {output}")
    h = load_helper(root)
    plan = read(campaign / "plan.json")
    require(plan["runId"] == "execution-smooth-continued-01" and plan["parentRun"] == "execution-smooth-distance-01", "Unexpected continuation lineage")
    require(plan["initialStep"] == 262179 and plan["targetGlobalStep"] == 1048576, "Unexpected training budget")
    require(plan["sourceIdentity"] == SOURCE_CURRENT, "Unexpected continuation source")
    require(plan["finalSeedsConsumed"] is False and plan["masteryAccepted"] is False and plan["limits"]["automaticPromotion"] is False, "Unsafe acceptance/final-seed declarations")
    evaluation = plan["evaluation"]
    require(evaluation["firstSeed"] == FIRST_SEED and evaluation["baseResets"] == COUNT and tuple(evaluation["conditions"]) == CONDITIONS,
            "Unexpected development evaluation contract")
    require(evaluation["rewardMode"] == "linear-radius" and evaluation["split"] == "reused development anchor", "Unexpected evaluation recipe")
    inputs = {f"{CAMPAIGN}/plan.json": sha(campaign / "plan.json"), HELPER: sha(root / HELPER)}
    frozen, identities, available_steps, checkpoint_parity = verify_inputs(root, campaign, plan, inputs)
    runs = {}
    for model in MODELS:
        model_base = root / BASES[model] if model in REFERENCES else campaign
        for condition in CONDITIONS:
            folder = model_base / "evaluation" / model / condition
            if model in CANDIDATES:
                identity_path = folder / "model-identity.json"
                actual = read(identity_path)
                for key in ("model", "modelHash", "checkpointHash", "step", "sourceIdentity"):
                    require(actual[key] == identities[model][key], f"{model}/{condition}: evaluation model-identity mismatch for {key}")
                inputs[identity_path.relative_to(root).as_posix()] = sha(identity_path)
            runs[model, condition] = validate_run(h, folder, model, condition,
                                                 identities[model]["sourceIdentity"], inputs, root, frozen)
    negative = {"matchedBaseResets": COUNT, "identicalInitialPhysicalActions": 0, "identicalPhysicalEpisodes": 0, "identicalLegalLandings": 0}
    for seed in SEEDS:
        ref_ep, _, ref_first, _ = runs[INITIAL, "A"]
        for model in MODELS:
            for condition in CONDITIONS:
                ep, goals, first, _ = runs[model, condition]
                require(np.array_equal(first[seed]["observation"][:124], ref_first[seed]["observation"][:124]), f"{model}/{condition}/{seed}: physical reset observation changed")
                require(h.group_key(ep[seed]) == h.group_key(ref_ep[seed]), f"{model}/{condition}/{seed}: reset descriptor changed")
                baseline_goal = runs[INITIAL, condition][1][seed]
                require(np.array_equal(h.target(goals[seed]), h.target(baseline_goal)) and goals[seed]["radius"] == baseline_goal["radius"], f"{model}/{condition}/{seed}: instruction changed across models")
        a, b = runs[INITIAL, "A"], runs[INITIAL, "B"]
        require(np.array_equal(a[2][seed]["physical"], b[2][seed]["physical"]), f"Initializer negative-control action mismatch: {seed}")
        negative["identicalInitialPhysicalActions"] += 1
        require({k: v for k, v in a[0][seed].items() if k != "reward"} == {k: v for k, v in b[0][seed].items() if k != "reward"}, f"Initializer negative-control episode mismatch: {seed}")
        negative["identicalPhysicalEpisodes"] += 1
        require(a[1][seed]["legalLanding"] == b[1][seed]["legalLanding"], f"Initializer negative-control legal mismatch: {seed}")
        if a[1][seed]["legalLanding"]:
            require(np.array_equal(h.landing(a[1][seed]), h.landing(b[1][seed])), f"Initializer negative-control landing mismatch: {seed}")
            negative["identicalLegalLandings"] += 1
    grouping, drills = groups(h, runs[INITIAL, "A"][0])
    summaries, causal, comparisons = {}, {}, {}
    for group, seeds in grouping.items():
        summaries[group], causal[group], comparisons[group] = {}, {}, {}
        gains = {}
        for model in MODELS:
            summaries[group][model] = {condition: h.metrics([runs[model, condition][1][s] for s in seeds]) for condition in CONDITIONS}
            causal[group][model], gains[model] = h.causal([runs[model, "A"][1][s] for s in seeds], [runs[model, "B"][1][s] for s in seeds])
        require(np.all(gains[INITIAL] == 0), f"Initializer assignment gain fails cancellation: {group}")
        for candidate in CANDIDATES:
            comparisons[group][candidate] = {}
            for reference in REFERENCES:
                comparisons[group][candidate][reference] = {
                    "assignmentGainChange": h.ci(gains[candidate] - gains[reference]),
                    "conditions": {condition: h.paired_changes_for([runs[reference, condition][1][s] for s in seeds], [runs[candidate, condition][1][s] for s in seeds]) for condition in CONDITIONS}}
    legal_checks = [{"reference": ref, "drill": drill, "condition": condition,
                     **comparisons[f"drill/{drill}"][FINAL][ref]["conditions"][condition]["legalRateChange"]}
                    for ref in REFERENCES for drill in drills for condition in CONDITIONS]
    tests = {
        "finalAssignmentGainCiLowerAboveZero": causal["all"][FINAL]["assignmentGain"]["ci95"][0] > 0,
        "bothFinalRegionTargetRatesExceedInitializer": all(comparisons["all"][FINAL][INITIAL]["conditions"][c]["targetRateChange"]["mean"] > 0 for c in ("A", "B")),
        "noFinalDrillLegalDropGreaterThanFivePercentagePointsVsEitherReference": all(check["mean"] >= -.05 - 1e-12 for check in legal_checks),
    }
    result = {
        "status": "complete_development_screen", "models": list(MODELS), "selectedModels": identities,
        "inputSha256": inputs, "analysisScriptSha256": sha(Path(__file__)),
        "analysisDependency": {"path": HELPER, "sha256": inputs[HELPER], "functions": ["read_rows", "ci", "landing", "target", "hit", "group_key", "metrics", "causal", "paired_changes_for"]},
        "provenance": {"repositoryRoot": str(root), "baselineInputSha256": frozen, "baselineWasReevaluated": False,
                       "checkpointStateParity": checkpoint_parity,
                       "newEvaluationModelBinding": "All six completed evaluations carry model-identity sidecars with pre/post asset hash checks matching the selected checkpoint/export pair",
                       "retainedCheckpointSteps": available_steps, "selectionRules": {k: evaluation[k] for k in ("midpointSelection", "finalSelection", "midpointUse")},
                       "evaluationRewardMode": "linear-radius", "trainingRewardMode": "smooth-distance-2m",
                       "baselineIdentityBasis": "Frozen files at original model/source directories; preserved baseline results were not replayed under the continuation build"},
        "baseResets": COUNT, "attemptsPerModel": COUNT * len(CONDITIONS), "negativeControl": negative,
        "uniqueInitialPhysicalObservationCount": len({tuple(runs[INITIAL, "A"][2][s]["observation"][:124]) for s in SEEDS}),
        "bootstrap": {"method": "paired base-reset percentile bootstrap", "seed": h.BOOTSTRAP_SEED, "replicates": h.BOOTSTRAP_DRAWS,
                      "coverage": "pointwise 95%, not simultaneous across models/groups; pairing retained across instructions and comparisons"},
        "groupKey": ["task", "serviceSide", "movementCategory", "movementPattern", "movementRange", "movementRegion", "player"],
        "movementCategoryMeaning": "actual-movement denotes a positive-range movement feed, not proof the root moved or positioning was mastered",
        "summaries": summaries, "causal": causal, "pairedCandidateMinusReference": comparisons,
        "screen": {"rules": evaluation["screen"], "model": FINAL, "tests": tests, "promising": all(tests.values()),
                   "legalRetentionChecks": legal_checks, "retentionInterpretation": "Point-estimate drop no worse than5pp for every drill/condition versus BOTH references; CIs reported separately, not a proof of equivalence",
                   "midpointUse": "Descriptive trajectory only; no midpoint pass/promotion and no outcome-based checkpoint selection"},
        "promoted": False, "masteryAccepted": False, "finalSeedsConsumed": False,
        "limitations": [
            "Repeated development anchor and one continuing training lineage; not an independent test of generalization or a replicated recipe comparison.",
            "Fresh processes reuse training reset seeds and do not restore live simulation state, in-flight rollouts, or process RNG progression.",
            "The midpoint is descriptive; final checkpoint selection remains fixed even when the midpoint performs better.",
            "Both-legal landing shifts are conditional and must be read with their contributing-pair count and unconditional placement success.",
            "Assignment gain tests target-following on paired physical resets; raw A/B target-rate improvement alone can reflect unconditional shot drift.",
            "First-decision identity validates recorded reset equivalence, not every hidden simulator state or every later stroke state.",
            "Sparse subgroup percentile intervals can be degenerate; repeated geometries and small all-success/failure cells do not establish certainty.",
            "This small-shift movement mixture does not cover arbitrary wide/deep/shallow positioning or prove full drill mastery.",
            "Historical evaluation model binding relies on the frozen input manifest and original provenance; those baselines were not rerun.",
        ],
    }
    # Check that frozen inputs/selection did not change while analysis ran.
    for relative, expected in inputs.items():
        require(sha(inside(root, relative)) == expected, f"Input changed during analysis: {relative}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    counts = {model: {condition: {key: summaries["all"][model][condition][key] for key in ("attempts", "legal", "targets", "nonzeroBonus")} for condition in CONDITIONS} for model in MODELS}
    print(json.dumps({"analysis": str(output), "counts": counts, "finalAssignmentGain": causal["all"][FINAL]["assignmentGain"],
                      "screenTests": tests, "promising": all(tests.values()), "promoted": False, "masteryAccepted": False}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
