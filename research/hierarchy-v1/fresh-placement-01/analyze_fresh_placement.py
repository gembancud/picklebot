"""Audit newly evaluated placement resets without equating new seed IDs with novelty.

Consumes a frozen fresh-placement-01 plan and two newly evaluated frozen models.
The only output is an exclusive campaign/audit/analysis.json. Statistical helpers
are imported from the preserved analyzer; its fixed-seed row reader is never used.
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
CANDIDATE = "ExecutionV1SmoothContinuedFinal01"
MODELS = (INITIAL, CANDIDATE)
CONDITIONS = ("A", "B", "random")
FILES = ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "model-identity.json")
SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
CONTRACT = "execution-v1-136obs-16continuous-release"
HELPER = "research/hierarchy-v1/smooth-distance-01/analyze_smooth_distance.py"
HELPER_SHA256 = "69b627d8821a25fa249ff01ea4e070c47d26eb0221103981c62e4f06be4cf7e6"
CAMPAIGN = "artifacts/hierarchy-v1/fresh-placement-01"
DRILLS = ("stationary-serve", "receive-feed", "rally-air-feed", "rally-bounce-feed")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, relative):
    path = root / relative
    require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root), f"Path escapes repository: {relative}")
    return path


def record_input(root, path, inputs, expected=None):
    require(path.is_file(), f"Missing input: {path}")
    digest = sha(path)
    if expected is not None:
        require(isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected) and digest == expected,
                f"Frozen input hash mismatch: {path}")
    inputs[path.relative_to(root).as_posix()] = digest


def load_helper(root, inputs):
    path = inside(root, HELPER)
    record_input(root, path, inputs, HELPER_SHA256)
    spec = importlib.util.spec_from_file_location("preserved_placement_statistics", path)
    require(spec is not None and spec.loader is not None, "Cannot import statistical helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.BOOTSTRAP_SEED == 20260912 and module.BOOTSTRAP_DRAWS == 10000, "Statistical bootstrap protocol changed")
    return module


def read_rows(path, seeds):
    """This campaign's explicit seeds, not the helper's old fixed anchor."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    require(len(rows) == len(seeds), f"{path}: wrong completed count")
    require(all(type(row["seed"]) is int for row in rows), f"{path}: invalid seed type")
    indexed = {row["seed"]: row for row in rows}
    require(len(indexed) == len(seeds) and sorted(indexed) == seeds, f"{path}: duplicate, missing, or unexpected seeds")
    return indexed


def physical_key(observation):
    values = np.asarray(observation, dtype=np.float32)
    require(values.shape == (136,) and np.isfinite(values).all(), "Invalid policy observation for physical clustering")
    # Numeric equality of original float32 values; +0 and -0 represent the same
    # observation. Goal features are excluded, but player-visible rule state stays.
    return tuple(float(value) if value != 0 else 0.0 for value in values[:124])


def verify_model_identities(root, plan, inputs):
    import torch

    identities = plan["modelIdentities"]
    require(set(identities) == set(MODELS), "Unexpected model identity set")
    for model, identity in identities.items():
        require(identity["sourceIdentity"] == SOURCE and type(identity["step"]) is int, "Model runtime source/step mismatch")
        asset = inside(root, identity["assetPath"])
        checkpoint = inside(root, identity["checkpoint"])
        require(asset.resolve() == (root / f"Assets/Picklebot/PlayerLearning/Models/{model}.onnx").resolve(), "Wrong evaluation asset path")
        record_input(root, asset, inputs, identity["modelHash"])
        record_input(root, checkpoint, inputs, identity["checkpointHash"])
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        steps = list(state["global_step"].values())
        require(len(steps) == 1 and steps[0].numel() == 1 and steps[0].item() == identity["step"], "Checkpoint stored step mismatch")
        require(state["Policy"]["network_body._body_endoder.seq_layers.0.weight"].shape == (128, 136), "Checkpoint executor shape mismatch")
    require(identities[INITIAL]["step"] == 0 and identities[CANDIDATE]["step"] == 1048609, "Unexpected fixed model selection")
    return identities


def prior_observations(root, plan, inputs):
    frozen = plan["priorObservationInputs"]
    require(isinstance(frozen, dict) and frozen, "Prior observation hashes are required for novelty accounting")
    for relative, expected in frozen.items():
        record_input(root, inside(root, relative), inputs, expected)
    observed, total = set(), 0
    for relative in frozen:
        first = read(inside(root, relative))
        require(isinstance(first, dict) and first, "Prior first-decisions input is empty or malformed")
        for decision in first.values():
            observed.add(physical_key(decision["observation"]))
            total += 1
    if "expectedPriorUniqueObservations" in plan:
        require(len(observed) == plan["expectedPriorUniqueObservations"], "Prior unique-observation count changed")
    return observed, total


def validate_run(h, root, folder, model, condition, identity, seeds, inputs):
    for name in FILES:
        record_input(root, folder / name, inputs)
    actual_identity = read(folder / "model-identity.json")
    require(actual_identity["model"] == model, f"{folder}: sidecar model mismatch")
    for key in ("modelHash", "checkpointHash", "step", "sourceIdentity"):
        require(actual_identity[key] == identity[key], f"{folder}: model sidecar mismatch: {key}")
    episodes = read_rows(folder / "episodes.jsonl", seeds)
    goals = read_rows(folder / "execution-goals.jsonl", seeds)
    raw = read(folder / "first-decisions.json")
    first = {int(key): value for key, value in raw.items()}
    require(len(raw) == len(first) == len(seeds) and sorted(first) == seeds, f"{folder}: first-decision seed mismatch")
    report = read(folder / "report.json")
    require(report["status"] == "seed_budget_complete" and not report.get("failure"), f"{folder}: incomplete/failed evaluation")
    require(report["firstSeed"] == seeds[0] and report["seedCount"] == len(seeds)
            and report["nextSeedIndex"] == len(seeds) and report["completedEpisodes"] == len(seeds), f"{folder}: wrong reset budget")
    require(report["sourceIdentity"] == SOURCE and report["contract"] == CONTRACT and report["split"] == "development", f"{folder}: runtime contract mismatch")
    require(report["trainerConnected"] is False and report["task"] == "movement-maintenance", f"{folder}: wrong evaluation mode")
    require(report["movementRecoveryMix"] is True and report["interleavedRecovery"] is True
            and report["fixedServeSides"] == "both" and report["movementPattern"] == "lateral"
            and abs(report["movementRange"] - .025) < 1e-6
            and abs(report["movementRehearsalRange"] - .1) < 1e-6
            and abs(report["maximumReturnDifficulty"] - .25) < 1e-6
            and report["movementTiming"] == report["movementStartVariation"] == 0, f"{folder}: physical curriculum changed")
    for seed in seeds:
        ep, row, decision = episodes[seed], goals[seed], first[seed]
        label = f"{model}/{condition}/{seed}"
        require(ep["task"] in DRILLS and ep["player"] in range(4), f"{label}: unexpected drill/player")
        require(ep["player"] == row["player"] == decision["player"] and decision["seed"] == seed, f"{label}: private identity mismatch")
        obs = np.asarray(decision["observation"], dtype=np.float32)
        physical_key(obs)
        action = np.asarray(decision["physical"], dtype=float)
        require(action.shape == (18,) and np.isfinite(action).all(), f"{label}: invalid action")
        require(np.array_equal(obs[124:132], [1, 0, 0, 0, 0, 0, 0, 0]), f"{label}: unexpected movement goal/intent")
        require(row["contract"] == CONTRACT and row["assigned"] is True and row["rewardMode"] == "linear-radius", f"{label}: wrong goal/reward contract")
        require(ep["outcome"] == row["outcome"] and ep["outcome"] not in ("exception", "infeasible"), f"{label}: outcome mismatch or simulator failure")
        legal = ep["outcome"] in ("legal_return", "legal_serve")
        require(row["legalLanding"] is legal and row["hasLanding"] is legal, f"{label}: legal landing mismatch")
        for key in ("faceContact", "netCrossed", "incomingServeLanded", "contactWasVolley", "serveAccepted"):
            require(type(ep[key]) is bool, f"{label}: missing actual contact indicator: {key}")
        require(not legal or (ep["faceContact"] and ep["netCrossed"]), f"{label}: legal outcome without accepted contact/net crossing")
        serve = ep["task"] == "stationary-serve"
        receive = ep["task"] == "receive-feed"
        rally = ep["task"] in ("rally-air-feed", "rally-bounce-feed")
        expected_phase = [1, 0, 0, 0, 0] if serve else [0, 1, 0, 0, 0] if receive else [0, 0, 0, 1, 0]
        require(np.array_equal(obs[39:44], expected_phase), f"{label}: initial rule phase mismatch")
        if serve:
            require(obs[44] == 1 and (not legal or (ep["outcome"] == "legal_serve" and ep["serveAccepted"])), f"{label}: serve rule evidence mismatch")
        if receive:
            require(obs[45] == 1 and obs[48] == 0, f"{label}: required-bounce feed did not start before its bounce")
            require(not ep["faceContact"] or ep["incomingServeLanded"], f"{label}: accepted receive contact lacks recorded required bounce")
        if ep["contactWasVolley"]:
            require(rally and ep["faceContact"], f"{label}: volley marker without accepted rally contact")
        # Rally feed labels do not force the agent to volley or wait for a bounce.
        # Count the contact actually taken; never call a no-contact false flag a groundstroke.
        radius = 1.5 if condition == "random" else 1.0
        require(abs(row["radius"] - radius) < 1e-6, f"{label}: target radius changed")
        require(np.isfinite([row[key] for key in ("targetX", "targetZ", "radius", "distance", "bonus", "landingX", "landingZ")]).all(), f"{label}: nonfinite evidence")
        require(np.allclose(obs[132:136], [1, row["targetX"] / 3.048, row["targetZ"] / 6.7056, radius / 3], atol=2e-6, rtol=0), f"{label}: target encoding mismatch")
        sign = 1 if ep["serveFromLeft"] else -1
        if condition == "random":
            require(row["targetLayout"] == "random" and abs(row["targetX"]) <= 2.3 + 2e-6
                    and 1 - 2e-6 <= row["targetZ"] <= 5.8 + 2e-6, f"{label}: random target geometry mismatch")
            if serve:
                require(.5 - 2e-6 <= sign * row["targetX"] <= 2.3 + 2e-6 and row["targetZ"] >= 2.8 - 2e-6, f"{label}: target outside serve box")
        else:
            expected = [sign * 1.4, 3.3 if condition == "A" else 5.4] if serve else [-1.2 if condition == "A" else 1.2, 3.8]
            require(row["targetLayout"] == "two-regions" and np.allclose(h.target(row), expected, atol=2e-6, rtol=0), f"{label}: wrong requested region")
        if legal:
            require(row["distance"] >= 0 and abs(np.linalg.norm(h.landing(row) - h.target(row)) - row["distance"]) < 2e-5, f"{label}: landing distance mismatch")
        else:
            require(row["distance"] == -1 and row["landingX"] == row["landingZ"] == 0, f"{label}: invalid landing sentinel")
        require(type(row["targetHit"]) is bool and row["targetHit"] == h.hit(row, row), f"{label}: target-hit mismatch")
        expected_bonus = .25 * max(0, 1 - row["distance"] / radius) if legal else 0
        require(0 <= row["bonus"] <= .25 and abs(row["bonus"] - expected_bonus) < 2e-5, f"{label}: evaluation bonus mismatch")
    return episodes, goals, first, report


def contact_counts(episodes):
    receiving = [ep for ep in episodes if ep["task"] == "receive-feed"]
    rally = [ep for ep in episodes if ep["task"] in ("rally-air-feed", "rally-bounce-feed")]
    volley = [ep for ep in rally if ep["faceContact"] and ep["contactWasVolley"]]
    bounced = [ep for ep in rally if ep["faceContact"] and not ep["contactWasVolley"]]
    legal = lambda ep: ep["outcome"] in ("legal_return", "legal_serve")
    return {
        "attempts": len(episodes), "requiredBounceReceiveAttempts": len(receiving),
        "requiredBounceObserved": sum(ep["incomingServeLanded"] for ep in receiving),
        "acceptedRequiredBounceContacts": sum(ep["faceContact"] and ep["incomingServeLanded"] for ep in receiving),
        "legalRequiredBounceReturns": sum(legal(ep) for ep in receiving),
        "rallyAttempts": len(rally), "acceptedVolleyContacts": len(volley), "legalVolleyReturns": sum(map(legal, volley)),
        "acceptedRallyContactsAfterBounce": len(bounced), "legalRallyReturnsAfterBounce": sum(map(legal, bounced)),
        "rallyAttemptsWithoutAcceptedFaceContact": sum(not ep["faceContact"] for ep in rally),
    }


def target_matrix(h, runs, model, seeds):
    matrix = {}
    for condition in ("A", "B"):
        cells = dict(attempts=len(seeds), legalInA=0, legalInB=0, legalOutsideBoth=0, illegalOrNoLegalLanding=0)
        for seed in seeds:
            row = runs[model, condition][1][seed]
            a, b = runs[model, "A"][1][seed], runs[model, "B"][1][seed]
            hit_a, hit_b = h.hit(row, a), h.hit(row, b)
            require(not (hit_a and hit_b), "A/B target matrix regions overlap")
            key = "illegalOrNoLegalLanding" if not row["legalLanding"] else "legalInA" if hit_a else "legalInB" if hit_b else "legalOutsideBoth"
            cells[key] += 1
        require(sum(value for key, value in cells.items() if key != "attempts") == len(seeds), "Target matrix denominator mismatch")
        matrix[condition] = cells
    return matrix


def unique_cluster_ci(h, values, seeds, keys):
    clustered = {}
    for seed, value in zip(seeds, values):
        clustered.setdefault(keys[seed], []).append(float(value))
    means = [float(np.mean(group)) for group in clustered.values()]
    result = h.ci(means)
    return {"mean": result["mean"], "ci95": result["ci95"], "resetPairs": len(seeds),
            "uniquePhysicalObservationClusters": len(means),
            "clusterMultiplicityMin": min(map(len, clustered.values())),
            "clusterMultiplicityMax": max(map(len, clustered.values())),
            "bootstrapReplicates": h.BOOTSTRAP_DRAWS,
            "weighting": "Mean gain within each exact float32 124-observation cluster, then equal weight per unique cluster; resample whole clusters."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    args = parser.parse_args()
    root = args.root.resolve()
    campaign, inputs = root / CAMPAIGN, {}
    output = campaign / "audit/analysis.json"
    require(not output.exists(), f"Refusing to overwrite {output}")
    plan_path = campaign / "plan.json"
    record_input(root, plan_path, inputs)
    plan = read(plan_path)
    require(plan["version"] == "fresh-placement-screen-01" and plan["sourceIdentity"] == SOURCE, "Unexpected campaign/source")
    require(tuple(plan["models"]) == MODELS and tuple(plan["conditions"]) == CONDITIONS, "Unexpected model/condition order")
    require(type(plan["firstSeed"]) is int and plan["firstSeed"] >= 0 and plan["seedCount"] == 256, "Invalid explicit reset interval")
    seeds = list(range(plan["firstSeed"], plan["firstSeed"] + plan["seedCount"]))
    require(plan["evaluationRewardMode"] == "linear-radius", "Wrong frozen evaluation reward")
    require(plan["finalSeedsConsumed"] is False and plan["masteryAccepted"] is False and plan["automaticPromotion"] is False, "Invalid acceptance/final-seed declaration")
    require(plan["screening"]["maximumPerDrillLegalDrop"] == .05
            and plan["screening"]["requireUniqueClusterGainCiLowerAboveZero"] is True, "Unexpected predeclared screen")
    h = load_helper(root, inputs)
    identities = verify_model_identities(root, plan, inputs)
    prior, prior_count = prior_observations(root, plan, inputs)
    runs = {(model, condition): validate_run(h, root, campaign / "evaluation" / model / condition,
            model, condition, identities[model], seeds, inputs) for model in MODELS for condition in CONDITIONS}
    keys, negative = {}, {"baseResets": len(seeds), "identicalFirstActions": 0,
                          "identicalPhysicalEpisodes": 0, "identicalLegalLandings": 0}
    base_episodes = runs[INITIAL, "A"][0]
    for seed in seeds:
        initial = runs[INITIAL, "A"]
        keys[seed] = physical_key(initial[2][seed]["observation"])
        for model in MODELS:
            for condition in CONDITIONS:
                ep, goals, first, _ = runs[model, condition]
                require(physical_key(first[seed]["observation"]) == keys[seed], f"{model}/{condition}/{seed}: initial physical observation mismatch")
                require(h.group_key(ep[seed]) == h.group_key(base_episodes[seed]), f"{model}/{condition}/{seed}: reset descriptor mismatch")
                reference_goal = runs[INITIAL, condition][1][seed]
                require(np.array_equal(h.target(goals[seed]), h.target(reference_goal)) and goals[seed]["radius"] == reference_goal["radius"], f"{model}/{condition}/{seed}: target changed across models")
        a, b = runs[INITIAL, "A"], runs[INITIAL, "B"]
        require(np.array_equal(a[2][seed]["physical"], b[2][seed]["physical"]), f"Initializer action negative control failed: {seed}")
        negative["identicalFirstActions"] += 1
        require({k: v for k, v in a[0][seed].items() if k != "reward"} == {k: v for k, v in b[0][seed].items() if k != "reward"}, f"Initializer physical negative control failed: {seed}")
        negative["identicalPhysicalEpisodes"] += 1
        if a[1][seed]["legalLanding"]:
            require(b[1][seed]["legalLanding"] and np.array_equal(h.landing(a[1][seed]), h.landing(b[1][seed])), f"Initializer landing negative control failed: {seed}")
            negative["identicalLegalLandings"] += 1
    unique = set(keys.values())
    novel = [seed for seed in seeds if keys[seed] not in prior]
    repeated = [seed for seed in seeds if keys[seed] in prior]
    prior_array = np.asarray(sorted(prior), dtype=np.float64)
    nearest = {key: float(np.max(np.abs(prior_array - np.asarray(key, dtype=np.float64)), axis=1).min()) for key in unique}
    nearest_rows = np.asarray([nearest[keys[seed]] for seed in seeds])
    grouping = {"all": seeds, "novelty/exact-novel": novel, "novelty/exact-repeated": repeated}
    require(set(ep["task"] for ep in base_episodes.values()) == set(DRILLS), "Fresh interval does not cover all four drills")
    for drill in DRILLS:
        grouping[f"drill/{drill}"] = [seed for seed in seeds if base_episodes[seed]["task"] == drill]
        for label, subset in (("exact-novel", novel), ("exact-repeated", repeated)):
            grouping[f"drill/{drill}/novelty/{label}"] = [seed for seed in subset if base_episodes[seed]["task"] == drill]
    for player in range(4):
        grouping[f"player/{player}"] = [seed for seed in seeds if base_episodes[seed]["player"] == player]
    for side in ("left", "right"):
        grouping[f"service/{side}"] = [seed for seed in seeds if base_episodes[seed]["task"] == "stationary-serve" and h.group_key(base_episodes[seed])[1] == side]
    for category in ("actual-movement", "central-or-familiar"):
        grouping[f"movement/{category}"] = [seed for seed in seeds if h.group_key(base_episodes[seed])[2] == category]
    grouping = {group: selected for group, selected in grouping.items() if selected}
    summaries, causal, changes, matrices, contacts, clustered = {}, {}, {}, {}, {}, {}
    for group, selected in grouping.items():
        summaries[group], causal[group], matrices[group], contacts[group], clustered[group] = {}, {}, {}, {}, {}
        gains = {}
        for model in MODELS:
            summaries[group][model] = {condition: h.metrics([runs[model, condition][1][seed] for seed in selected]) for condition in CONDITIONS}
            causal[group][model], gains[model] = h.causal([runs[model, "A"][1][seed] for seed in selected], [runs[model, "B"][1][seed] for seed in selected])
            clustered[group][model] = unique_cluster_ci(h, gains[model], selected, keys)
            matrices[group][model] = target_matrix(h, runs, model, selected)
            contacts[group][model] = {condition: contact_counts([runs[model, condition][0][seed] for seed in selected]) for condition in CONDITIONS}
        require(np.all(gains[INITIAL] == 0), f"Initializer assignment gain did not cancel: {group}")
        changes[group] = {"assignmentGainResetWeighted": h.ci(gains[CANDIDATE] - gains[INITIAL]),
                          "assignmentGainUniqueClusterWeighted": unique_cluster_ci(h, gains[CANDIDATE] - gains[INITIAL], selected, keys),
                          "conditions": {condition: h.paired_changes_for([runs[INITIAL, condition][1][seed] for seed in selected], [runs[CANDIDATE, condition][1][seed] for seed in selected]) for condition in CONDITIONS}}
    retention = [{"drill": drill, "condition": condition, **changes[f"drill/{drill}"]["conditions"][condition]["legalRateChange"]}
                 for drill in DRILLS for condition in CONDITIONS]
    tests = {"resetWeightedAssignmentGainCiLowerAboveZero": causal["all"][CANDIDATE]["assignmentGain"]["ci95"][0] > 0,
             "uniqueClusterWeightedAssignmentGainCiLowerAboveZero": clustered["all"][CANDIDATE]["ci95"][0] > 0,
             "bothRegionTargetRatesExceedInitializer": all(changes["all"]["conditions"][condition]["targetRateChange"]["mean"] > 0 for condition in ("A", "B")),
             "noDrillLegalDropGreaterThanFivePercentagePoints": all(item["mean"] >= -.05 - 1e-12 for item in retention)}
    cluster_members = {}
    for seed in seeds:
        cluster_members.setdefault(keys[seed], []).append(seed)
    novelty = {"comparison": "Exact numeric equality after float32 conversion of first-decision observation indices0..123; goals excluded",
               "priorRecordedObservations": prior_count, "priorUniquePhysicalObservations": len(prior),
               "currentResets": len(seeds), "currentUniquePhysicalObservations": len(unique),
               "exactNovelResets": len(novel), "exactRepeatedResets": len(repeated),
               "exactNovelUniqueObservations": len(unique - prior), "exactRepeatedUniqueObservations": len(unique & prior),
               "clusters": [{"fingerprintSha256": hashlib.sha256(np.asarray(key, dtype="<f4").tobytes()).hexdigest(),
                             "resetCount": len(members), "seeds": members, "exactNovel": key not in prior,
                             "nearestPriorMaxAbsDifference": nearest[key]} for key, members in cluster_members.items()],
               "byDrill": {drill: {"resets": len(grouping[f"drill/{drill}"]),
                                   "exactNovelResets": sum(keys[seed] not in prior for seed in grouping[f"drill/{drill}"]),
                                   "exactRepeatedResets": sum(keys[seed] in prior for seed in grouping[f"drill/{drill}"])} for drill in DRILLS},
               "nearestPriorMaximumAbsoluteNormalizedFeatureDifference": {
                   "quantilesAcrossResets": {str(q): float(np.quantile(nearest_rows, q)) for q in (0, .25, .5, .75, 1)},
                   "resetsAtOrBelow1eMinus5": int(np.sum(nearest_rows <= 1e-5)),
                   "resetsAtOrBelow1eMinus4": int(np.sum(nearest_rows <= 1e-4)),
                   "uniqueObservationsAtOrBelow1eMinus5": sum(value <= 1e-5 for value in nearest.values()),
                   "uniqueObservationsAtOrBelow1eMinus4": sum(value <= 1e-4 for value in nearest.values()),
                   "units": "normalized observation features, not metres; tolerances are descriptive and exclude no attempts"},
               "perReset": [{"seed": seed, "exactNovel": keys[seed] not in prior, "nearestPriorMaxAbsDifference": nearest[keys[seed]]} for seed in seeds],
               "subsetAnalysis": "Exact-novel and exact-repeated subsets are descriptive, included only when nonempty; no novelty-based case selection"}
    result = {"status": "complete_fresh_development_screen", "firstSeed": seeds[0], "seedCount": len(seeds),
              "models": list(MODELS), "modelIdentities": identities, "sourceIdentity": SOURCE,
              "newlyEvaluatedModels": list(MODELS), "baselineWasReevaluated": True,
              "attemptsPerModel": len(seeds) * len(CONDITIONS), "inputSha256": inputs,
              "analysisScriptSha256": sha(Path(__file__)), "negativeControl": negative,
              "novelty": novelty, "summaries": summaries, "causalResetWeighted": causal,
              "causalUniqueClusterWeighted": clustered, "pairedCandidateMinusInitializer": changes,
              "targetConfusionMatrices": matrices, "actualContactIndicators": contacts,
              "targetMatrixMeaning": "Rows are requested A/B; mutually exclusive legal landings in A, B, outside both, or no legal landing. Serve A/B means shallower/deeper; rally A/B means canonical left/right.",
              "bootstrap": {"seed": h.BOOTSTRAP_SEED, "replicates": h.BOOTSTRAP_DRAWS,
                            "resetWeighted": "Paired base-reset bootstrap preserving model/instruction correspondence",
                            "uniqueClusterWeighted": "Paired gains averaged within exact physical observation clusters; clusters resampled with equal weight",
                            "coverage": "Pointwise95%, not simultaneous across groups; exact observation clustering does not prove identical hidden states or independence of distinct geometries"},
              "screen": {"predeclared": plan["screening"], "tests": tests, "promising": all(tests.values()),
                         "retentionChecks": retention, "retentionInterpretation": "Per-drill point-estimate drop limit, not a statistical noninferiority guarantee",
                         "interpretation": "Screening on this same-recipe cohort, not proof of drill mastery or generalization merely because seed IDs changed"},
              "promoted": False, "masteryAccepted": False, "finalSeedsConsumed": False,
              "limitations": [
                  "Both frozen models were evaluated anew, but distinct seed IDs can produce repeated physical observations.",
                  "Exact-novel observations can differ only slightly; nearest-prior normalized feature differences are descriptive, not a physical difficulty measure.",
                  "Reset-weighted and equally weighted unique-cluster estimates answer different questions and need not match.",
                  "Observation-equivalent resets can hide simulator state differences; observations are used to limit duplicate weighting, not to prove full state identity.",
                  "Required-bounce receiving is distinct from rally-bounce feeds, where volley eligibility is already established; actual contact flags determine the reported contact type.",
                  "No-contact false volley flags are not counted as groundstrokes. Landing-shift statistics remain conditional on both attempts landing legally.",
                  "Sparse group intervals and one training lineage do not establish replicated learning effects or broad wide/deep/shallow movement mastery.",
                  "This fresh seed interval retains the existing physical recipe; final evaluation seeds remain reserved."]}
    for relative, expected in inputs.items():
        require(sha(inside(root, relative)) == expected, f"Input changed while analysis ran: {relative}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"analysis": str(output), "promising": all(tests.values()), "screenTests": tests,
                      "novelResets": len(novel), "uniquePhysicalObservations": len(unique),
                      "resetWeightedCandidateGain": causal["all"][CANDIDATE]["assignmentGain"],
                      "uniqueClusterWeightedCandidateGain": clustered["all"][CANDIDATE],
                      "promoted": False, "masteryAccepted": False}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
