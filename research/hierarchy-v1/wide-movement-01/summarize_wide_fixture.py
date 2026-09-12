"""Summarize eight reset-only wide movement fixture batches, without rollouts.

Reads <base>/plan.json and <base>/fixture/wide-fixture-{0000..0448}.json.
The sole output is exclusive <base>/fixture-summary.json. No policy is loaded.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

FIRST, COUNT = 1109849, 512
SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
RUN = "artifacts/hierarchy-v1/wide-movement-fixture-01"
CONTRACT = "execution-v1-136obs-16continuous-release"
WIDTH, LENGTH, KITCHEN = 3.048, 6.7056, 2.1336
DIRECTIONS = {3: "left", 5: "right", 1: "shallow", 7: "deep"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(values, length=None):
    return isinstance(values, list) and (length is None or len(values) == length) and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def close(left, right, tolerance=2e-5):
    return len(left) == len(right) and all(abs(a - b) <= tolerance for a, b in zip(left, right))


def fingerprint(observation):
    converted = [struct.unpack("<f", struct.pack("<f", value))[0] for value in observation]
    # Signed zero is not physical novelty.
    packed = struct.pack("<124f", *(0.0 if v == 0 else v for v in converted))
    return hashlib.sha256(packed).hexdigest()


def key(row):
    if row["challenge"]:
        return f"{row['task']}/{row['direction']}/{row['centimetres']}cm/player-{row['player']}"
    return f"{row['task']}/familiar/player-{row['player']}/left-{str(row['serveFromLeft'])}"


def expected_descriptor(index):
    block = index // 4 % 16
    task = "stationary-serve" if block < 2 else "receive-feed" if block < 4 else "rally-air-feed" if block < 6 or 8 <= block < 12 else "rally-bounce-feed"
    challenge = block >= 8
    range_value = 0.0 if block >= 4 else -1.0
    if challenge:
        range_value = .25 * (1 + block % 4) * .25
    return {"index": index, "seed": FIRST + index, "player": index % 4, "task": task,
            "pattern": "axes" if challenge else "court", "range": range_value,
            "challenge": challenge, "centimetres": round(400 * range_value) if challenge else 0,
            "serveFromLeft": block == 1, "difficulty": 1.0 if block < 2 else .25 if block == 3 else 0.0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--base", type=Path, help="Defaults to ROOT/artifacts/hierarchy-v1/wide-movement-fixture-01")
    args = parser.parse_args()
    root = args.root.resolve()
    base = args.base.resolve() if args.base else root / RUN
    output = base / "fixture-summary.json"
    require(not output.exists(), f"Refusing to overwrite {output}")
    plan_path = base / "plan.json"
    plan = read(plan_path)
    require(plan["version"] == "wide-movement-diagnostic-01", "Unexpected plan version")
    require(plan["firstSeed"] == FIRST and plan["seedCount"] == COUNT, "Plan seed allocation mismatch")
    require(plan["sourceIdentity"] == SOURCE, "Plan source mismatch")
    recipe = {"task": "movement-maintenance", "maximumReturnDifficulty": .25, "movementRange": .25,
              "movementPattern": "axes", "movementRehearsalRange": 0, "movementRecoveryMix": False,
              "interleavedRecovery": False, "movementTiming": 0, "movementStartVariation": 0,
              "movementPositionReward": 0, "fixedServeSides": "both"}
    require(plan["physicalRecipe"] == recipe, "Frozen physical recipe differs from this fixture")
    require(plan["fixture"]["batchSize"] == 64 and plan["fixture"]["batchOrdinals"] == list(range(0, COUNT, 64)), "Plan batch contract mismatch")
    require(plan["diagnosticOnly"] is True and plan["conditions"] == ["A", "B"] and plan["evaluationRewardMode"] == "linear-radius", "Plan diagnostic/goal contract mismatch")
    require(all(plan[k] is False for k in ("finalSeedsConsumed", "masteryAccepted", "automaticPromotion")), "Invalid plan acceptance/final-seed declaration")
    inputs = {str(plan_path): sha(plan_path)}
    template = base / "fixture-template.cs"
    require(sha(template) == plan["fixture"]["templateSha256"], "Frozen fixture template changed")
    inputs[str(template)] = sha(template)
    script_manifest_path = base / "script-hashes.json"
    scripts = read(script_manifest_path)
    require(all(f"wide-fixture-{start:04d}.cs" in scripts for start in range(0, COUNT, 64)), "Frozen batch script manifest is incomplete")
    require(scripts["wide-fixture-0000.cs"] == plan["fixture"]["templateSha256"], "First batch script differs from frozen template")
    inputs[str(script_manifest_path)] = sha(script_manifest_path)
    revision_path = base / "fixture-script-revision-01.json"
    revision = read(revision_path)
    require(revision["runtimeSourceChanged"] is False and revision["previousResetOutputs"] == 0 and revision["originalScriptsPreserved"] is True,
            "Fixture script revision changes the recorded reset/source contract")
    require(set(revision["files"]) == {f"wide-fixture-v2-{start:04d}.cs" for start in range(0, COUNT, 64)}, "Corrected script revision is incomplete")
    for start in range(0, COUNT, 64):
        corrected = revision["files"][f"wide-fixture-v2-{start:04d}.cs"]
        original = f"wide-fixture-{start:04d}.cs"
        require(corrected["original"] == original and corrected["originalSha256"] == scripts[original], "Corrected script loses original provenance")
        require(len(corrected["sha256"]) == 64 and all(c in "0123456789abcdef" for c in corrected["sha256"]), "Invalid corrected script hash")
    inputs[str(revision_path)] = sha(revision_path)
    fixture_manifest_path = base / "fixture-hashes.json"
    fixture_hashes = read(fixture_manifest_path)
    require(set(fixture_hashes) == {f"wide-fixture-{start:04d}.json" for start in range(0, COUNT, 64)}, "Frozen reset output manifest is incomplete")
    inputs[str(fixture_manifest_path)] = sha(fixture_manifest_path)
    batches, rows = [], {}
    violations = []

    def check(ok, code, index=None, detail=None, blocking=True):
        if not ok:
            violations.append({"code": code, "index": index, "seed": FIRST + index if index is not None else None,
                               "detail": detail, "blocking": blocking})

    planned = None
    identity = None
    for start in range(0, COUNT, 64):
        path = base / "fixture" / f"wide-fixture-{start:04d}.json"
        batch = read(path)
        inputs[str(path)] = sha(path)
        require(inputs[str(path)] == fixture_hashes[path.name], f"{path}: frozen reset output hash mismatch")
        require(batch["status"] == "reset_fixture_only" and batch["firstSeed"] == FIRST and batch["seedCount"] == COUNT and batch["reservation"] == RUN,
                f"{path}: fixture identity mismatch")
        require(batch["inspectFirstOrdinal"] == start and batch["inspectCount"] == 64 and len(batch["rows"]) == 64, f"{path}: incomplete batch")
        found_identity = {k: batch[k] for k in ("sourceIdentity", "sourceRecordHash", "ledgerHash", "unityVersion", "loadedAssembly")}
        require(found_identity["sourceIdentity"] == SOURCE, f"{path}: wrong source")
        if identity is None:
            identity = found_identity
        require(found_identity == identity, f"{path}: source/ledger/runtime changed between batches")
        for k in ("policyActions", "physicsTicks", "rewardsCollected"):
            check(batch[k] == 0, "batch_not_reset_only", detail={"batch": start, "field": k, "value": batch[k]})
        for k in ("modelsLoaded", "physicalReachabilityProven", "legalReturnAbilityProven", "promoted", "finalSeedsConsumed"):
            check(batch[k] is False, "batch_invalid_claim", detail={"batch": start, "field": k})
        if planned is None:
            planned = batch["planned"]
        require(batch["planned"] == planned, f"{path}: planned reset descriptors differ between batches")
        require(len(planned) == COUNT, "Expected complete schedule in each batch")
        require([r["index"] for r in batch["rows"]] == list(range(start, start + 64)), f"{path}: wrong physical ordinals")
        for row in batch["rows"]:
            require(row["index"] not in rows, f"Duplicate physical ordinal {row['index']}")
            rows[row["index"]] = row
        batches.append(batch)
    require(sorted(rows) == list(range(COUNT)), "Incomplete physical reset coverage")
    require([r["index"] for r in planned] == list(range(COUNT)), "Planned ordinal mismatch")
    source_path = root / "artifacts/hierarchy-v1/smooth-distance-01/source-records.json"
    require(sha(source_path) == identity["sourceRecordHash"] and read(source_path)["sourceIdentity"] == SOURCE, "Fixture source manifest mismatch")
    inputs[str(source_path)] = sha(source_path)
    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    ledger = read(ledger_path)
    require(sha(ledger_path) == identity["ledgerHash"], "Ledger changed since fixture; use the frozen matching ledger snapshot explicitly if archived")
    inputs[str(ledger_path)] = sha(ledger_path)
    require(ledger["version"] == "player-v3-seed-ledger-1" and ledger["finalSeedsConsumed"] == [], "Ledger schema/final usage mismatch")
    matches = [r for r in ledger["developmentBlocks"] if r["firstSeed"] == FIRST and r["count"] == COUNT and r.get("run") == RUN]
    require(len(matches) == 1, "Missing exact fixture development reservation")
    for field in ("sourceRecordHash", "ledgerHash"):
        if field in plan:
            require(plan[field] == identity[field], f"Plan {field} differs from fixture")

    coverage = Counter()
    shift_cells = Counter()
    task_counts = Counter()
    unique_groups = defaultdict(list)
    first_configuration = None
    geometry = {"initialBallOutsideCourt": [], "nominalPointOutsideCourt": [], "nominalPointInsideKitchen": [], "initialOverlaps": []}
    for index in range(COUNT):
        p, row = planned[index], rows[index]
        expected = expected_descriptor(index)
        for name, value in expected.items():
            check(p.get(name) == value, "planned_descriptor_mismatch", index, {"field": name, "expected": value, "actual": p.get(name)})
        for name in ("index", "seed", "player", "task", "pattern", "range", "region", "direction", "centimetres", "challenge"):
            check(row.get(name) == p[name], "actual_descriptor_mismatch", index, {"field": name, "planned": p[name], "actual": row.get(name)})
        cell = key(p)
        coverage[cell] += 1
        task_counts[p["task"]] += 1
        if p["challenge"]:
            shift_cells[f"{p['task']}/{p['direction']}/{p['centimetres']}cm"] += 1
            check(DIRECTIONS.get(p["region"]) == p["direction"], "axis_direction_mismatch", index)
        check(row["actualTicks"] == 0 and row["worldSeconds"] == 0 and row["policiesAttached"] is False and row["outcomeMeasured"] is False,
              "physical_row_not_reset_only", index)
        check(row["rejectedSurfaces"] == [], "unexpected_reset_rejections", index, row["rejectedSurfaces"])
        vectors = {name: length for name, length in (("learnerRoot", 3), ("paddleFace", 3), ("ballPosition", 3), ("ballVelocity", 3), ("ballSpin", 3), ("gravity", 3), ("physicalObservation124", 124))}
        good_vectors = True
        for name, length in vectors.items():
            valid = finite(row.get(name), length)
            check(valid, "invalid_vector", index, name)
            good_vectors &= valid
        check(isinstance(row["ballMass"], (float, int)) and math.isfinite(row["ballMass"]) and row["ballMass"] > 0,
              "invalid_ball_mass", index)
        check(isinstance(row["ballDiameter"], (float, int)) and math.isfinite(row["ballDiameter"]) and row["ballDiameter"] > 0,
              "invalid_ball_diameter", index)
        check(math.isfinite(row["physicsDt"]) and abs(row["physicsDt"] - 1/240) < 1e-8, "wrong_physics_timestep", index)
        check(row["ballHeld"] is False, "unexpected_hand_held_ball", index)
        check(row["stationarySupport"] is (p["task"] == "stationary-serve"), "support_mode_mismatch", index)
        players = row["players"]
        check(len(players) == 4 and [r["seat"] for r in players] == list(range(4)), "player_identity_mismatch", index)
        for player in players:
            check(finite(player["root"], 3) and finite(player["paddlePosition"], 3) and finite(player["paddleRotation"], 4), "invalid_player_pose", index, player["seat"])
        if not good_vectors:
            continue
        check(close(players[p["player"]]["root"], row["learnerRoot"]), "learner_root_mismatch", index)
        obs_hash = fingerprint(row["physicalObservation124"])
        for group in ("all", f"drill/{p['task']}", "challenge" if p["challenge"] else "familiar", cell):
            unique_groups[group].append(obs_hash)
        x, y, z = row["ballPosition"]
        radius = row["ballDiameter"] / 2
        check(y >= radius - 2e-5, "ball_intersects_floor_plane", index, {"ballY": y, "radius": radius})
        inbound = abs(x) <= WIDTH + 2e-5 and abs(z) <= LENGTH + 2e-5
        if not inbound:
            fact = {"index": index, "seed": p["seed"], "task": p["task"], "position": row["ballPosition"], "fixedServe": p["task"] == "stationary-serve"}
            geometry["initialBallOutsideCourt"].append(fact)
            # Initial position alone cannot determine whether the later flight,
            # bounce or return is legal. Boundary location is descriptive.
        overlaps = row["overlaps"]
        if overlaps:
            fact = {"index": index, "seed": p["seed"], "task": p["task"], "stationarySupport": row["stationarySupport"], "overlaps": overlaps}
            geometry["initialOverlaps"].append(fact)
            check(False, "initial_collider_overlap", index, fact)
        check(close(row["ballSpin"], [0, 0, 0]), "unexpected_initial_spin", index)
        if p["range"] >= 0:
            check(finite(row["nominalPoint"], 3) and finite(row["canonicalNominalShift"], 2), "invalid_nominal_geometry", index)
            if finite(row["nominalPoint"], 3) and finite(row["canonicalNominalShift"], 2):
                sign = 1 if p["player"] < 2 else -1
                nominal, face = row["nominalPoint"], row["paddleFace"]
                actual_shift = [(nominal[0]-face[0])*sign, (nominal[2]-face[2])*sign]
                distance = math.hypot(*actual_shift)
                check(close(actual_shift, row["canonicalNominalShift"]) and math.isfinite(row["nominalDistanceMetres"]) and abs(distance-row["nominalDistanceMetres"]) < 2e-5,
                      "measured_nominal_shift_mismatch", index)
                expected_distance = p["centimetres"] / 100
                direction = p["direction"]
                desired = {"left": [-expected_distance, 0], "right": [expected_distance, 0], "shallow": [0, expected_distance], "deep": [0, -expected_distance]}.get(direction, [0, 0])
                check(close(actual_shift, desired) and abs(distance-expected_distance) < 2e-5, "requested_nominal_axis_shift_mismatch", index)
                nominal_in = abs(nominal[0]) <= WIDTH and abs(nominal[2]) <= LENGTH
                kitchen = abs(nominal[2]) <= KITCHEN
                check(row["nominalPointInCourt"] is nominal_in and row["nominalPointInKitchen"] is kitchen, "nominal_domain_flag_mismatch", index)
                if not nominal_in:
                    geometry["nominalPointOutsideCourt"].append({"index": index, "seed": p["seed"], "point": nominal, "direction": direction, "centimetres": p["centimetres"]})
                if kitchen:
                    geometry["nominalPointInsideKitchen"].append({"index": index, "seed": p["seed"], "point": nominal})
        else:
            check(all(row[n] is None for n in ("nominalPoint", "canonicalNominalShift", "nominalDistanceMetres", "nominalPointInCourt", "nominalPointInKitchen")), "unexpected_nonmovement_nominal_point", index)
        goals = row["instructions"]
        check(len(goals) == 2 and [g["condition"] for g in goals] == ["A", "B"], "goal_condition_mismatch", index)
        for goal in goals:
            encoded = goal["observation136"]
            check(finite(encoded, 136), "invalid_goal_observation", index, goal["condition"])
            if not finite(encoded, 136):
                continue
            target_x = (1.4 if p["serveFromLeft"] else -1.4) if p["task"] == "stationary-serve" else (-1.2 if goal["condition"] == "A" else 1.2)
            target_z = (3.3 if goal["condition"] == "A" else 5.4) if p["task"] == "stationary-serve" else 3.8
            check(close([goal["targetX"], goal["targetZ"], goal["radius"]], [target_x, target_z, 1]), "target_geometry_mismatch", index, goal["condition"])
            check(encoded[:124] == row["physicalObservation124"] and encoded[124:132] == [1, 0, 0, 0, 0, 0, 0, 0] and close(encoded[132:], [1, target_x/WIDTH, target_z/LENGTH, 1/3], 2e-6),
                  "goal_contract_mismatch", index, goal["condition"])
        rule = row["rule"]
        check(rule["phase"] == ("AwaitServe" if p["task"] == "stationary-serve" else "ServeFlight" if p["task"] == "receive-feed" else "Rally"), "unexpected_initial_rule_phase", index, rule)
        check(rule["CanVolley"] is (p["task"] in ("rally-air-feed", "rally-bounce-feed")), "wrong_initial_volley_eligibility", index)
        config = json.loads(row["configurationJson"])
        if first_configuration is None:
            first_configuration = config
        check(config == first_configuration, "physical_configuration_changed_between_resets", index)
        check(abs(config["BallMass"]-row["ballMass"]) < 2e-6 and abs(config["BallDiameter"]-row["ballDiameter"]) < 2e-6,
              "configuration_ball_mismatch", index)
        check(close(row["gravity"], [config["Gravity"][axis] for axis in ("x", "y", "z")]), "configuration_gravity_mismatch", index)

    expected_joint = [f"{task}/{direction}/{cm}cm/player-{player}" for task in ("rally-air-feed", "rally-bounce-feed") for direction in DIRECTIONS.values() for cm in (25, 50, 75, 100) for player in range(4)]
    missing_joint = sorted(k for k in expected_joint if not coverage[k])
    for batch in batches:
        check(dict(coverage) == batch["plannedCoverage"], "reported_planned_coverage_mismatch")
        observed = Counter(key(planned[r["index"]]) for r in batch["rows"])
        check(dict(observed) == batch["inspectedCoverage"], "reported_batch_coverage_mismatch", detail=batch["inspectFirstOrdinal"])
        check(missing_joint == sorted(batch["missingJointCells"]), "reported_missing_cells_mismatch")
    all_shifts = [f"{task}/{direction}/{cm}cm" for task in ("rally-air-feed", "rally-bounce-feed") for direction in DIRECTIONS.values() for cm in (25, 50, 75, 100)]
    unique = {group: {"resets": len(values), "uniquePhysicalObservations": len(set(values)), "largestMultiplicity": max(Counter(values).values())} for group, values in unique_groups.items()}
    expected_schedule = {"fixedServes": 64, "requiredBounceReceives": 64, "familiarAir": 64, "familiarBounce": 64, "axisAir": 128, "axisBounce": 128}
    actual_schedule = {"fixedServes": task_counts["stationary-serve"], "requiredBounceReceives": task_counts["receive-feed"],
                       "familiarAir": sum(r["task"] == "rally-air-feed" and not r["challenge"] for r in planned),
                       "familiarBounce": sum(r["task"] == "rally-bounce-feed" and not r["challenge"] for r in planned),
                       "axisAir": sum(r["task"] == "rally-air-feed" and r["challenge"] for r in planned),
                       "axisBounce": sum(r["task"] == "rally-bounce-feed" and r["challenge"] for r in planned)}
    check(actual_schedule == expected_schedule and all(plan["expectedSchedule"][k] == v for k, v in expected_schedule.items()), "physical_schedule_count_mismatch", detail=actual_schedule)
    blocking = [v for v in violations if v["blocking"]]
    result = {
        "status": "reset_fixture_valid" if not blocking else "reset_fixture_needs_review",
        "firstSeed": FIRST, "seedCount": COUNT, "batches": len(batches), "identity": identity, "contract": CONTRACT,
        "planSha256": inputs[str(plan_path)], "analysisScriptSha256": sha(Path(__file__)), "inputSha256": inputs,
        "fixtureScriptRevision": revision,
        "policyActions": sum(b["policyActions"] for b in batches), "physicsTicks": sum(b["physicsTicks"] for b in batches),
        "rewardsCollected": sum(b["rewardsCollected"] for b in batches), "outcomesMeasured": any(r["outcomeMeasured"] for r in rows.values()),
        "outcomeAllowed": not blocking,
        "outcomeAllowedMeaning": "Readiness for the planned frozen policy diagnostic, not evidence of a successful or physically reachable return",
        "resetOnlyReachabilityNotProven": True, "promoted": False, "masteryAccepted": False, "finalSeedsConsumed": False,
        "violations": violations, "blockingViolationCount": len(blocking), "geometry": geometry,
        "coverage": {"schedule": actual_schedule, "byTask": dict(task_counts), "shiftCells": {k: shift_cells[k] for k in all_shifts},
                     "jointCellsIncludingPlayer": {k: coverage[k] for k in expected_joint}, "missingJointCells": missing_joint,
                     "minimumShiftCellCount": min(shift_cells[k] for k in all_shifts), "maximumShiftCellCount": max(shift_cells[k] for k in all_shifts)},
        "physicalObservationUniqueness": unique,
        "existingEpisodeTelemetry": {"travelBeforeContact[player]": "planar root path length before first accepted contact (or through a miss)",
                                     "contactDisplacement": "net planar root displacement at accepted contact", "contactDistanceFromStart": "planar ball distance from initial root at accepted contact",
                                     "faceContactBallHeight": "ball height at accepted contact", "contactPositionXYZ": "not present in current episode telemetry"},
        "limitations": ["Reset geometry only: no ball flight, bounce, action, contact, reward, or reachability was tested.",
                        "Nominal ball points inside the kitchen do not alone determine player volley legality.",
                        "Initial ball centers outside the court are reported descriptively; flight and later bounce legality were not simulated.",
                        "Every initial collider overlap is reported and blocks readiness; stationary support does not silently excuse penetration.",
                        "Nominal points outside the court are reported for interpretation; they are reset design points, not guaranteed contact points.",
                        "Sparse or repeated cells do not establish skill reliability; unique counts use only the recorded124 observation features.",
                        "DoublesWorld.Dispose destroys geometry immediately, but local scene unloading can finish after each batch returns."],
    }
    for path, expected in inputs.items():
        require(sha(Path(path)) == expected, f"Input changed during summary: {path}")
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"summary": str(output), "status": result["status"], "violations": len(violations), "outcomeAllowed": result["outcomeAllowed"],
                      "resets": COUNT, "uniquePhysicalObservations": unique["all"]["uniquePhysicalObservations"], "missingJointCells": len(missing_joint),
                      "resetOnlyReachabilityNotProven": True}, indent=2))


if __name__ == "__main__":
    main()
