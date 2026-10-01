"""CPU-only checkpoint/first-decision diagnostic; no Unity rollout or optimization.

Reads pinned F: evidence and installed ML-Agents actor/critic implementation.
Writes only an exclusive JSON report beside this workspace script.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from mlagents.torch_utils import torch
from mlagents.trainers.settings import NetworkSettings
from mlagents.trainers.torch_entities.networks import SimpleActor, ValueNetwork
from mlagents_envs.base_env import ObservationSpec, DimensionProperty, ObservationType, ActionSpec
import mlagents.trainers.torch_entities.networks as networks_module
import mlagents.trainers.torch_entities.encoders as encoders_module
import mlagents.trainers.torch_entities.action_model as action_module

ROOT = Path("F:/dev/picklebot")
BASE = ROOT / "artifacts/hierarchy-v1"
FIRST_WEIGHT = "network_body._body_endoder.seq_layers.0.weight"
GOALS = ["playBall", "recover", "cover", "yield", "move.enabled", "move.relative.x", "move.relative.z", "move.radius", "shot.enabled", "shot.x", "shot.z", "shot.radius"]
CHANNELS = [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17]
MOTORS = ["move.x", "move.z", "turn.rate", "crouch", "sprint", "torso.turn", "torso.forwardLean", "torso.lateralLean", "shoulder.yaw", "shoulder.flexion", "shoulder.abduction", "elbow.flexion", "forearm.rotation", "wrist.flexion", "wrist.deviation", "offHand.lift"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    result = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]
    mapped = {row["seed"]: row for row in result}
    require(len(result) == len(mapped), f"Duplicate seeds: {path}")
    return mapped


def stat(array):
    a = np.asarray(array, dtype=float)
    require(a.size > 0 and np.isfinite(a).all(), "Invalid numeric summary")
    return {"minimum": float(a.min()), "mean": float(a.mean()), "median": float(np.median(a)), "maximum": float(a.max())}


def load_case(label, run, verification, model):
    checkpoint = ROOT / "training/snapshots/execution-v1-initial.pt" if label == "initial" else ROOT / f"artifacts/mlagents/{run}/PicklebotExecutionV1/checkpoint.pt"
    expected = "2c1dcfab6c32d3e98dfd334863f5670c09cef2edfb8bf51483bba4abe683cb9f" if label == "initial" else read(verification)["checkpointHash"]
    require(sha(checkpoint) == expected, f"Checkpoint identity mismatch: {checkpoint}")
    folder = (BASE / "smooth-distance-01/evaluation" if label == "smooth" else BASE / "two-regions-01/evaluation") / model
    observed, episodes, goals, identities = {}, {}, {}, {}
    for condition in ("A", "B"):
        part = folder / condition
        observed[condition] = {int(k): v for k, v in read(part / "first-decisions.json").items()}
        episodes[condition] = rows(part / "episodes.jsonl")
        goals[condition] = rows(part / "execution-goals.jsonl")
        for name in ("first-decisions.json", "episodes.jsonl", "execution-goals.jsonl", "report.json"):
            identities[str((part / name).relative_to(ROOT))] = sha(part / name)
    return dict(label=label, checkpoint=checkpoint, checkpointHash=expected, observed=observed, episodes=episodes, goals=goals, inputHashes=identities)


def network_diagnostic(module, state, initial_state, x, n):
    norm = module.network_body.processors[0].normalizer
    normalized = norm(x)
    require(torch.isfinite(normalized).all().item(), "Nonfinite normalized observation")
    w = state[FIRST_WEIGHT].detach().cpu().numpy()
    initial_w = initial_state[FIRST_WEIGHT].detach().cpu().numpy()
    normalized_np = normalized.detach().cpu().numpy()
    delta = normalized_np[n:] - normalized_np[:n]
    first_layer_goal_delta = delta[:, 124:] @ w[:, 124:].T
    mean = norm.running_mean.detach().cpu().numpy()
    count = int(norm.normalization_steps.item())
    std = torch.sqrt(norm.running_variance / norm.normalization_steps).detach().cpu().numpy()
    require(np.isfinite(std).all() and (std > 0).all(), "Invalid normalizer scale")
    goal_info = [{
        "name": name, "index": 124 + i, "runningMean": float(mean[124 + i]),
        "normalizerStd": float(std[124 + i]),
        "normalizedRange": [float(normalized_np[:, 124 + i].min()), float(normalized_np[:, 124 + i].max())],
        "pairedNormalizedBMinusA": stat(delta[:, 124 + i]),
        "normalizedAtClippingLimitFraction": float(np.mean(np.abs(normalized_np[:, 124 + i]) >= 5)),
        "firstLayerColumnL2": float(np.linalg.norm(w[:, 124 + i])),
        "firstLayerColumnChangeL2": float(np.linalg.norm(w[:, 124 + i] - initial_w[:, 124 + i])),
    } for i, name in enumerate(GOALS)]
    return {
        "normalizationSteps": count, "goals": goal_info,
        "goalFirstLayerWeightL2": float(np.linalg.norm(w[:, 124:])),
        "oldObservationFirstLayerWeightL2": float(np.linalg.norm(w[:, :124])),
        "oldObservationFirstLayerChangeL2": float(np.linalg.norm(w[:, :124] - initial_w[:, :124])),
        "firstLayerGoalContrastL2PerState": stat(np.linalg.norm(first_layer_goal_delta, axis=1)),
        "goalXYNormalizedBMinusAByState": delta[:, [133, 134]].tolist(),
    }, normalized_np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("goal_path_diagnostic.json"))
    args = parser.parse_args()
    require(not args.output.exists(), f"Refusing overwrite: {args.output}")
    require(args.output.resolve().is_relative_to(Path(__file__).resolve().parent), "Output must remain in the workspace diagnostic directory")
    torch.set_num_threads(1)
    torch.set_default_device("cpu")
    cases = [
        load_case("initial", None, None, "ExecutionV1Initial"),
        load_case("linear", "execution-two-regions-02", BASE / "two-regions-01/execution-two-regions-02/verification.json", "ExecutionV1TwoRegions01"),
        load_case("smooth", "execution-smooth-distance-01", BASE / "smooth-distance-01/execution-smooth-distance-01/verification.json", "ExecutionV1SmoothDistance01"),
    ]
    seeds = sorted(cases[0]["observed"]["A"])
    require(seeds == list(range(1108985, 1108985 + 256)), "Unexpected development seeds")
    n = len(seeds)
    initial_state = torch.load(cases[0]["checkpoint"], map_location="cpu", weights_only=False)
    specifications = [ObservationSpec((136,), (DimensionProperty.NONE,), ObservationType.DEFAULT, "VectorSensor_size136")]
    settings = NetworkSettings(normalize=True, hidden_units=128, num_layers=2)
    checks = {"physicalObservationMatches": 0, "goalCoordinateMatches": 0, "serveTargetSideMatches": 0, "landingDistanceMatches": 0}
    outputs = {}
    for case in cases:
        label = case["label"]
        for condition in ("A", "B"):
            require(sorted(case["observed"][condition]) == seeds, f"Missing first states: {label}/{condition}")
            for seed in seeds:
                first = case["observed"][condition][seed]
                ep, goal = case["episodes"][condition][seed], case["goals"][condition][seed]
                observation = np.asarray(first["observation"])
                baseline = np.asarray(cases[0]["observed"]["A"][seed]["observation"])
                require(observation.shape == (136,) and np.isfinite(observation).all(), "Invalid observation")
                require(np.array_equal(observation[:124], baseline[:124]), f"Reset mismatch: {label}/{condition}/{seed}")
                checks["physicalObservationMatches"] += 1
                require(first["player"] == ep["player"] == goal["player"], "Private player mismatch")
                canonical_target = np.array([goal["targetX"], goal["targetZ"]])
                decoded_target = observation[[133, 134]] * np.array([3.048, 6.7056])
                require(np.allclose(decoded_target, canonical_target, atol=2e-6, rtol=0), "Goal target encoding mismatch")
                require(observation[132] == 1 and np.isclose(observation[135] * 3, 1, atol=2e-6), "Goal mask or radius mismatch")
                is_serve = ep["task"] == "stationary-serve"
                if is_serve:
                    # Rules designate the diagonally opposite box. Own-right role -> canonical target X negative.
                    expected_x = 1.4 if ep["serveFromLeft"] else -1.4
                    require(bool(observation[53]) == (not ep["serveFromLeft"]), "Serve role/side inconsistency")
                    expected = [expected_x, 3.3 if condition == "A" else 5.4]
                    checks["serveTargetSideMatches"] += 1
                else:
                    expected = [-1.2 if condition == "A" else 1.2, 3.8]
                require(np.allclose(canonical_target, expected, atol=2e-6, rtol=0), "A/B canonical target mapping mismatch")
                checks["goalCoordinateMatches"] += 1
                if goal["legalLanding"]:
                    actual_distance = np.linalg.norm(np.array([goal["landingX"], goal["landingZ"]]) - canonical_target)
                    require(abs(actual_distance - goal["distance"]) < 2e-5, "Canonical landing distance mismatch")
                    checks["landingDistanceMatches"] += 1
        observations = np.asarray([case["observed"][c][s]["observation"] for c in ("A", "B") for s in seeds], dtype=np.float32)
        x = torch.tensor(observations, device="cpu")
        checkpoint = torch.load(case["checkpoint"], map_location="cpu", weights_only=False)
        actor = SimpleActor(specifications, settings, ActionSpec(16, (2,)), conditional_sigma=False, tanh_squash=False).to("cpu")
        critic = ValueNetwork(["extrinsic"], specifications, settings).to("cpu")
        actor.load_state_dict(checkpoint["Policy"], strict=True)
        critic.load_state_dict(checkpoint["Optimizer:critic"], strict=True)
        actor.eval()
        critic.eval()
        with torch.no_grad():
            actor_diag, actor_normalized = network_diagnostic(actor, checkpoint["Policy"], initial_state["Policy"], x, n)
            critic_diag, critic_normalized = network_diagnostic(critic, checkpoint["Optimizer:critic"], initial_state["Optimizer:critic"], x, n)
            encoded, _ = actor.network_body([x])
            distribution = actor.action_model._continuous_distribution(encoded)
            raw = distribution.mean.detach().cpu().numpy()
            scaled = raw / 3
            clipped = np.clip(raw, -3, 3) / 3
            values, _ = critic([x])
            value = values["extrinsic"].detach().cpu().numpy().reshape(-1)
            raw_delta, scale_delta, clip_delta = raw[n:] - raw[:n], scaled[n:] - scaled[:n], clipped[n:] - clipped[:n]
            recorded_physical = np.asarray([case["observed"][c][s]["physical"] for c in ("A", "B") for s in seeds])
            decoded = clipped.copy()
            for index, channel in enumerate(CHANNELS):
                if channel in (3, 5, 17):
                    decoded[:, index] = (decoded[:, index] + 1) * .5
            recorded_error = np.abs(decoded - recorded_physical[:, CHANNELS])
            require(float(recorded_error.max()) < 2e-5, f"CPU checkpoint differs from recorded Unity first commands: {label}: {recorded_error.max()}")
            channel_rows = []
            for i, name in enumerate(MOTORS):
                active = np.abs(scale_delta[:, i]) > 1e-8
                removed = active & (np.abs(clip_delta[:, i]) < 1e-8)
                channel_rows.append({
                    "channel": name, "rawStd": float(distribution.std[0, i]),
                    "rawMeanBMinusA": stat(raw_delta[:, i]),
                    "scaledMeanBMinusABeforeClip": stat(scale_delta[:, i]),
                    "mappedMeanBMinusAAfterClip": stat(clip_delta[:, i]),
                    "pairedNonzeroPreclipContrasts": int(active.sum()), "contrastsFullyRemovedByClip": int(removed.sum()),
                    "allInitialStatesMeanClippedFraction": float((np.abs(raw[:, i]) >= 3).mean()),
                })
            subsets = {"all": list(range(n)), "serve": [i for i,s in enumerate(seeds) if case["episodes"]["A"][s]["task"] == "stationary-serve"], "nonserve": [i for i,s in enumerate(seeds) if case["episodes"]["A"][s]["task"] != "stationary-serve"]}
            summaries = {}
            for name, indices in subsets.items():
                summaries[name] = {
                    "pairs": len(indices), "rawMeanAbsMaxPerPair": stat(np.abs(raw_delta[indices]).max(axis=1)),
                    "beforeClipAbsMaxPerPair": stat(np.abs(scale_delta[indices]).max(axis=1)),
                    "afterClipAbsMaxPerPair": stat(np.abs(clip_delta[indices]).max(axis=1)),
                    "criticValueBMinusA": stat((value[n:] - value[:n])[indices]),
                    "encodedActorBMinusAL2": stat(torch.linalg.vector_norm(encoded[n:][indices] - encoded[:n][indices], dim=1).cpu().numpy()),
                }
            raw_records = []
            for i, seed in enumerate(seeds):
                raw_records.append({
                    "seed": seed, "player": case["episodes"]["A"][seed]["player"], "task": case["episodes"]["A"][seed]["task"],
                    "actorNormalizedGoalsA": actor_normalized[i, 124:].tolist(), "actorNormalizedGoalsB": actor_normalized[n+i, 124:].tolist(),
                    "criticNormalizedGoalsA": critic_normalized[i, 124:].tolist(), "criticNormalizedGoalsB": critic_normalized[n+i, 124:].tolist(),
                    "rawMeansA": raw[i].tolist(), "rawMeansB": raw[n+i].tolist(),
                    "scaledMeansBeforeClipA": scaled[i].tolist(), "scaledMeansBeforeClipB": scaled[n+i].tolist(),
                    "mappedMeansAfterClipA": clipped[i].tolist(), "mappedMeansAfterClipB": clipped[n+i].tolist(),
                    "criticValueA": float(value[i]), "criticValueB": float(value[n+i]),
                })
            outputs[label] = {
                "checkpoint": str(case["checkpoint"]), "checkpointSha256": case["checkpointHash"],
                "checkpointSteps": {k: int(v.item()) for k,v in checkpoint["global_step"].items()},
                "inputSha256": case["inputHashes"], "actor": actor_diag, "critic": critic_diag,
                "cpuVersusRecordedUnityPhysicalMaxError": float(recorded_error.max()),
                "summaries": summaries, "actionChannels": channel_rows, "rawFirstStatePairs": raw_records,
            }
    source_paths = [
        Path(networks_module.__file__), Path(encoders_module.__file__), Path(action_module.__file__),
        ROOT / "Assets/Picklebot/PlayerLearning/PlayerExecutionGoalV1.cs",
        ROOT / "Assets/Picklebot/PlayerLearning/PlayerExecutionDrillsV1.cs",
        ROOT / "Assets/Picklebot/PlayerLearning/PlayerMlAgentV3.cs",
        ROOT / "Assets/Picklebot/PlayerAgents/PlayerObservation.cs",
        ROOT / "Assets/Picklebot/Doubles/DoublesRules.cs",
    ]
    result = {
        "status": "completed_cpu_first_decision_diagnostic", "scriptSha256": sha(Path(__file__)),
        "sourceSha256": {str(p): sha(p) for p in source_paths}, "checks": checks,
        "baseResetCount": n, "uniqueInitialPhysicalObservations": len(np.unique(np.asarray([cases[0]["observed"]["A"][s]["observation"][:124] for s in seeds]), axis=0)),
        "models": outputs,
        "limitations": [
            "Only recorded first decisions are available here; this is not a whole-stroke or in-rally audit.",
            "No environment was stepped, no stochastic action was sampled, and no policy, normalizer or optimizer update was performed.",
            "Goal columns changing and actor sensitivity are not proof of correct PPO credit assignment, useful aiming or sufficient network capacity.",
            "Motor-command signs cannot be equated to landing-direction signs in this articulated nonlinear simulation.",
            "Canonical coordinate checks validate encoded targets and recorded canonical distances; raw world-space landing-event streams were not part of these files.",
            "Recovered/cover/yield and movement-goal features were inactive in these experiments; their unchanged weights do not indicate failed training.",
        ],
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    brief = {label: {"actorNormSteps": data["actor"]["normalizationSteps"], "criticNormSteps": data["critic"]["normalizationSteps"],
                    "actorGoalWeightL2": data["actor"]["goalFirstLayerWeightL2"], "criticGoalWeightL2": data["critic"]["goalFirstLayerWeightL2"],
                    "actorTargetColumns": [row for row in data["actor"]["goals"] if row["name"] in ("shot.x", "shot.z")],
                    "summaries": data["summaries"], "cpuUnityMaxError": data["cpuVersusRecordedUnityPhysicalMaxError"]}
             for label, data in outputs.items()}
    print(json.dumps({"output": str(args.output), "checks": checks, "models": brief}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
