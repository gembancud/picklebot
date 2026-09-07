"""Verify complete development games and every player-local selector decision."""
import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path

import torch

from player_actor import ROOT, file_hash, source_hash
from player_skill_gate import SkillGate, load_experts, selected_outputs
from player_skill_gate_audit import validate_selection

spec = importlib.util.spec_from_file_location("player_compare_models", ROOT/"scripts/player-compare-models.py")
comparison = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparison)


def validate_trace(records, game):
    """Keep the source split, owner, identity and 20 Hz ordering explicit."""
    counts = [0]*4; selections = [0, 0]; switches = [0]*4; previous = {}
    previous_key = None; pair = None; first = {}
    team = game["candidateTeam"]
    for row in records:
        player = row.get("player"); tick = row.get("observationTick"); rally = row.get("rally")
        if (type(player) is not int or player//2 != team or row.get("candidateTeam") != team
                or row.get("gameSeed") != game["gameSeed"] or row.get("observationPlayer") != player
                or row.get("identity") != game["identityBySeat"][player]
                or type(tick) is not int or tick < 0 or tick % 12 or row.get("applyTick") != tick+6
                or type(rally) is not int or not 0 <= rally < game["rallies"]):
            raise ValueError("Selector trace ownership, split, identity or timing changed")
        key = (rally, tick)
        if pair is None:
            if player != team*2 or (previous_key is not None and key <= previous_key):
                raise ValueError("Selector decision pair order changed")
            if previous_key is not None and rally == previous_key[0] and tick != previous_key[1]+12:
                raise ValueError("Missing selector decision tick")
            pair = key
        else:
            if player != team*2+1 or key != pair:
                raise ValueError("Missing simultaneous teammate selector decision")
            previous_key = pair; pair = None
        selected = row.get("selectedExpert")
        if type(selected) is not int or selected not in (0, 1):
            raise ValueError("Invalid expert selection")
        if player in previous and previous[player] != selected: switches[player] += 1
        previous[player] = selected
        counts[player] += 1; selections[selected] += 1
        first.setdefault(player, row)
    if (pair is not None or not records or counts != game["decisionCounts"]
            or selections != game["expertSelections"] or switches != game["expertSwitches"]):
        raise ValueError("Selector trace counts or switches changed")
    for player, row in first.items():
        summary = game["firstDecisions"][player]
        for key in ("player", "identity", "observationPlayer", "observationTick", "applyTick", "action"):
            if row[key] != summary[key]:
                raise ValueError("First selector action differs from game summary")
    return dict(decisions=len(records), expertSelections=selections, expertSwitches=switches)


def validate_game_outcome(report):
    game = report["games"][0]; winner = game["winner"]; score = game["score"]; rallies = report["rallies"]
    if (not game["complete"] or winner not in (0, 1) or len(score) != 2
            or any(type(s) is not int or s < 0 for s in score)
            or score[winner] < 11 or score[winner]-score[1-winner] < 2
            or len(rallies) != game["rallies"] or not rallies or rallies[-1]["score"] != score):
        raise ValueError("Incomplete game or inconsistent final score")
    hits = [0]*4; previous_score = [0, 0]; truncated = 0
    for rally in rallies:
        if (rally["gameSeed"] != game["gameSeed"] or rally["candidateTeam"] != game["candidateTeam"]
                or rally["winner"] not in (-1, 0, 1) or len(rally["legalHits"]) != 4):
            raise ValueError("Rally ownership or result changed")
        if rally["winner"] == -1:
            # Existing protocol truncation makes no point. A later completed
            # game can contain such rallies; they must remain in the denominator.
            seconds = rally.get("seconds")
            if (rally.get("fault") != "None" or type(seconds) not in (int, float)
                    or not math.isfinite(seconds) or not 30 <= seconds <= 35
                    or rally["score"] != previous_score):
                raise ValueError("Invalid no-point time-limit rally")
            truncated += 1
        previous_score = rally["score"]
        for i, n in enumerate(rally["legalHits"]):
            if type(n) is not int or n < 0: raise ValueError("Invalid rally hit count")
            hits[i] += n
    if hits != game["metrics"]["legalHits"]:
        raise ValueError("Rally and game hit counts disagree")
    # Frozen-baseline motor failures remain reported, not attributed to the
    # candidate or silently removed. The candidate includes scripted serves.
    if any(n != 0 for key, n in game["motorViolations"].items() if key.startswith("candidate ")):
        raise ValueError("Candidate motor violation in complete game")
    return dict(truncatedRallies=truncated)


def audit(folder):
    torch.set_num_threads(2)
    plan = json.loads((folder/"evaluation-plan.json").read_text())
    if plan.get("version") != "player-skill-gate-games-v1":
        raise ValueError("Expected explicit selector development games")
    comparison.validate_schedule(plan, 1141000)
    gate_path = (ROOT/plan["gatePath"]).resolve(); gate_path.relative_to(ROOT)
    if file_hash(gate_path) != plan["gateHash"]:
        raise ValueError("Selector checkpoint changed")
    gate, metadata = SkillGate.load_export(gate_path); gate.eval(); experts = load_experts(metadata)
    if metadata["sourceHash"] != source_hash() or metadata["sourceHash"] != plan["sourceHash"]:
        raise ValueError("Selector runtime changed")
    if (plan["olderExpertPath"] != metadata["experts"][0]["path"]
            or plan["actorHash"] != metadata["experts"][0]["sha256"]
            or plan["shortActorPath"] != metadata["experts"][1]["path"]
            or plan["shortActorHash"] != metadata["experts"][1]["sha256"]):
        raise ValueError("Selector uses different frozen experts")
    for key in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
        if key in plan and plan[key] != metadata[key]:
            raise ValueError("Selector game provenance differs: " + key)
    verified = comparison.verify_run(folder, ROOT/plan["olderExpertPath"], 1141000, source_hash())
    completion = json.loads((folder/"completion.json").read_text())
    for key in ("gateHash", "shortActorHash"):
        if completion[key] != plan[key]: raise ValueError("Terminal selector provenance changed")
    summaries = []; replay = []
    for group in range(8):
        report = json.loads((folder/f"group-{group}.json").read_text())
        if report.get("version") != "player-skill-gate-games-v1":
            raise ValueError("Selector group schema changed")
        if report.get("method") != metadata["method"]:
            raise ValueError("Selector training method differs from its checkpoint")
        for key in ("gatePath", "gateHash", "shortActorPath", "shortActorHash"):
            if report[key] != plan[key]: raise ValueError("Selector group provenance changed")
        if report["configurationHash"] != metadata["configurationHash"]:
            raise ValueError("Selector physics configuration changed")
        outcomes = validate_game_outcome(report)
        game = report["games"][0]
        trace = (ROOT/game["decisionTracePath"]).resolve(); trace.relative_to(folder.resolve())
        if file_hash(trace) != game["decisionTraceHash"]:
            raise ValueError("Selector game decisions changed")
        records = [json.loads(line) for line in trace.read_text().splitlines()]
        summaries.append(dict(group=group, **outcomes, **validate_trace(records, game), traceHash=game["decisionTraceHash"]))
        replay.extend(records)
    with torch.no_grad():
        for offset in range(0, len(replay), 1024):
            batch = replay[offset:offset+1024]
            logits, selected, outputs = selected_outputs(gate, experts, torch.tensor([r["observation"] for r in batch]))
            for i, row in enumerate(batch): validate_selection(row, logits[i], selected[i], outputs[i])
    verified["olderExpertHash"] = verified.pop("actorHash")
    verified["olderExpertTrainingSourceHash"] = verified.pop("trainingSourceHash")
    verified["historicalOlderExpert"] = verified.pop("historicalCandidate")
    return dict(**verified, gateHash=plan["gateHash"], shortExpertHash=plan["shortActorHash"],
                gateTrainingSourceHash=metadata["sourceHash"],
                declaredTrainingMethod=metadata["method"],
                selectorReplayDecisions=len(replay), selectorGames=summaries,
                truncatedRallies=sum(g["truncatedRallies"] for g in summaries),
                limitation="Development match results only. Training method is recorded separately. No promotion or final acceptance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder", type=Path)
    args = parser.parse_args(); print(json.dumps(audit(args.folder), indent=2))
