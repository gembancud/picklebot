"""Shared actor definition and explicit JSON export for Unity inference."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_path(path):
    return str(path).replace("\\", "/")


def canonical_text(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def ordinal_key(path):
    return canonical_path(path).encode("utf-16-be")


def source_record_text(records):
    records = [(canonical_path(path), canonical_text(text)) for path, text in records]
    return "\n".join(path + "\n" + text for path, text in sorted(records, key=lambda item: ordinal_key(item[0])))


def source_records(root, folders, excluded=()):
    records = []
    for folder in folders:
        for path in (root / "Assets/Picklebot" / folder).rglob("*.cs"):
            name = path.relative_to(root).as_posix()
            if "/Tests/" not in name and path.name not in excluded:
                records.append((name, path.read_text(encoding="utf-8-sig")))
    return records


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contact_source_hash(root):
    return digest(source_record_text(source_records(root, ("Doubles", "Core", "Simulation"), ("DoublesDemo.cs", "DoublesEditor.cs"))))


def player_source_hash(root):
    return digest(contact_source_hash(root) + "\n" + source_record_text(source_records(root, ("PlayerAgents",))))


def team_source_hash(root):
    paths = sorted((root / "Assets/Picklebot/DoublesTraining").rglob("*.cs"), key=lambda p: ordinal_key(p.relative_to(root)))
    return digest(contact_source_hash(root) + "\n".join(canonical_text(p.read_text(encoding="utf-8-sig")) for p in paths))


def source_hash():
    return player_source_hash(ROOT)


class Actor(nn.Module):
    def __init__(self, hidden=128):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(54, hidden), nn.Linear(hidden, hidden), nn.Linear(hidden, 12)])
        self.log_std = nn.Parameter(torch.full((2,), -2.0))

    def forward(self, observation):
        value = observation
        for i, layer in enumerate(self.layers):
            value = layer(value)
            if i < len(self.layers) - 1:
                value = value.tanh()
        return value

    @staticmethod
    def movement(raw):
        move = raw.tanh()
        return move / torch.linalg.vector_norm(move, dim=-1, keepdim=True).clamp_min(1.0)

    def export(self, metadata):
        return dict(metadata, version="player-actor-v1", observationVersion="player-observation-v1",
                    logStd=self.log_std.detach().cpu().clamp(-5, 1).tolist(),
                    layers=[dict(inputs=layer.in_features, outputs=layer.out_features,
                                 weights=layer.weight.detach().cpu().flatten().tolist(),
                                 bias=layer.bias.detach().cpu().tolist()) for layer in self.layers])

    @classmethod
    def load_export(cls, path):
        value = json.loads(Path(path).read_text())
        if value["version"] != "player-actor-v1" or value["observationVersion"] != "player-observation-v1":
            raise ValueError("Actor schema mismatch")
        model = cls(value["layers"][0]["outputs"])
        if len(value["layers"]) != len(model.layers):
            raise ValueError("Actor layer count mismatch")
        with torch.no_grad():
            for layer, record in zip(model.layers, value["layers"]):
                if (record["inputs"], record["outputs"]) != (layer.in_features, layer.out_features):
                    raise ValueError("Actor shape mismatch")
                layer.weight.copy_(torch.tensor(record["weights"]).reshape(layer.out_features, layer.in_features))
                layer.bias.copy_(torch.tensor(record["bias"]))
            model.log_std.copy_(torch.tensor(value["logStd"]))
        if not all(torch.isfinite(p).all() for p in model.parameters()):
            raise ValueError("Non-finite actor tensors")
        return model, value


def teacher_data(report_path, split):
    report = json.loads(Path(report_path).read_text())
    if report.get("status", "complete") != "complete":
        raise ValueError("Teacher collection did not complete")
    if report["split"] != split or report["sourceHash"] != source_hash():
        raise ValueError("Wrong teacher split or stale source")
    if report["protocolHash"] != file_hash(ROOT / "config/player-agents/evaluation-v1.json"):
        raise ValueError("Teacher protocol changed")
    if report["contactModelHash"] != file_hash(ROOT / "Assets/Picklebot/Doubles/Models/contact.json"):
        raise ValueError("Teacher contact checkpoint changed")
    if report["teamModelHash"] != file_hash(ROOT / "Assets/Picklebot/Doubles/Models/teams.json"):
        raise ValueError("Teacher team checkpoint changed")
    if report["baselineManifestHash"] != file_hash(ROOT / "artifacts/player-agents/baseline-manifest.json"):
        raise ValueError("Teacher baseline manifest changed")
    data_path = ROOT / report["dataPath"]
    records = [json.loads(line) for line in data_path.read_text().splitlines()]
    x, y = teacher_tensors(records, report["rows"], split)
    if report.get("candidateOnly") or report.get("fixtureVersion") == "incoming-skill-v1":
        validate_incoming_report(report)
    if report.get("baselineOpponent") or report.get("candidateOnly"):
        validate_curriculum_ownership(records, report)
    elif "teacherProbability" in report:
        validate_four_player_curriculum(records, report)
    return x, y, report, file_hash(data_path)


def validate_four_player_curriculum(records, report):
    """Every four-player teaching step must retain four separate owned labels."""
    games = report.get("gameResults", [])
    if not games or report["teacherDecisions"] + report["actorDecisions"] != len(records):
        raise ValueError("Missing four-player curriculum evidence")
    seeds = {report["seed"] + i for i in range(len(games))}
    for index, game in enumerate(games):
        if game["gameSeed"] != report["seed"] + index or game["candidateTeam"] != -1:
            raise ValueError("Four-player curriculum game ownership changed")
    seen = set()
    for row in records:
        if row["gameSeed"] not in seeds or row.get("candidateTeam") != -1 or row["tick"] % 12:
            raise ValueError("Four-player curriculum ownership or timing changed")
        key = (row["gameSeed"], row["rally"], row["tick"], row["player"])
        if key in seen: raise ValueError("Duplicate four-player decision")
        seen.add(key)
    for seed, rally, tick, _ in seen:
        if any((seed, rally, tick, player) not in seen for player in range(4)):
            raise ValueError("Missing simultaneous four-player decision")


def validate_incoming_report(report):
    if (report.get("candidateOnly") is not True or report.get("fixtureVersion") != "incoming-skill-v1" or report.get("games") != 0
            or report.get("baselineOpponent") or report.get("physicsHz") != 240
            or report.get("decisionTicks") != 12 or report.get("actionLatencyTicks") != 6
            or report.get("requestedFixtures") != len(report.get("gameResults", []))
            or any(g.get("complete") or g.get("winner") != -1 for g in report["gameResults"])):
        raise ValueError("Invalid injected skill report or claimed match results")
    snapshot = (ROOT / report["collectorSnapshotPath"]).resolve()
    snapshot.relative_to((ROOT / "artifacts/player-agents").resolve())
    if file_hash(snapshot) != report["collectorHash"]:
        raise ValueError("Incoming collector snapshot changed")
    if "skillProfile" in report:
        validate_incoming_profile(report)


def validate_incoming_profile(report):
    """Check the disclosed reset distribution, never treat skill cases as games."""
    profile = report["skillProfile"]
    if profile not in ("deep", "kitchen"):
        raise ValueError("Unknown incoming skill profile")
    kitchen = profile == "kitchen"
    expected = dict(lane=[-2, 2] if kitchen else [-2.7, 2.7], height=[1.1, 1.5],
                    ballDepth=[.15, .7], velocityX=[-.8, .8], velocityY=[.8, 1.8],
                    velocityZ=[-3.6, -2.7] if kitchen else [-8.7, -7.3],
                    playerDepth=[1.8, 3.2] if kitchen else [3.4, 6.6], playerXJitter=[-.35, .35])
    ranges = report.get("ranges", {})
    if set(ranges) != set(expected):
        raise ValueError("Incoming profile ranges changed")
    def inside(value, bounds):
        return type(value) in (float, int) and math.isfinite(value) and bounds[0] - 1e-5 <= value <= bounds[1] + 1e-5
    for key, bounds in expected.items():
        if (not isinstance(ranges[key], list) or len(ranges[key]) != 2
                or any(not inside(value, [bound, bound]) for value, bound in zip(ranges[key], bounds))):
            raise ValueError("Incoming profile ranges changed: " + key)
    for game in report["gameResults"]:
        team = game.get("candidateTeam")
        if type(team) is not int or team not in (0, 1):
            raise ValueError("Incoming profile has no valid player ownership")
        for field, keys in (("canonicalBall", ["lane", "height", "ballDepth"]),
                            ("canonicalVelocity", ["velocityX", "velocityY", "velocityZ"])):
            values = game.get(field)
            if not isinstance(values, list) or len(values) != 3 or any(not inside(v, expected[k]) for v, k in zip(values, keys)):
                raise ValueError("Incoming initial ball state differs from its profile")
        starts = game.get("playerStarts")
        if not isinstance(starts, list) or len(starts) != 4:
            raise ValueError("Missing incoming player starts")
        for player, position in enumerate(starts):
            sign = 1 if player < 2 else -1
            x = (1.55 if player % 2 == 0 else -1.55) * sign
            jitter = .35 if player // 2 == team else 0
            depth = expected["playerDepth"] if player // 2 == team else [6, 6]
            if (not isinstance(position, list) or len(position) != 3
                    or not inside(position[0], [x - jitter, x + jitter])
                    or not inside(position[1], [0, 0]) or not inside(-sign * position[2], depth)):
                raise ValueError("Incoming player start differs from its profile")
        if any(type(game.get(k)) is not bool for k in ("legalHit", "legalLanding", "legalKitchenGroundstroke")):
            raise ValueError("Missing incoming contact outcomes")
        if (game["legalLanding"] or game["legalKitchenGroundstroke"]) and not game["legalHit"]:
            raise ValueError("Incoming outcome requires a legal contact")


def validate_curriculum_ownership(records, report):
    """Baseline seats must never provide learner actions or teacher labels."""
    games = report["gameResults"]
    if not games or report["initialCandidateTeam"] not in (0, 1):
        raise ValueError("Missing curriculum game ownership")
    owners = {}
    for index, game in enumerate(games):
        seed = report["seed"] + index
        team = report["initialCandidateTeam"] ^ (index & 1)
        if game["gameSeed"] != seed or game["candidateTeam"] != team:
            raise ValueError("Curriculum game seeds or court ends do not match")
        owners[seed] = team
    if report["teacherDecisions"] + report["actorDecisions"] != len(records):
        raise ValueError("Curriculum mixture counts differ from recorded decisions")
    seen = set()
    for row in records:
        team = owners.get(row["gameSeed"])
        if team is None or row.get("candidateTeam") != team or row["player"] // 2 != team:
            raise ValueError("Opponent decision entered the learner curriculum")
        key = (row["gameSeed"], row["rally"], row["tick"], row["player"])
        if key in seen:
            raise ValueError("Duplicate curriculum decision")
        seen.add(key)
    for seed, rally, tick, player in seen:
        if (seed, rally, tick, player ^ 1) not in seen:
            raise ValueError("Missing simultaneous teammate decision")


def teacher_tensors(records, expected_rows, split):
    if split not in ("training", "development"):
        raise ValueError("Unknown teacher split")
    lower = 1000000 if split == "training" else 1100000
    if len(records) != expected_rows or not records or not all(lower <= r["gameSeed"] < lower + 100000 for r in records):
        raise ValueError("Teacher rows or seed partition are invalid")
    if any(r["player"] not in range(4) or r["tick"] < 0 or r["rally"] < 0 or type(r["action"]["attempt"]) is not bool for r in records):
        raise ValueError("Invalid teacher ownership, timing or hit label")
    x = np.asarray([r["observation"] for r in records], dtype=np.float32)
    y = np.asarray([[r["action"]["moveX"], r["action"]["moveZ"], float(r["action"]["attempt"]), r["action"]["shot"]] for r in records], dtype=np.float32)
    if x.shape != (len(records), 54) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Invalid teacher tensors")
    if (np.linalg.norm(y[:, :2], axis=1) > 1.00001).any() or (y[:, 3] < 0).any() or (y[:, 3] > 8).any() or (y[:, 3] != np.floor(y[:, 3])).any():
        raise ValueError("Teacher action is outside the actor contract")
    return torch.from_numpy(x), torch.from_numpy(y)
