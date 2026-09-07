"""Compare shot policies on one fixed training observation bank, without simulation."""
import argparse
from collections import Counter
import json
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_ppo import nonshot_parameters, validate_episodes, validate_motor_metrics


def nearby_expected_ball(observation):
    """A current-state diagnostic filter, not a predicted contact or a teacher."""
    if len(observation) != 54:
        raise ValueError("Observation schema differs")
    return (observation[46] == 1 and sum(observation[40:43]) == 1
            and (observation[4] * 8.4) ** 2 + (observation[6] * 16.2) ** 2 < 1.5 ** 2)


def compare_outputs(reference, candidate):
    if reference.shape != candidate.shape or reference.ndim != 2 or reference.shape[1] != 12 or not len(reference):
        raise ValueError("Expected matching non-empty actor outputs")
    if not torch.isfinite(reference).all() or not torch.isfinite(candidate).all():
        raise ValueError("Non-finite actor output")
    probabilities = candidate[:, 3:].softmax(-1)
    choices = candidate[:, 3:].argmax(-1)
    return dict(observations=len(reference),
                changedShotChoices=int((choices != reference[:, 3:].argmax(-1)).sum()),
                argmaxShots=dict(sorted(Counter(choices.tolist()).items())),
                meanProbabilities=probabilities.mean(0).tolist(),
                meanShotEntropy=float(-(probabilities * probabilities.clamp_min(1e-20).log()).sum(-1).mean()),
                maximumNonshotOutputChange=float((candidate[:, :3] - reference[:, :3]).abs().max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollout", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidates", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(2)
    report = json.loads(args.rollout.read_text())
    current_source = source_hash()
    if (report["status"] != "complete" or report["split"] != "training" or not report["sampledActor"]
            or report["sourceHash"] != current_source or report["actorHash"] != file_hash(args.reference)):
        raise ValueError("Expected a complete current-source reference training rollout")
    validate_motor_metrics(report)
    data_path = ROOT / report["dataPath"]
    records = [json.loads(line) for line in data_path.read_text().splitlines()]
    if len(records) != report["rows"] or not records:
        raise ValueError("Incomplete training observation bank")
    validate_episodes(records, report)
    if any(not 1000000 <= row["gameSeed"] < 1100000 for row in records):
        raise ValueError("Observation bank contains non-training seeds")
    selected = [row for row in records if nearby_expected_ball(row["observation"])]
    if not selected:
        raise ValueError("No nearby expected-team observations")
    observations = torch.tensor([row["observation"] for row in selected])
    reference, metadata = Actor.load_export(args.reference)
    if metadata["sourceHash"] != current_source:
        raise ValueError("Reference actor uses a different runtime")
    protected = nonshot_parameters(reference)
    with torch.no_grad():
        reference_outputs = reference(observations)
        models = []
        for path in [args.reference] + args.candidates:
            candidate, metadata = Actor.load_export(path)
            if metadata["sourceHash"] != current_source:
                raise ValueError("Candidate actor uses a different runtime")
            actual = nonshot_parameters(candidate)
            if len(actual) != len(protected) or any(a.shape != b.shape for a, b in zip(actual, protected)):
                raise ValueError("Actor architecture differs")
            outputs = candidate(observations)
            models.append(dict(actorPath=str(path.resolve()), actorHash=file_hash(path),
                               maximumNonshotParameterChange=max(float((a-b).abs().max()) for a, b in zip(actual, protected)),
                               **compare_outputs(reference_outputs, outputs),
                               byPhase=[dict(phase=name, **compare_outputs(reference_outputs[mask], outputs[mask]))
                                        for index, name in ((40, "ServeFlight"), (41, "ReturnFlight"), (42, "Rally"))
                                        if (mask := observations[:, index] == 1).any()]))
    result = dict(version="player-shot-audit-v1", sourceHash=current_source,
                  auditHash=file_hash(__file__), rolloutPath=str(args.rollout.resolve()),
                  rolloutHash=file_hash(args.rollout), dataHash=file_hash(data_path),
                  trainingObservations=len(records), selectedObservations=len(selected),
                  sampledShots=dict(sorted(Counter(row["sample"]["action"]["shot"] for row in selected).items())),
                  models=models,
                  limitation="Fixed training-state comparison only. Nearby means ground distance below 1.5 m with own team expected. It is not a contact count or match-strength result.")
    if source_hash() != current_source:
        raise ValueError("Runtime changed during audit")
    if args.output:
        with args.output.open("x") as output:
            json.dump(result, output, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
