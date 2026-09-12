"""Analyze the predeclared smooth-distance development screen; never promote a model.

Default inputs and exclusive output are under artifacts/hierarchy-v1/smooth-distance-01.
Reuse verified, immutable initializer and historical linear-training evaluation files.
All evaluations use linear-radius rewards; only the new candidate's training is smooth.
Every bootstrap unit is one base reset, retaining its paired conditions/models.
Repeated seeds/geometries and one training run do not establish generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


MODELS = ("ExecutionV1Initial", "ExecutionV1SmoothDistance01")
HISTORICAL_MODEL = "ExecutionV1TwoRegions01"
ALL_MODELS = (*MODELS, HISTORICAL_MODEL)
BASELINE_MODELS = (MODELS[0], HISTORICAL_MODEL)
BASELINE_SOURCE = "48190f51a4fd7bedeca31377ea909afdba476722483d250a9610585a50e95f4c"
CONDITIONS = ("A", "B", "random")
EVALUATION_FILES = ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json")
FIRST_SEED, COUNT = 1108985, 256
SEEDS = list(range(FIRST_SEED, FIRST_SEED + COUNT))
BOOTSTRAP_SEED, BOOTSTRAP_DRAWS = 20260912, 10000
CONTRACT = "execution-v1-136obs-16continuous-release"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    require(len(rows) == COUNT, f"{path}: expected {COUNT} completed rows")
    result = {int(row["seed"]): row for row in rows}
    require(len(result) == COUNT and sorted(result) == SEEDS, f"{path}: duplicate/missing/unexpected seeds")
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_baseline(plan):
    """Validate every frozen prior input before opening any of them as evidence."""
    root = Path(plan["baselineRoot"])
    require(root.is_absolute() and root.is_dir(), "Baseline root must be an existing absolute directory")
    root = root.resolve()
    hashes = plan["baselineInputSha256"]
    require(isinstance(hashes, dict), "Missing baseline hash manifest")
    required = {f"evaluation/{model}/{condition}/{name}"
                for model in BASELINE_MODELS for condition in CONDITIONS for name in EVALUATION_FILES}
    required.update(("source-records.json", "audit/analysis.json"))
    require(required.issubset(hashes), f"Missing frozen baseline hashes: {sorted(required.difference(hashes))}")
    for relative, expected in hashes.items():
        path = root / relative
        require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root),
                f"Baseline manifest path escapes its root: {relative}")
        require(isinstance(expected, str) and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
                f"Invalid baseline digest: {relative}")
        require(path.is_file() and digest(path) == expected, f"Frozen baseline hash mismatch: {relative}")
    return root, hashes


def ci(values, mask=None):
    """Percentile interval of a mean, clustered by corresponding base-reset row."""
    values = np.asarray(values, dtype=float)
    if mask is None:
        mask = np.ones(len(values), dtype=bool)
    mask = np.asarray(mask, dtype=bool)
    require(len(values) == len(mask), "Bootstrap mask mismatch")
    n = len(values)
    valid_n = int(mask.sum())
    if n == 0 or valid_n == 0:
        return {"mean": None, "ci95": None, "baseResets": n, "contributingResets": valid_n}
    indices = np.random.default_rng(BOOTSTRAP_SEED).integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    selected = mask[indices]
    denominator = selected.sum(axis=1)
    boot = (values[indices] * selected).sum(axis=1)[denominator > 0] / denominator[denominator > 0]
    return {
        "mean": float(values[mask].mean()),
        "ci95": [float(v) for v in np.quantile(boot, [0.025, 0.975])],
        "baseResets": n, "contributingResets": valid_n,
        "bootstrapReplicatesWithContributors": int(len(boot)),
    }


def landing(row):
    return np.asarray([row["landingX"], row["landingZ"]], dtype=float)


def target(row):
    return np.asarray([row["targetX"], row["targetZ"]], dtype=float)


def hit(row, requested):
    # Illegal attempts never contribute to placement success, including the alternate region.
    return bool(row["legalLanding"] and np.linalg.norm(landing(row) - target(requested)) <= requested["radius"])


def group_key(episode):
    serve = "serve" in episode["task"] and episode["task"] != "receive-serve"
    side = ("left" if episode["serveFromLeft"] else "right") if serve else "not-serve"
    actual = bool(episode["movementFeed"] and episode["movementRange"] > 0)
    movement = "actual-movement" if actual else "central-or-familiar"
    return (episode["task"], side, movement, episode["movementPattern"],
            float(episode["movementRange"]), int(episode["movementRegion"]), int(episode["player"]))


def metrics(goals):
    legal = np.asarray([bool(r["legalLanding"]) for r in goals])
    hits = np.asarray([hit(r, r) for r in goals])
    bonus = np.asarray([r["bonus"] > 0 for r in goals])
    distances = [float(r["distance"]) for r in goals if r["legalLanding"]]
    n, nl = len(goals), int(legal.sum())
    return {
        "attempts": n, "legal": nl, "targets": int(hits.sum()), "nonzeroBonus": int(bonus.sum()),
        "legalPerAttempt": ci(legal), "targetPerAttempt": ci(hits), "bonusPerAttempt": ci(bonus),
        "targetGivenLegal": float(hits.sum() / nl) if nl else None,
        "meanDistanceGivenLegal": float(np.mean(distances)) if nl else None,
        "meanBonusPerAttempt": float(np.mean([r["bonus"] for r in goals])) if n else None,
    }


def causal(a, b):
    gains, shifts, both, both_hits = [], [], [], []
    for ar, br in zip(a, b):
        gains.append(0.5 * (int(hit(ar, ar)) - int(hit(ar, br)) + int(hit(br, br)) - int(hit(br, ar))))
        both.append(bool(ar["legalLanding"] and br["legalLanding"]))
        both_hits.append(bool(hit(ar, ar) and hit(br, br)))
        axis = target(br) - target(ar)
        require(np.linalg.norm(axis) > ar["radius"] + br["radius"], "Target regions overlap")
        shifts.append(float(np.dot(landing(br) - landing(ar), axis / np.linalg.norm(axis))) if both[-1] else 0.0)
    return {
        "assignmentGain": ci(gains), "bothRequestedTargetsHitPerPair": ci(both_hits),
        "bothLegalPairs": int(sum(both)), "allPairs": len(a),
        "landingShiftTowardBMetresGivenBothLegal": ci(shifts, both),
    }, np.asarray(gains)


def paired_changes_for(parent, candidate):
    return {
        "legalRateChange": ci([int(c["legalLanding"]) - int(p["legalLanding"]) for p, c in zip(parent, candidate)]),
        "targetRateChange": ci([int(hit(c, c)) - int(hit(p, p)) for p, c in zip(parent, candidate)]),
        "bonusIncidenceChange": ci([int(c["bonus"] > 0) - int(p["bonus"] > 0) for p, c in zip(parent, candidate)]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("F:/dev/picklebot/artifacts/hierarchy-v1/smooth-distance-01"))
    args = parser.parse_args()
    base = args.base
    output = base / "audit/analysis.json"
    require(not output.exists(), f"Refusing to overwrite {output}")
    plan = read_json(base / "plan.json")
    require(plan["parent"] == MODELS[0] and plan["candidate"] == MODELS[1], "Plan model mismatch")
    require(plan["firstSeed"] == FIRST_SEED and plan["baseResetCount"] == COUNT, "Plan reset mismatch")
    require(plan.get("finalSeedsConsumed") is False, "Final seed declaration missing/invalid")
    baseline_root, baseline_hashes = verified_baseline(plan)
    source_identities = plan["modelSourceIdentities"]
    require(all(model in source_identities for model in ALL_MODELS), "Missing per-model source identity")
    require(all(source_identities[model] == BASELINE_SOURCE for model in BASELINE_MODELS), "Unexpected baseline source identity")
    require(isinstance(source_identities[MODELS[1]], str) and len(source_identities[MODELS[1]]) == 64
            and all(c in "0123456789abcdef" for c in source_identities[MODELS[1]]), "Invalid candidate source identity")
    inputs = {"plan.json": digest(base / "plan.json")}
    inputs.update({f"baseline/{path}": value for path, value in baseline_hashes.items()})
    runs = {}
    for model in ALL_MODELS:
        for condition in CONDITIONS:
            reused = model in BASELINE_MODELS
            root = baseline_root if reused else base
            folder = root / "evaluation" / model / condition
            files = [folder / name for name in EVALUATION_FILES]
            for path in files:
                require(path.is_file(), f"Missing complete evaluation input: {path}")
                relative = path.relative_to(root).as_posix()
                if reused:
                    require(digest(path) == baseline_hashes[relative], f"Baseline changed after verification: {path}")
                else:
                    inputs[f"current/{relative}"] = digest(path)
            episodes, goals = read_rows(files[0]), read_rows(files[1])
            first = {int(k): v for k, v in read_json(files[2]).items()}
            require(sorted(first) == SEEDS, f"{folder}: first-decision seeds mismatch")
            report = read_json(files[3])
            require(report["status"] == "seed_budget_complete" and not report.get("failure"), f"{folder}: unsuccessful report")
            require(report["completedEpisodes"] == COUNT and report["firstSeed"] == FIRST_SEED and report["seedCount"] == COUNT, f"{folder}: incomplete budget")
            require(report["sourceIdentity"] == source_identities[model] and report["contract"] == CONTRACT, f"{folder}: source/contract mismatch")
            require(not report["trainerConnected"], f"{folder}: evaluation connected to trainer")
            for seed in SEEDS:
                ep, row, decision = episodes[seed], goals[seed], first[seed]
                require(row.get("rewardMode", "linear-radius" if reused else None) == "linear-radius", f"{folder}/{seed}: evaluation must use linear-radius rewards")
                require(row["assigned"] and row["contract"] == CONTRACT, f"{folder}/{seed}: missing assigned goal/contract")
                require(ep["player"] == row["player"] == decision["player"] and decision["seed"] == seed, f"{folder}/{seed}: private identity mismatch")
                obs, action = np.asarray(decision["observation"]), np.asarray(decision["physical"])
                require(obs.shape == (136,) and action.shape == (18,) and np.isfinite(obs).all() and np.isfinite(action).all(), f"{folder}/{seed}: invalid first decision")
                require(row["legalLanding"] == (ep["outcome"] in ("legal_return", "legal_serve")), f"{folder}/{seed}: legality mismatch")
                require(row["hasLanding"] == row["legalLanding"], f"{folder}/{seed}: landing availability mismatch")
                radius = 1.5 if condition == "random" else 1.0
                require(abs(row["radius"] - radius) < 1e-6, f"{folder}/{seed}: wrong radius")
                require(np.allclose(obs[132:136], [1, row["targetX"] / 3.048, row["targetZ"] / 6.7056, radius / 3], atol=2e-6, rtol=0), f"{folder}/{seed}: observed goal does not match evidence")
                require(np.isfinite([row[k] for k in ("targetX", "targetZ", "radius", "distance", "bonus", "landingX", "landingZ")]).all(), f"{folder}/{seed}: nonfinite outcome")
                if row["legalLanding"]:
                    require(abs(np.linalg.norm(landing(row) - target(row)) - row["distance"]) < 2e-5, f"{folder}/{seed}: recorded landing distance mismatch")
                computed_hit = hit(row, row)
                if "targetHit" in row:
                    # Unity computes distance in float32: boundary disagreements are surfaced, not silently hidden.
                    require(bool(row["targetHit"]) == computed_hit, f"{folder}/{seed}: target-hit boundary/evidence mismatch")
                expected_bonus = .25 * max(0.0, 1 - row["distance"] / radius) if row["legalLanding"] else 0.0
                require(abs(row["bonus"] - expected_bonus) < 2e-5, f"{folder}/{seed}: target bonus mismatch")
            runs[model, condition] = (episodes, goals, first, report)

    # Validate pairing before computing any outcome comparisons.
    negative_control = {"matchedResets": COUNT, "identicalFirstPhysicalActions": 0, "identicalPhysicalEpisodes": 0, "identicalLegalLandings": 0}
    for seed in SEEDS:
        reference = runs[MODELS[0], "A"]
        reference_observation = np.asarray(reference[2][seed]["observation"])
        for model in ALL_MODELS:
            for condition in CONDITIONS:
                ep, goals, first, _ = runs[model, condition]
                require(np.array_equal(np.asarray(first[seed]["observation"])[:124], reference_observation[:124]), f"{model}/{condition}/{seed}: initial physical observations differ")
                require(group_key(ep[seed]) == group_key(reference[0][seed]), f"{model}/{condition}/{seed}: curriculum membership differs")
                parent_goal = runs[MODELS[0], condition][1][seed]
                require(np.array_equal(target(goals[seed]), target(parent_goal)), f"{model}/{condition}/{seed}: target changed between models")
                if condition != "random":
                    row = goals[seed]
                    serve = ep[seed]["task"] == "stationary-serve"
                    expected = [np.sign(row["targetX"]) * 1.4, 3.3 if condition == "A" else 5.4] if serve else [-1.2 if condition == "A" else 1.2, 3.8]
                    require(np.allclose(target(row), expected, atol=2e-6, rtol=0), f"{model}/{condition}/{seed}: unexpected region coordinates")
        ia, ib = runs[MODELS[0], "A"], runs[MODELS[0], "B"]
        require(np.array_equal(ia[2][seed]["physical"], ib[2][seed]["physical"]), f"Initializer action negative control failed: {seed}")
        negative_control["identicalFirstPhysicalActions"] += 1
        epa = {k: v for k, v in ia[0][seed].items() if k != "reward"}
        epb = {k: v for k, v in ib[0][seed].items() if k != "reward"}
        require(epa == epb, f"Initializer physical episode negative control failed: {seed}")
        negative_control["identicalPhysicalEpisodes"] += 1
        require(ia[1][seed]["legalLanding"] == ib[1][seed]["legalLanding"], f"Initializer legality negative control failed: {seed}")
        if ia[1][seed]["legalLanding"]:
            require(np.array_equal(landing(ia[1][seed]), landing(ib[1][seed])), f"Initializer landing negative control failed: {seed}")
            negative_control["identicalLegalLandings"] += 1

    base_episodes = runs[MODELS[0], "A"][0]
    drills = sorted({ep["task"] for ep in base_episodes.values()})
    # Full joint breakdowns plus drill and movement totals avoid hiding sparse cells.
    grouping = {"all": SEEDS}
    for drill in drills:
        grouping[f"drill/{drill}"] = [s for s in SEEDS if base_episodes[s]["task"] == drill]
        for side in ("left", "right"):
            side_seeds = [s for s in SEEDS if base_episodes[s]["task"] == drill and group_key(base_episodes[s])[1] == side]
            if side_seeds:
                grouping[f"drill/{drill}/serve-side/{side}"] = side_seeds
    for movement in ("actual-movement", "central-or-familiar"):
        grouping[f"movement/{movement}"] = [s for s in SEEDS if group_key(base_episodes[s])[2] == movement]
    for key in sorted({group_key(ep) for ep in base_episodes.values()}):
        name = "cell/" + "/".join(str(item) for item in key)
        grouping[name] = [s for s in SEEDS if group_key(base_episodes[s]) == key]
    grouping = {k: v for k, v in grouping.items() if v}
    summaries, paired_changes, causal_results, causal_changes = {}, {}, {}, {}
    gains = {}
    for group, seeds in grouping.items():
        summaries[group], paired_changes[group], causal_results[group] = {}, {}, {}
        for model in ALL_MODELS:
            summaries[group][model] = {}
            for condition in CONDITIONS:
                summaries[group][model][condition] = metrics([runs[model, condition][1][s] for s in seeds])
            result, values = causal([runs[model, "A"][1][s] for s in seeds], [runs[model, "B"][1][s] for s in seeds])
            causal_results[group][model] = result
            gains[model, group] = values
        require(np.all(gains[MODELS[0], group] == 0), f"Initializer assignment gain did not cancel: {group}")
        causal_changes[group] = ci(gains[MODELS[1], group] - gains[MODELS[0], group])
        for condition in CONDITIONS:
            parent = [runs[MODELS[0], condition][1][s] for s in seeds]
            candidate = [runs[MODELS[1], condition][1][s] for s in seeds]
            paired_changes[group][condition] = paired_changes_for(parent, candidate)

    # This additional historical comparison is descriptive; it does not replace
    # the predeclared primary screen or establish a replicated reward-mode effect.
    historical_comparison = {}
    for group in ["all", *(f"drill/{drill}" for drill in drills)]:
        seeds = grouping[group]
        historical_comparison[group] = {
            "assignmentGainChange": ci(gains[MODELS[1], group] - gains[HISTORICAL_MODEL, group]),
            "conditions": {
                condition: paired_changes_for(
                    [runs[HISTORICAL_MODEL, condition][1][s] for s in seeds],
                    [runs[MODELS[1], condition][1][s] for s in seeds])
                for condition in CONDITIONS},
        }

    legal_checks = [{"drill": drill, "condition": condition,
                     "change": paired_changes[f"drill/{drill}"][condition]["legalRateChange"]["mean"]}
                    for drill in drills for condition in CONDITIONS]
    lower = causal_results["all"][MODELS[1]]["assignmentGain"]["ci95"][0]
    tests = {
        "assignmentGainCiLowerAboveZero": lower > 0,
        "bothRegionTargetRatesImprove": all(paired_changes["all"][c]["targetRateChange"]["mean"] > 0 for c in ("A", "B")),
        "noDrillLegalDropGreaterThanFivePercentagePoints": all(r["change"] >= -.05 - 1e-12 for r in legal_checks),
    }
    result = {
        "status": "complete_development_screen", "models": list(MODELS), "modelSourceIdentities": source_identities,
        "historicalComparator": HISTORICAL_MODEL,
        "provenance": {
            "baselineRoot": str(baseline_root), "baselineInputSha256": baseline_hashes,
            "reusedModels": list(BASELINE_MODELS), "newlyEvaluatedModels": [MODELS[1]],
            "baselineWasReevaluated": False, "evaluationRewardMode": "linear-radius",
            "interpretation": "Prior frozen evaluations retain their original source identities; source-delta audit and trajectory parity support reuse, not a new full baseline replay.",
        },
        "baseResets": COUNT, "attemptsPerModel": COUNT * len(CONDITIONS), "inputSha256": inputs,
        "negativeControl": negative_control,
        "analysisScriptSha256": digest(Path(__file__)),
        "uniqueInitialPhysicalObservationCount": len({tuple(runs[MODELS[0], "A"][2][s]["observation"][:124]) for s in SEEDS}),
        "bootstrap": {"method": "paired base-reset percentile bootstrap", "seed": BOOTSTRAP_SEED, "replicates": BOOTSTRAP_DRAWS,
                      "coverage": "pointwise 95%; not simultaneous across cells; one training lineage; repeated geometries are not independent situations"},
        "groupKey": ["task", "serviceSide", "movementCategory", "movementPattern", "movementRange", "movementRegion", "player"],
        "summaries": summaries, "pairedCandidateMinusParent": paired_changes,
        "causal": causal_results, "pairedAssignmentGainChange": causal_changes,
        "pairedCandidateMinusHistoricalLinear": historical_comparison,
        "screen": {"rule": plan["screening"], "tests": tests, "promising": all(tests.values()),
                   "legalRetentionChecks": legal_checks, "retentionInterpretation": "Point-estimate legal-drop limit applies to every drill in A, B and unchanged random conditions; uncertainty is reported separately."},
        "promoted": False, "masteryAccepted": False, "finalSeedsConsumed": False,
        "limitations": [
            "Reused development resets; this screen cannot establish final acceptance or a robust training-seed effect.",
            "Conditional landing shifts use only both-legal pairs and must be read with their denominator and unconditional success.",
            "Positive assignment gain means the requested target changes region-specific success; first-action sensitivity alone is not useful aiming.",
            "Sparse subgroup percentile intervals can be degenerate; all-success or all-failure small cells do not prove certainty.",
            "Current movement range and feed coverage do not establish mastery of arbitrary wide/deep/shallow feeds or target feasibility.",
            "The primary comparison measures learning versus the initializer; the historical linear-trained comparison is secondary and has one training run per recipe.",
            "Historical baseline results were reused with verified hashes and original sources; they were not rerun under the candidate build.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    brief_counts = {model: {condition: {key: summaries["all"][model][condition][key]
                                       for key in ("attempts", "legal", "targets", "nonzeroBonus")}
                           for condition in CONDITIONS} for model in ALL_MODELS}
    print(json.dumps({"analysis": str(output), "promising": result["screen"]["promising"],
                      "screenTests": tests, "counts": brief_counts,
                      "candidateAssignmentGain": causal_results["all"][MODELS[1]]["assignmentGain"],
                      "promoted": False, "masteryAccepted": False}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
