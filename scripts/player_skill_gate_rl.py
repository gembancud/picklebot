"""Training-only selector likelihoods and complete-game rollout verification."""
import copy
import json
import math
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_skill_gate import SkillGate, load_experts
from player_skill_gate_games import validate_trace, validate_game_outcome
from player_acceptance import validate_player_identities
from player_ppo import log_probability, validate_motor_metrics
from player_skill_retention import validate_replayed_action


def next_draw(state):
    state ^= (state << 13) & 0xffffffff
    state ^= state >> 17
    state ^= (state << 5) & 0xffffffff
    return state, (state >> 8)/16777216


def likelihood(logits, choices):
    if (logits.ndim != 1 or choices.shape != logits.shape or not torch.isfinite(logits).all()
            or not ((choices == 0) | (choices == 1)).all()):
        raise ValueError("Invalid sampled selector inputs")
    probability = .05 + .9*(.5*logits).sigmoid()
    return torch.where(choices.bool(), probability.log(), torch.log1p(-probability)), probability


def game_weights(outcomes, lengths):
    if (len(outcomes) != len(lengths) or not lengths or any(v not in (-1, 1) for v in outcomes)
            or any(type(n) is not int or n < 1 for n in lengths)):
        raise ValueError("Only complete nonempty team-game trajectories can train")
    rewards = torch.cat([torch.full((n,), float(v)) for v, n in zip(outcomes, lengths)])
    weights = torch.cat([torch.full((n,), 1/n, dtype=torch.float64) for n in lengths])
    return rewards, weights


def validate_opponent_record(row, raw, expected_logp):
    sample = row["opponentSample"]
    if (not math.isfinite(sample["logProbability"]) or not math.isfinite(float(expected_logp))
            or abs(sample["logProbability"]-float(expected_logp)) > .0002):
        raise ValueError("Older opponent action likelihood changed")
    # The decision loop validates an already bounded action again. Float32
    # radial normalization can change movement by about 1e-7 on the unit rim.
    # Replay both copies under the existing actor tolerance; keep hit/shot exact.
    for action in (sample["action"], row["action"]):
        validate_replayed_action(action, Actor.movement(raw), row["action"]["attempt"], row["action"]["shot"])


def verify_training_schedule(plan):
    if (plan.get("version") != "player-skill-gate-training-v1" or plan.get("split") != "training"
            or plan.get("seedList") != list(range(1071000, 1071004)) or plan.get("gamesPerGroup") != 1
            or plan.get("sampledSelector") is not True or plan.get("sampledActor") is not False
            or plan.get("logitScale") != .5 or plan.get("explorationFloor") != .05
            or plan.get("opponentMode") != "older actor / sampled"):
        raise ValueError("Changed selector-training schedule or likelihood")
    expected = [dict(group=g, candidateTeam=(g//2)%2, sampledOpponent=True,
                     swapPartnerIdentities=bool(g&1), seeds=[1071000+g]) for g in range(4)]
    if plan.get("groups") != expected:
        raise ValueError("Changed selector-training court ends or identities")


def verify(folder):
    torch.set_num_threads(2)
    plan_path = folder/"training-plan.json"; plan = json.loads(plan_path.read_text())
    verify_training_schedule(plan)
    completion = json.loads((folder/"completion.json").read_text())
    if (completion.get("status") != "complete" or completion.get("games") != 4
            or completion.get("evaluationPlanHash") != file_hash(plan_path)
            or set(completion.get("reportHashes", {})) != {f"group-{g}.json" for g in range(4)}):
        raise ValueError("Training collection is not terminal")
    for pk, hk in (("collectorSnapshotPath", "collectorHash"), ("gatePath", "gateHash"),
                   ("shortActorPath", "shortActorHash"), ("olderExpertPath", "actorHash")):
        path = (ROOT/plan[pk]).resolve(); path.relative_to(ROOT)
        if file_hash(path) != plan[hk]: raise ValueError("Changed training artifact: " + pk)
    gate, metadata = SkillGate.load_export(ROOT/plan["gatePath"]); gate.eval(); experts = load_experts(metadata)
    if plan["sourceHash"] != source_hash() or metadata["sourceHash"] != source_hash():
        raise ValueError("Training runtime changed")
    for key in ("sourceHash", "gateHash", "actorHash", "shortActorHash"):
        if completion[key] != plan[key]: raise ValueError("Training completion provenance changed")
    for field, path in (("protocolHash", "config/player-agents/evaluation-v1.json"),
                        ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json"),
                        ("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                        ("opponentHash", "Assets/Picklebot/Doubles/Models/teams.json")):
        if plan[field] != file_hash(ROOT/path): raise ValueError("Changed frozen training input")
    if (plan["actorHash"] != metadata["experts"][0]["sha256"]
            or plan["shortActorHash"] != metadata["experts"][1]["sha256"]
            or plan["opponentActorHash"] != plan["actorHash"]):
        raise ValueError("Training expert or opponent mismatch")
    protocol = json.loads((ROOT/"config/player-agents/evaluation-v1.json").read_text())
    all_rows = []; opponents = []; summaries = []; rewards = []; lengths = []
    for group in range(4):
        path = folder/f"group-{group}.json"; report = json.loads(path.read_text())
        if file_hash(path) != completion["reportHashes"][path.name]: raise ValueError("Training report changed")
        if (report.get("status") != "complete" or report.get("error") is not None or len(report["games"]) != 1
                or report.get("version") != plan["version"] or report.get("split") != "training"
                or report["evaluationPlanHash"] != file_hash(plan_path) or report["group"] != group):
            raise ValueError("Incomplete or changed training report")
        for key in ("sourceHash", "gateHash", "actorHash", "shortActorHash", "collectorHash", "contactModelHash",
                    "baselineManifestHash", "protocolHash", "opponentHash", "opponentActorHash", "opponentMode",
                    "sampledSelector", "sampledActor", "logitScale", "explorationFloor"):
            if report[key] != plan[key]: raise ValueError("Training group provenance changed: " + key)
        if (report["configurationHash"] != metadata["configurationHash"] or report["physicsHz"] != 240
                or report["decisionTicks"] != 12 or report["actionLatencyTicks"] != 6
                or report["experimentalContactOverride"] or report["flatPitchOffsetDegrees"] != 0):
            raise ValueError("Training physics or control timing changed")
        validate_motor_metrics(report); outcome = validate_game_outcome(report)
        game = report["games"][0]; team = game["candidateTeam"]
        if game["gameSeed"] != 1071000+group or team != (group//2)%2:
            raise ValueError("Changed training game seed or side")
        if any(game["motorViolations"].values()): raise ValueError("An independent training motor violated a bound")
        candidate_game = copy.deepcopy(game)
        for player in range(4):
            if player//2 != team:
                candidate_game["decisionCounts"][player] = 0; candidate_game["firstDecisions"][player] = None
        validate_player_identities(candidate_game, bool(group&1), protocol)
        trace = (ROOT/game["decisionTracePath"]).resolve(); trace.relative_to(folder.resolve())
        if file_hash(trace) != game["decisionTraceHash"]: raise ValueError("Training decisions changed")
        records = [json.loads(line) for line in trace.read_text().splitlines()]
        owned = []; last_key = None; counts = [0]*4
        states = [(game["gameSeed"]*397+i*7919) ^ 0x9e3779b9 for i in range(4)]
        if game["selectorRandomSeedBySeat"] != [states[i] for i in game["identityBySeat"]]:
            raise ValueError("Selector RNG identity mismatch")
        for index, row in enumerate(records):
            player = index%4; key = (row["rally"], row["observationTick"])
            if (row["player"] != player or row["observationPlayer"] != player
                    or row["identity"] != game["identityBySeat"][player] or row["gameSeed"] != game["gameSeed"]
                    or row["candidateTeam"] != team or row["applyTick"] != row["observationTick"]+6
                    or row["observationTick"] % 12 or not 0 <= row["rally"] < game["rallies"]
                    or (player and key != last_key)):
                raise ValueError("Four-player training decision ownership changed")
            last_key = key; counts[player] += 1
            if player//2 == team:
                if row["executedBy"] != "selector" or row["opponentSample"] is not None:
                    raise ValueError("Privileged or opponent action entered candidate training")
                identity = row["identity"]; states[identity], draw = next_draw(states[identity])
                if row["selectorDraw"] != draw or row["selectedExpert"] != int(draw < row["shortProbability"]):
                    raise ValueError("Sampled selector RNG or choice differs")
                owned.append(row)
            else:
                if row["executedBy"] != "older-opponent" or row["selectedExpert"] != -1 or row["opponentSample"] is None:
                    raise ValueError("Older opponent was replaced")
                opponents.append(row)
        if counts != game["decisionCounts"] or len(records)%4: raise ValueError("Missing training decisions")
        replay_counts = validate_trace(owned, candidate_game)
        rewards.append(1 if game["winner"] == team else -1); lengths.append(len(owned)); all_rows.extend(owned)
        summaries.append(dict(group=group, score=game["score"], won=game["winner"] == team,
                              rallies=game["rallies"], **outcome, **replay_counts, traceHash=game["decisionTraceHash"]))
    with torch.no_grad():
        for offset in range(0, len(all_rows), 1024):
            rows = all_rows[offset:offset+1024]; x = torch.tensor([r["observation"] for r in rows])
            logits = gate(x); choice = torch.tensor([r["selectedExpert"] for r in rows]); logp, probability = likelihood(logits, choice)
            outputs = torch.where(choice[:, None].bool(), experts[1](x), experts[0](x))
            for i, row in enumerate(rows):
                for actual, expected in ((row["gateLogit"], logits[i]), (row["shortProbability"], probability[i]),
                                         (row["selectorLogProbability"], logp[i])):
                    if not math.isfinite(actual) or abs(actual-float(expected)) > .0001:
                        raise ValueError("Selector likelihood does not replay")
                out = outputs[i]
                validate_replayed_action(row["action"], Actor.movement(out[:2]), bool(out[2] >= 0), int(out[3:].argmax()))
        for offset in range(0, len(opponents), 1024):
            rows = opponents[offset:offset+1024]; x = torch.tensor([r["observation"] for r in rows])
            raw = torch.tensor([[r["opponentSample"]["rawX"], r["opponentSample"]["rawZ"]] for r in rows])
            attempt = torch.tensor([r["action"]["attempt"] for r in rows], dtype=torch.float32)
            shots = torch.tensor([r["action"]["shot"] for r in rows])
            logp, _ = log_probability(experts[0], x, raw, attempt, shots)
            for i, row in enumerate(rows):
                validate_opponent_record(row, raw[i], logp[i])
    result = dict(status="verified", folder=str(folder), planHash=file_hash(plan_path), completionHash=file_hash(folder/"completion.json"),
                  gateHash=plan["gateHash"], games=summaries, wins=sum(r==1 for r in rewards),
                  candidateRows=len(all_rows), opponentRows=len(opponents), fourPlayerMotorChecksPassed=True,
                  limitation="Training-only opponent curriculum. Not baseline or held-out match strength.")
    return gate, metadata, all_rows, game_weights(rewards, lengths), result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder", type=Path)
    args = parser.parse_args(); print(json.dumps(verify(args.folder)[-1], indent=2))
