"""Audit the complete frozen wide-movement diagnostic; never select successful cases.

Requires the pre-outcome reset-only fixture and all four full evaluations. Writes
only an exclusive campaign/audit/analysis.json. No training, simulation or promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

sys.dont_write_bytecode = True
CAMPAIGN = "artifacts/hierarchy-v1/wide-movement-fixture-01"
FRESH_HELPER = "research/hierarchy-v1/fresh-placement-01/analyze_fresh_placement.py"
FRESH_HELPER_SHA = "5223da419a0d08453afca78d86845e8a8c4db4d0135b73c11e64fdd56ea202e4"
SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
INITIAL, CANDIDATE = "ExecutionV1Initial", "ExecutionV1SmoothContinuedFinal01"
MODELS, CONDITIONS = (INITIAL, CANDIDATE), ("A", "B")
DRILLS = ("stationary-serve", "receive-feed", "rally-air-feed", "rally-bounce-feed")
DIRECTIONS = ("left", "right", "shallow", "deep")
RECIPE = dict(task="movement-maintenance", maximumReturnDifficulty=.25,
              movementRange=.25, movementPattern="axes", movementRehearsalRange=0,
              movementRecoveryMix=False, interleavedRecovery=False, movementTiming=0,
              movementStartVariation=0, movementPositionReward=0, fixedServeSides="both")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helpers(root, inputs):
    path = root / FRESH_HELPER
    require(path.is_file() and sha(path) == FRESH_HELPER_SHA, "Preserved helper hash mismatch")
    inputs[FRESH_HELPER] = FRESH_HELPER_SHA
    spec = importlib.util.spec_from_file_location("wide_preserved_utilities", path)
    require(spec is not None and spec.loader is not None, "Cannot load preserved utilities")
    f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f)
    return f, f.load_helper(root, inputs)


def coverage_key(row):
    if row["challenge"]:
        return f'{row["task"]}/{row["direction"]}/{row["centimetres"]}cm/player-{row["player"]}'
    return f'{row["task"]}/familiar/player-{row["player"]}/left-{row["serveFromLeft"]}'


def validate_provenance(f, root, base, plan, inputs):
    for name in ("source-records.json", "allocation.json", "seed-ledger-before.json", "script-hashes.json"):
        f.record_input(root, base / name, inputs)
    source, allocation = read(base / "source-records.json"), read(base / "allocation.json")
    require(source["sourceIdentity"] == SOURCE, "Source manifest identity mismatch")
    digest = hashlib.sha256(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(digest == SOURCE, "Source manifest contents do not produce the declared identity")
    for relative, expected in source["files"].items():
        f.record_input(root, f.inside(root, relative), inputs, expected)
    require(all(allocation[key] == value for key, value in
                (("firstSeed", plan["firstSeed"]), ("count", plan["seedCount"]),
                 ("planHash", sha(base / "plan.json")), ("finalSeedsConsumed", False))), "Allocation mismatch")
    require(sha(base / "seed-ledger-before.json") == allocation["ledgerBeforeHash"]
            == plan["freshness"]["ledgerBeforeHash"], "Ledger-before hash mismatch")
    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    f.record_input(root, ledger_path, inputs, allocation["ledgerAfterHash"])
    ledger = read(ledger_path)
    require(ledger["version"] == "player-v3-seed-ledger-1" and ledger["finalSeedsConsumed"] == [], "Final seed ledger changed")
    overlaps = [block for block in ledger["developmentBlocks"] if
                plan["firstSeed"] < block["firstSeed"] + block["count"] and
                plan["firstSeed"] + plan["seedCount"] > block["firstSeed"]]
    require(len(overlaps) == 1 and overlaps[0]["firstSeed"] == plan["firstSeed"]
            and overlaps[0]["count"] == plan["seedCount"] and overlaps[0]["run"] == CAMPAIGN, "Incorrect seed reservation")
    selected = plan["provenance"]
    f.record_input(root, f.inside(root, selected["modelSelectionPlan"]), inputs, selected["modelSelectionPlanHash"])
    template = base / "fixture-template.cs"
    f.record_input(root, template, inputs, plan["fixture"]["templateSha256"])
    # Preserve original and amended script manifests. The archive separately copies
    # exact executed scripts; runtime source and observed resets are checked here.
    for path in sorted(base.glob("*amendment*.json")) + sorted(base.glob("*script-hashes*.json")) + sorted(base.glob("fixture-script-revision-*.json")):
        f.record_input(root, path, inputs)
    return allocation


def validate_fixture(f, root, base, plan, seeds, allocation, inputs):
    """Must finish before opening any policy outcome file."""
    for name in ("fixture-summary.json", "fixture-hashes.json"):
        f.record_input(root, base / name, inputs)
    gate, frozen = read(base / "fixture-summary.json"), read(base / "fixture-hashes.json")
    require(gate["status"] == "reset_fixture_valid" and gate["outcomeAllowed"] is True
            and gate["seedCount"] == len(seeds) and gate["firstSeed"] == seeds[0]
            and gate["planSha256"] == sha(base / "plan.json"), "Pre-outcome fixture gate is not passed for this plan")
    require(gate["identity"]["sourceIdentity"] == SOURCE and gate["identity"]["ledgerHash"] == allocation["ledgerAfterHash"]
            and gate["policyActions"] == gate["physicsTicks"] == gate["rewardsCollected"] == 0
            and gate["outcomesMeasured"] is False and gate["masteryAccepted"] is False, "Fixture gate provenance mismatch")
    for absolute, expected in gate["inputSha256"].items():
        path = Path(absolute).resolve()
        require(path.is_relative_to(root), f"Fixture gate input escapes repository: {absolute}")
        f.record_input(root, path, inputs, expected)
    expected_paths = [f"wide-fixture-{ordinal:04d}.json" for ordinal in range(0, len(seeds), 64)]
    require(isinstance(frozen, dict) and set(frozen) == set(expected_paths), "Fixture hash manifest must cover exactly eight batches")
    require(plan["fixture"]["batchSize"] == 64 and plan["fixture"]["batchOrdinals"] == list(range(0, len(seeds), 64)), "Fixture batch plan mismatch")
    rows, planned = {}, None
    assemblies, versions = set(), set()
    source_hash = sha(base / "source-records.json")
    declared_coverage, declared_missing = None, None
    for ordinal, relative in zip(range(0, len(seeds), 64), expected_paths):
        path = f.inside(root, f"{CAMPAIGN}/fixture/{relative}")
        f.record_input(root, path, inputs, frozen[relative])
        batch = read(path)
        require(batch["status"] == "reset_fixture_only" and batch["reservation"] == CAMPAIGN
                and batch["firstSeed"] == seeds[0] and batch["seedCount"] == len(seeds), f"{relative}: wrong fixture identity")
        require(batch["sourceIdentity"] == SOURCE and batch["sourceRecordHash"] == source_hash
                and batch["ledgerHash"] == allocation["ledgerAfterHash"], f"{relative}: fixture source/ledger mismatch")
        require(batch["inspectFirstOrdinal"] == ordinal and batch["inspectCount"] == 64
                and len(batch["rows"]) == 64, f"{relative}: wrong actual capture count")
        require(batch["policyActions"] == batch["physicsTicks"] == batch["rewardsCollected"] == 0
                and all(batch[key] is False for key in ("modelsLoaded", "physicalReachabilityProven", "legalReturnAbilityProven", "promoted", "finalSeedsConsumed")), f"{relative}: fixture advanced or loaded policies")
        assemblies.add(batch["loadedAssembly"])
        versions.add(batch["unityVersion"])
        if planned is None:
            planned = batch["planned"]
            declared_coverage, declared_missing = batch["plannedCoverage"], batch["missingJointCells"]
        require(batch["planned"] == planned and batch["plannedCoverage"] == declared_coverage
                and batch["missingJointCells"] == declared_missing, "Planned reset schedule changed between fixture batches")
        require(len(planned) == len(seeds), "Fixture planned count mismatch")
        actual_coverage = Counter()
        require([row["index"] for row in batch["rows"]] == list(range(ordinal, ordinal + 64)), "Wrong inspected ordinal range")
        for row in batch["rows"]:
            index, seed = row["index"], row["seed"]
            desc = planned[index]
            require(seed == seeds[index] and seed not in rows, "Duplicate or unexpected fixture reset")
            for key in ("index", "seed", "player", "task", "pattern", "range", "region", "direction", "centimetres", "challenge"):
                require(row[key] == desc[key], f"{seed}: actual fixture differs from planned {key}")
            require(row["actualTicks"] == row["worldSeconds"] == 0 and row["policiesAttached"] is False
                    and row["outcomeMeasured"] is False, "Fixture row advanced or attached policies")
            physical = np.asarray(row["physicalObservation124"], dtype=np.float32)
            require(physical.shape == (124,) and np.isfinite(physical).all(), "Invalid reset physical observation")
            instructions = {item["condition"]: item for item in row["instructions"]}
            require(len(row["instructions"]) == 2 and set(instructions) == set(CONDITIONS), "Missing fixture goal instruction")
            for condition, instruction in instructions.items():
                obs = np.asarray(instruction["observation136"], dtype=np.float32)
                f.physical_key(obs)
                require(np.array_equal(obs[:124], physical) and instruction["radius"] == 1, "Fixture instruction altered physical observation")
                sign = 1 if desc["serveFromLeft"] else -1
                target = ([sign * 1.4, 3.3 if condition == "A" else 5.4] if desc["task"] == "stationary-serve"
                          else [-1.2 if condition == "A" else 1.2, 3.8])
                require(np.allclose([instruction["targetX"], instruction["targetZ"]], target, rtol=0, atol=2e-6), "Fixture target geometry mismatch")
                require(np.array_equal(obs[124:132], [1, 0, 0, 0, 0, 0, 0, 0])
                        and np.allclose(obs[132:], [1, target[0]/3.048, target[1]/6.7056, 1/3], rtol=0, atol=2e-6), "Fixture goal encoding mismatch")
            if row["range"] >= 0:
                face, nominal = np.asarray(row["paddleFace"]), np.asarray(row["nominalPoint"])
                shift = (nominal - face)[[0, 2]] * (1 if row["player"] < 2 else -1)
                require(np.allclose(shift, row["canonicalNominalShift"], rtol=0, atol=2e-5)
                        and abs(np.linalg.norm(shift)-row["nominalDistanceMetres"]) < 2e-5, "Fixture nominal-shift telemetry mismatch")
                if row["challenge"]:
                    distance = row["centimetres"] / 100
                    desired = {"left": [-distance, 0], "right": [distance, 0], "shallow": [0, distance], "deep": [0, -distance]}[row["direction"]]
                    require(np.allclose(shift, desired, rtol=0, atol=2e-5), "Nominal cm/direction differs from actual geometry")
                else:
                    require(np.linalg.norm(shift) < 2e-5, "Familiar rally feed has an unexpected shift")
            else:
                require(row["nominalPoint"] is None and row["nominalDistanceMetres"] is None, "Nonmovement nominal telemetry is not null")
            rows[seed] = row
            actual_coverage[coverage_key(desc)] += 1
        require(dict(actual_coverage) == batch["inspectedCoverage"], "Actual batch coverage mismatch")
    require(sorted(rows) == seeds, "Reset-only fixture is incomplete")
    coverage = Counter()
    for index, desc in enumerate(planned):
        block = index // 4 % 16
        task = "stationary-serve" if block < 2 else "receive-feed" if block < 4 else "rally-air-feed" if block < 6 or 8 <= block < 12 else "rally-bounce-feed"
        challenge = block >= 8
        movement_range = -1 if block < 4 else 0 if block < 8 else .25 * (1 + block % 4) * .25
        expected = dict(index=index, seed=seeds[index], player=index % 4, task=task, challenge=challenge,
                        pattern="axes" if challenge else "court", range=movement_range,
                        centimetres=round(400*movement_range) if challenge else 0,
                        serveFromLeft=block == 1, difficulty=1 if block < 2 else .25 if block == 3 else 0)
        require(all(desc[key] == value for key, value in expected.items()), f"{seeds[index]}: schedule recipe mismatch")
        if challenge:
            require(desc["direction"] == {3:"left", 5:"right", 1:"shallow", 7:"deep"}.get(desc["region"]), "Axis direction/region mismatch")
        else:
            require(desc["direction"] == "familiar" and (desc["region"] == -1 if block < 4 else desc["region"] in range(9)), "Familiar descriptor mismatch")
        coverage[coverage_key(desc)] += 1
    require(dict(coverage) == declared_coverage, "Whole planned coverage mismatch")
    expected_cells = [f"{task}/{direction}/{cm}cm/player-{player}" for task in DRILLS[2:]
                      for direction in DIRECTIONS for cm in (25, 50, 75, 100) for player in range(4)]
    missing = [cell for cell in expected_cells if not coverage[cell]]
    require(missing == declared_missing, "Declared missing-cell coverage mismatch")
    return rows, {row["seed"]: row for row in planned}, {
        "seedCount": len(seeds), "actualCapturedResets": len(rows), "noPolicyActionsOrSimulationTicks": True,
        "preOutcomeGate": gate, "loadedAssemblies": sorted(assemblies), "unityVersions": sorted(versions),
        "plannedCoverage": dict(coverage), "missingJointCells": missing,
        "sparseChallengeCellsUnderFiveAttempts": {cell: coverage[cell] for cell in expected_cells if 0 < coverage[cell] < 5},
        "resetsWithRecordedOverlaps": [seed for seed, row in rows.items() if row["overlaps"]],
        "resetRejectionRecords": {str(seed): row["rejectedSurfaces"] for seed, row in rows.items() if row["rejectedSurfaces"]},
        "nominalPointsOutsideCourt": [seed for seed, row in rows.items() if row["nominalPointInCourt"] is False],
        "nominalPointsInKitchen": [seed for seed, row in rows.items() if row["nominalPointInKitchen"] is True],
        "physicalReachabilityProven": False,
        "interpretation": "Nominal shift is relative to the initial paddle face. It is not required body travel, actual contact displacement, or demonstrated reachability. No overlap or sparse case is removed."}


def validate_run(f, h, root, folder, model, condition, identity, seeds, descriptors, fixture, inputs):
    for name in (*f.FILES, "summary.json"):
        f.record_input(root, folder / name, inputs)
    sidecar = read(folder / "model-identity.json")
    require(sidecar["model"] == model and all(sidecar[key] == identity[key] for key in
            ("modelHash", "checkpointHash", "step", "sourceIdentity")), f"{folder}: model identity mismatch")
    episodes, goals = (f.read_rows(folder / name, seeds) for name in ("episodes.jsonl", "execution-goals.jsonl"))
    raw = read(folder / "first-decisions.json")
    first = {int(key): value for key, value in raw.items()}
    require(len(raw) == len(first) == len(seeds) and sorted(first) == seeds, "First-decision reset coverage mismatch")
    report = read(folder / "report.json")
    require(report["status"] == "seed_budget_complete" and not report.get("failure"), "Incomplete/failed evaluation")
    require(report["firstSeed"] == seeds[0] and all(report[key] == len(seeds) for key in
            ("seedCount", "completedEpisodes", "nextSeedIndex")), "Evaluation reset count mismatch")
    require(report["sourceIdentity"] == SOURCE and report["contract"] == f.CONTRACT
            and report["split"] == "development" and report["trainerConnected"] is False, "Evaluation runtime contract mismatch")
    require(all(report[key] == value for key, value in RECIPE.items()), "Evaluation used a different physical recipe")
    require(all(report[key] is False for key in ("alignedDecisions", "randomMatchContext", "cooperativePairs", "activePracticePlayers"))
            and report["backgroundDecisions"] == 0 and all(report[key] == 0 for key in
            ("stationaryFlightDifficulty", "feedLowering", "feedLateralOffset", "initialHoldLift")), "Unexpected contextual/feed changes")
    for seed in seeds:
        ep, goal, decision, desc = episodes[seed], goals[seed], first[seed], descriptors[seed]
        label = f"{model}/{condition}/{seed}"
        for actual, expected in (("task", "task"), ("player", "player"), ("serveFromLeft", "serveFromLeft"),
                                 ("feedDifficulty", "difficulty"), ("movementPattern", "pattern"), ("movementRange", "range")):
            require(ep[actual] == desc[expected], f"{label}: wrong reset descriptor {actual}")
        movement = desc["range"] >= 0
        require(ep["movementFeed"] is movement and (not movement or ep["movementRegion"] == desc["region"]), "Movement descriptor mismatch")
        require(all(ep[key] == 0 for key in ("movementTiming", "movementStartVariation", "movementPositionRewardScale", "movementPositionReward"))
                and ep["cooperativePairs"] is False and ep["randomMatchContext"] is False, "Unexpected movement/controller shaping")
        require(ep["player"] == goal["player"] == decision["player"] and decision["seed"] == seed, "Private player identity mismatch")
        obs = np.asarray(decision["observation"], dtype=np.float32)
        f.physical_key(obs)
        instruction = next(item for item in fixture[seed]["instructions"] if item["condition"] == condition)
        require(np.array_equal(obs, np.asarray(instruction["observation136"], dtype=np.float32)), f"{label}: evaluation observation differs from reset-only fixture")
        action = np.asarray(decision["physical"], dtype=float)
        require(action.shape == (18,) and np.isfinite(action).all(), "Invalid first action")
        require(goal["contract"] == f.CONTRACT and goal["assigned"] is True and goal["rewardMode"] == "linear-radius"
                and goal["targetLayout"] == "two-regions", "Unexpected evaluation goal/reward contract")
        require(goal["radius"] == 1 and np.allclose(h.target(goal), [instruction["targetX"], instruction["targetZ"]], rtol=0, atol=2e-6), "Requested target mismatch")
        require(ep["outcome"] == goal["outcome"] and ep["outcome"] not in ("exception", "infeasible"), "Outcome mismatch/simulator failure")
        legal = ep["outcome"] in ("legal_return", "legal_serve")
        require(goal["legalLanding"] is legal and goal["hasLanding"] is legal, "Legal outcome mismatch")
        for key in ("faceContact", "netCrossed", "incomingServeLanded", "contactWasVolley", "serveAccepted"):
            require(type(ep[key]) is bool, f"Missing actual contact indicator: {key}")
        require(not legal or ep["faceContact"] and ep["netCrossed"], "Legal result lacks actual contact/net crossing")
        serve, receive = ep["task"] == DRILLS[0], ep["task"] == DRILLS[1]
        phase = [1,0,0,0,0] if serve else [0,1,0,0,0] if receive else [0,0,0,1,0]
        require(np.array_equal(obs[39:44], phase), "Wrong initial rules phase")
        if serve:
            require(obs[44] == 1 and (not legal or ep["outcome"] == "legal_serve" and ep["serveAccepted"]), "Serve rule evidence mismatch")
        if receive:
            require(obs[45] == 1 and obs[48] == 0 and (not ep["faceContact"] or ep["incomingServeLanded"]), "Required-bounce contact evidence mismatch")
        require(not ep["contactWasVolley"] or ep["task"] in DRILLS[2:] and ep["faceContact"], "Volley marker without accepted rally contact")
        require(np.isfinite([goal[key] for key in ("distance", "bonus", "landingX", "landingZ")]).all(), "Nonfinite landing evidence")
        if legal:
            require(goal["distance"] >= 0 and abs(np.linalg.norm(h.landing(goal)-h.target(goal))-goal["distance"]) < 2e-5, "Landing distance mismatch")
        else:
            require(goal["distance"] == -1 and goal["landingX"] == goal["landingZ"] == 0, "Wrong absent-landing sentinel")
        require(type(goal["targetHit"]) is bool and goal["targetHit"] == h.hit(goal, goal), "Target-hit mismatch")
        bonus = .25 * max(0, 1-goal["distance"]) if legal else 0
        require(0 <= goal["bonus"] <= .25 and abs(goal["bonus"]-bonus) < 2e-5, "Linear evaluation reward mismatch")
        if movement:
            path = np.asarray(ep["travelBeforeContact"], dtype=float)
            require(path.shape == (4,) and np.isfinite(path).all() and (path >= 0).all(), "Missing measured movement path")
            if ep["faceContact"]:
                require(ep["hitter"] == ep["player"], "Solo movement contact was not made by the learner")
                values = [ep[key] for key in ("contactDisplacement", "contactDistanceFromStart", "faceContactBallHeight")]
                require(np.isfinite(values).all() and min(values) >= 0 and ep["contactDisplacement"] <= path[ep["player"]] + 1e-4, "Invalid path/contact displacement evidence")
    summary = read(folder / "summary.json")
    require(summary == dict(model=model, condition=condition, episodes=len(seeds),
                            legal=sum(row["legalLanding"] for row in goals.values()), targets=sum(row["targetHit"] for row in goals.values())), "Evaluation summary does not match raw outcomes")
    return episodes, goals, first, report


def values_summary(values):
    data = np.asarray(values, dtype=float)
    return {"measuredAttempts": len(data), "mean": float(data.mean()) if len(data) else None,
            "median": float(np.median(data)) if len(data) else None,
            "quantiles": {str(q): float(np.quantile(data, q)) for q in (0, .25, .75, .9, 1)} if len(data) else {}}


def telemetry(f, episodes):
    moving = [ep for ep in episodes if ep["movementFeed"]]
    contacted = [ep for ep in moving if ep["faceContact"]]
    missed = [ep for ep in moving if not ep["faceContact"]]
    path = lambda ep: ep["travelBeforeContact"][ep["player"]]
    return {**f.contact_counts(episodes), "acceptedFaceContacts": sum(ep["faceContact"] for ep in episodes),
            "netCrossings": sum(ep["netCrossed"] for ep in episodes),
            "movementTelemetryAttempts": len(moving), "unmeasuredNonmovementAttempts": len(episodes)-len(moving),
            "rootPathThroughFirstContactOrTerminalMetres": values_summary([path(ep) for ep in moving]),
            "rootPathBeforeAcceptedContactMetres": values_summary([path(ep) for ep in contacted]),
            "rootPathThroughNoContactTerminationMetres": values_summary([path(ep) for ep in missed]),
            "netRootDisplacementConditionalOnAcceptedContactMetres": values_summary([ep["contactDisplacement"] for ep in contacted]),
            "ballDistanceFromInitialRootConditionalOnAcceptedContactMetres": values_summary([ep["contactDistanceFromStart"] for ep in contacted]),
            "ballHeightConditionalOnAcceptedMovementContactMetres": values_summary([ep["faceContactBallHeight"] for ep in contacted])}


def compact(episodes, goals):
    n = len(episodes)
    contacted = [ep for ep in episodes if ep["faceContact"]]
    paths = [ep["travelBeforeContact"][ep["player"]] for ep in episodes]
    return dict(attempts=n, legal=sum(row["legalLanding"] for row in goals), targets=sum(row["targetHit"] for row in goals),
                acceptedContacts=sum(ep["faceContact"] for ep in episodes), netCrossings=sum(ep["netCrossed"] for ep in episodes),
                actualVolleyContacts=sum(ep["faceContact"] and ep["contactWasVolley"] for ep in episodes),
                actualAfterBounceRallyContacts=sum(ep["task"] in DRILLS[2:] and ep["faceContact"] and not ep["contactWasVolley"] for ep in episodes),
                rootPathThroughContactOrTerminationMeanMetres=float(np.mean(paths)) if paths else None,
                contactDisplacementMeasuredAttempts=len(contacted),
                contactDisplacementMeanMetres=float(np.mean([ep["contactDisplacement"] for ep in contacted])) if contacted else None)


def paired_telemetry(h, before, after):
    require(len(before) == len(after) and all(a["seed"] == b["seed"] and a["movementFeed"] == b["movementFeed"]
            for a,b in zip(before, after)), "Unpaired movement telemetry")
    moving = [(a,b) for a,b in zip(before,after) if a["movementFeed"]]
    contacted = [(a,b) for a,b in moving if a["faceContact"] and b["faceContact"]]
    result = {"acceptedContactRateChange":h.ci([int(b["faceContact"])-int(a["faceContact"]) for a,b in zip(before,after)]),
              "netCrossingRateChange":h.ci([int(b["netCrossed"])-int(a["netCrossed"]) for a,b in zip(before,after)]),
              "movementAttemptPairs":len(moving), "bothAcceptedMovementContactPairs":len(contacted)}
    if moving:
        result["rootPathThroughContactOrTerminationChangeMetres"] = h.ci([
            b["travelBeforeContact"][b["player"]]-a["travelBeforeContact"][a["player"]] for a,b in moving])
        values = [b["contactDisplacement"]-a["contactDisplacement"] for a,b in moving]
        mask = [a["faceContact"] and b["faceContact"] for a,b in moving]
        # Bootstrap all matched movement resets, then condition within each draw.
        result["netDisplacementChangeConditionalOnBothAcceptedContactsMetres"] = h.ci(values, mask)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    args = parser.parse_args()
    root, inputs = args.root.resolve(), {}
    base = root / CAMPAIGN
    output = base / "audit/analysis.json"
    require(not output.exists(), "Refusing to overwrite existing analysis")
    f, h = load_helpers(root, inputs)
    f.record_input(root, base / "plan.json", inputs)
    plan = read(base / "plan.json")
    require(plan["version"] == "wide-movement-diagnostic-01" and plan["sourceIdentity"] == SOURCE, "Unexpected campaign/source")
    require(tuple(plan["models"]) == MODELS and tuple(plan["conditions"]) == CONDITIONS, "Unexpected model/condition set")
    require(plan["firstSeed"] == 1109849 and plan["seedCount"] == 512, "Frozen seed interval changed")
    require(plan["physicalRecipe"] == RECIPE and plan["evaluationRewardMode"] == "linear-radius", "Frozen recipe changed")
    require(plan["diagnosticOnly"] is True and all(plan[key] is False for key in
            ("masteryAccepted", "automaticPromotion", "finalSeedsConsumed")), "Diagnostic/final-seed declaration mismatch")
    seeds = list(range(plan["firstSeed"], plan["firstSeed"] + plan["seedCount"]))
    allocation = validate_provenance(f, root, base, plan, inputs)
    identities = f.verify_model_identities(root, plan, inputs)
    fixture, descriptors, fixture_summary = validate_fixture(f, root, base, plan, seeds, allocation, inputs)
    runs = {(model, condition): validate_run(f, h, root, base / "evaluation" / model / condition,
            model, condition, identities[model], seeds, descriptors, fixture, inputs)
            for model in MODELS for condition in CONDITIONS}
    keys, clusters = {}, {}
    negative = dict(resetPairs=len(seeds), identicalFirstActions=0, identicalPhysicalEpisodes=0, identicalLegalLandings=0)
    for seed in seeds:
        keys[seed] = f.physical_key(runs[INITIAL, "A"][2][seed]["observation"])
        clusters.setdefault(keys[seed], []).append(seed)
        for model in MODELS:
            for condition in CONDITIONS:
                require(f.physical_key(runs[model, condition][2][seed]["observation"]) == keys[seed], "Physical observation pairing failed")
        a, b = runs[INITIAL, "A"], runs[INITIAL, "B"]
        require(np.array_equal(a[2][seed]["physical"], b[2][seed]["physical"]), "Initializer action negative control failed")
        require({k:v for k,v in a[0][seed].items() if k != "reward"} == {k:v for k,v in b[0][seed].items() if k != "reward"}, "Initializer episode negative control failed")
        negative["identicalFirstActions"] += 1
        negative["identicalPhysicalEpisodes"] += 1
        if a[1][seed]["legalLanding"]:
            require(np.array_equal(h.landing(a[1][seed]), h.landing(b[1][seed])), "Initializer landing negative control failed")
            negative["identicalLegalLandings"] += 1
    groups = {"all": seeds}
    for task in DRILLS:
        groups[f"drill/{task}"] = [seed for seed in seeds if descriptors[seed]["task"] == task]
    for player in range(4):
        groups[f"player/{player}"] = [seed for seed in seeds if descriptors[seed]["player"] == player]
    for direction in DIRECTIONS:
        groups[f"axis/{direction}"] = [seed for seed in seeds if descriptors[seed]["direction"] == direction]
    for cm in (25, 50, 75, 100):
        groups[f"nominal-shift/{cm}cm"] = [seed for seed in seeds if descriptors[seed]["centimetres"] == cm]
    for label, challenge in (("familiar", False), ("axis-challenge", True)):
        groups[f"schedule/{label}"] = [seed for seed in seeds if descriptors[seed]["challenge"] is challenge]
    groups["nominal-shift/0cm-familiar-rally"] = [seed for seed in seeds if descriptors[seed]["range"] == 0]
    for label, side in (("left", True), ("right", False)):
        groups[f"serve/{label}"] = [seed for seed in seeds if descriptors[seed]["task"] == DRILLS[0] and descriptors[seed]["serveFromLeft"] is side]
    groups = {key:value for key,value in groups.items() if value}
    summaries, causal, changes, matrices, contacts, cluster_causal = {}, {}, {}, {}, {}, {}
    for group, selected in groups.items():
        summaries[group], causal[group], matrices[group], contacts[group], cluster_causal[group] = {}, {}, {}, {}, {}
        gains = {}
        for model in MODELS:
            summaries[group][model] = {condition:h.metrics([runs[model, condition][1][seed] for seed in selected]) for condition in CONDITIONS}
            causal[group][model], gains[model] = h.causal([runs[model,"A"][1][seed] for seed in selected], [runs[model,"B"][1][seed] for seed in selected])
            cluster_causal[group][model] = f.unique_cluster_ci(h, gains[model], selected, keys)
            matrices[group][model] = f.target_matrix(h, runs, model, selected)
            contacts[group][model] = {condition:telemetry(f, [runs[model,condition][0][seed] for seed in selected]) for condition in CONDITIONS}
        require(np.all(gains[INITIAL] == 0), "Target-blind assignment gain did not cancel")
        changes[group] = {"assignmentGainResetWeighted": h.ci(gains[CANDIDATE]-gains[INITIAL]),
                          "assignmentGainUniqueClusterWeighted": f.unique_cluster_ci(h, gains[CANDIDATE]-gains[INITIAL], selected, keys),
                          "conditions": {condition:h.paired_changes_for([runs[INITIAL,condition][1][seed] for seed in selected], [runs[CANDIDATE,condition][1][seed] for seed in selected]) for condition in CONDITIONS},
                          "telemetry":{condition:paired_telemetry(h, [runs[INITIAL,condition][0][seed] for seed in selected], [runs[CANDIDATE,condition][0][seed] for seed in selected]) for condition in CONDITIONS}}
    # Joint cells stay descriptive, avoiding hundreds of misleading tiny-cell CIs.
    joint = []
    for task in DRILLS[2:]:
        for direction in DIRECTIONS:
            for cm in (25,50,75,100):
                for player in range(4):
                    selected = [seed for seed in seeds if (descriptors[seed]["task"], descriptors[seed]["direction"], descriptors[seed]["centimetres"], descriptors[seed]["player"]) == (task,direction,cm,player)]
                    counts = {model:{condition:compact([runs[model,condition][0][seed] for seed in selected], [runs[model,condition][1][seed] for seed in selected]) for condition in CONDITIONS} for model in MODELS}
                    joint.append(dict(drill=task, direction=direction, nominalShiftCm=cm, player=player,
                                      attempts=len(selected), uniqueObservationClusters=len({keys[seed] for seed in selected}), counts=counts,
                                      pairedCandidateMinusInitializer={condition:{key:(counts[CANDIDATE][condition][key]-counts[INITIAL][condition][key])/len(selected) if selected else None for key in ("legal","targets","acceptedContacts")} for condition in CONDITIONS}))
    result = {"status":"complete_wide_movement_diagnostic", "diagnosticOnly":True, "firstSeed":seeds[0], "seedCount":len(seeds),
              "models":list(MODELS), "conditions":list(CONDITIONS), "modelIdentities":identities, "sourceIdentity":SOURCE,
              "physicalRecipe":RECIPE, "newlyEvaluatedModels":list(MODELS), "attemptsPerModel":len(seeds)*2,
              "inputSha256":inputs, "analysisScriptSha256":sha(Path(__file__)), "fixture":fixture_summary,
              "negativeControl":negative, "summaries":summaries, "causalResetWeighted":causal,
              "causalUniqueClusterWeighted":cluster_causal, "pairedCandidateMinusInitializer":changes,
              "targetConfusionMatrices":matrices, "actualContactAndMovementTelemetry":contacts,
              "descriptiveJointChallengeCells":joint,
              "physicalObservationClusters":{"resetPairs":len(seeds), "uniqueClusters":len(clusters),
                  "duplicateResetInstancesBeyondUnique":len(seeds)-len(clusters),
                  "comparison":"Exact numeric float32 equality of first124 observation features; no claim of hidden-state identity or novelty versus training",
                  "clusters":[{"fingerprintSha256":hashlib.sha256(np.asarray(key,dtype="<f4").tobytes()).hexdigest(), "seeds":members, "resetCount":len(members)} for key,members in clusters.items()]},
              "bootstrap":{"seed":h.BOOTSTRAP_SEED,"replicates":h.BOOTSTRAP_DRAWS,
                  "resetWeighted":"Paired base-reset resampling retains model/instruction correspondence; repeat reset observations retain their schedule weight.",
                  "uniqueClusterWeighted":"Average paired gains within each exact observation cluster, then equally weight/resample whole unique clusters.",
                  "coverage":"Pointwise95% intervals, not simultaneous bounds. Conditional landing projection includes only reset pairs where both instructions landed legally."},
              "targetMatrixMeaning":"Requested A/B rows, mutually exclusive actual legal landings in A, B, outside both, or no legal landing. Serve A/B is shallower/deeper; returns A/B is canonical left/right.",
              "movementTelemetryMeaning":"All movement attempts contribute measured planar root path until accepted face contact or termination. Net contact displacement and ball position/height statistics require actual accepted contact. Nonmovement telemetry is unmeasured, not zero movement.",
              "promoted":False,"masteryAccepted":False,"automaticPromotion":False,"finalSeedsConsumed":False,
              "limitations":[
                  "This predeclared diagnostic has no automatic mastery or promotion rule. It retains every scheduled attempt, including misses and sparse cells.",
                  "Nominal25-100cm shifts are reset locations relative to the paddle; arm reach may suffice and measured root motion need not equal the nominal shift.",
                  "Zero-tick fixture checks establish initial geometry/observation consistency, not flight timing or physical return feasibility.",
                  "Rally-bounce is a feed label after volley eligibility is established. Actual contact flags distinguish volleys from bounced rally contacts; no-contact false flags are not groundstrokes.",
                  "Required-bounce receiving is evaluated separately and accepted contacts require a recorded incoming serve bounce.",
                  "Sparse joint cells have counts and descriptive differences only. Marginal direction/distance performance can conceal interactions with drill/player.",
                  "Exact observation duplicates are clustered, but unique observations can be near duplicates or hide different simulator states.",
                  "One training lineage and this bounded development reset recipe do not establish generalization to realistic full-court feeds, motion timing variation, paired decisions, or2v2.",
                  "Final evaluation seeds remain unused. Fresh seed IDs alone do not establish novel situations."]}
    for relative, expected in inputs.items():
        require(sha(f.inside(root, relative)) == expected, f"Input changed during analysis: {relative}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"analysis":str(output),"diagnosticOnly":True,"uniqueObservationClusters":len(clusters),
                      "candidateAssignmentGain":causal["all"][CANDIDATE]["assignmentGain"],
                      "promoted":False,"masteryAccepted":False},indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
