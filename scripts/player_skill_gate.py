"""Experimental player-local selector. This schema is not an action policy export."""
import json
from pathlib import Path

import torch
from torch import nn

from player_actor import Actor, ROOT, file_hash


class SkillGate(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(54, 32), nn.Linear(32, 1)])

    @staticmethod
    def inputs(observations):
        if observations.ndim != 2 or observations.shape[1] != 54 or not torch.isfinite(observations).all():
            raise ValueError("Expected finite player-owned 54-value observations")
        result = observations.clone()
        # Teacher paddle pose is a consequence of its action. Do not classify by it.
        result[:, 25:37] = 0
        return result

    def forward(self, observations):
        return self.layers[1](self.layers[0](self.inputs(observations)).tanh()).squeeze(-1)

    def export(self, metadata):
        return dict(metadata, version="player-skill-gate-v1", observationVersion="player-observation-v1",
                    maskedIndices=list(range(25, 37)), threshold=0, selection="logit >= 0 selects expert 1; otherwise expert 0",
                    layers=[dict(inputs=l.in_features, outputs=l.out_features,
                                 weights=l.weight.detach().flatten().tolist(), bias=l.bias.detach().tolist()) for l in self.layers])

    @classmethod
    def load_export(cls, path):
        value = json.loads(Path(path).read_text())
        if (value.get("version") != "player-skill-gate-v1"
                or value.get("observationVersion") != "player-observation-v1"
                or value.get("maskedIndices") != list(range(25, 37))
                or type(value.get("threshold")) is not int or value["threshold"] != 0):
            raise ValueError("Skill gate schema mismatch")
        model = cls()
        if len(value.get("layers", [])) != 2:
            raise ValueError("Skill gate needs two layers")
        with torch.no_grad():
            for layer, record in zip(model.layers, value["layers"]):
                if ((record.get("inputs"), record.get("outputs")) != (layer.in_features, layer.out_features)
                        or len(record.get("weights", [])) != layer.weight.numel()
                        or len(record.get("bias", [])) != layer.bias.numel()):
                    raise ValueError("Skill gate shape mismatch")
                layer.weight.copy_(torch.tensor(record["weights"]).reshape_as(layer.weight))
                layer.bias.copy_(torch.tensor(record["bias"]))
        if not all(torch.isfinite(p).all() for p in model.parameters()):
            raise ValueError("Non-finite skill gate weights")
        return model, value


def source_label(report):
    if report.get("fixtureVersion") == "incoming-skill-v1":
        if report.get("skillProfile") not in ("kitchen", "deep"):
            raise ValueError("Unknown training skill profile")
        return int(report["skillProfile"] == "kitchen")
    if report.get("baselineOpponent") is True and report.get("teacherProbability") == 1:
        return 0
    raise ValueError("Unapproved selector source")


def load_experts(metadata):
    records = metadata.get("experts", [])
    if len(records) != 2 or [r.get("role") for r in records] != ["older", "short-return"]:
        raise ValueError("Expected ordered older and short-return experts")
    models = []
    for record in records:
        path = (ROOT / record["path"]).resolve(); path.relative_to(ROOT)
        if file_hash(path) != record["sha256"]:
            raise ValueError("Frozen expert changed")
        model, actor = Actor.load_export(path)
        if type(actor.get("trainingSteps")) is not int or actor["trainingSteps"] <= 0:
            raise ValueError("Untrained expert")
        if actor["sourceHash"] != record["trainingSourceHash"]:
            raise ValueError("Expert training source changed")
        for field in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
            if actor[field] != metadata[field]:
                raise ValueError("Expert provenance differs: " + field)
        models.append(model.eval().requires_grad_(False))
    return models


def selected_outputs(gate, experts, observations):
    logits = gate(observations)
    choice = (logits >= 0).long()
    # Each expert sees this player's unmodified observations, never a partner's input.
    output = torch.where(choice[:, None].bool(), experts[1](observations), experts[0](observations))
    return logits, choice, output
