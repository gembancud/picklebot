"""Audit fixed-policy repeat traces. This is not a match-strength acceptance test."""
import argparse
import gzip
import itertools
import json
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_skill_retention import validate_replayed_action


def differences(left, right, path="", limit=32):
    result = []

    def visit(a, b, key):
        if len(result) >= limit:
            return
        if type(a) is not type(b):
            result.append(dict(path=key, left=a, right=b))
        elif isinstance(a, dict):
            for field in sorted(a.keys() | b.keys()):
                if field not in a or field not in b:
                    result.append(dict(path=key+"."+field, missing="left" if field not in a else "right"))
                else:
                    visit(a[field], b[field], key+"."+field)
                if len(result) >= limit:
                    break
        elif isinstance(a, list):
            if len(a) != len(b):
                result.append(dict(path=key+".length", left=len(a), right=len(b)))
            for index, (x, y) in enumerate(zip(a, b)):
                visit(x, y, f"{key}[{index}]")
                if len(result) >= limit:
                    break
        elif a != b:
            result.append(dict(path=key, left=a, right=b))

    visit(left, right, path)
    return result


def records(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        for line in stream:
            yield json.loads(line)


def first_difference(left, right):
    previous = None
    for index, (a, b) in enumerate(itertools.zip_longest(left, right)):
        if a != b:
            return dict(equal=False, identicalPrefixRows=index,
                        differences=differences(a, b), previousEqualRow=previous,
                        leftRow=a, rightRow=b)
        previous = a
    return dict(equal=True)


def audit(folder):
    torch.set_num_threads(2)
    plan_path = folder/"plan.json"
    plan = json.loads(plan_path.read_text())
    done = json.loads((folder/"completion.json").read_text())
    if (plan["version"] != "player-fixed-policy-repeat-v1" or plan["split"] != "development-diagnostic"
            or not 1100000 <= plan["seed"] < 1200000 or plan["repeats"] != 3
            or plan["candidateTeam"] != 0 or plan["sampledActor"] or plan["sampledBaseline"]
            or plan["identityBySeat"] != [0, 1, 2, 3]
            or done["status"] != "complete" or done["planHash"] != file_hash(plan_path)
            or done["sourceHash"] != plan["sourceHash"] or plan["sourceHash"] != source_hash()):
        raise ValueError("Repeat plan or completion provenance mismatch")
    for path, expected in plan["hashes"].items():
        if file_hash(ROOT/path) != expected:
            raise ValueError("Input changed: " + path)
    if file_hash(folder/"collector.cs") != plan["hashes"]["scripts/player-fixed-policy-repeat.cs"]:
        raise ValueError("Collector snapshot changed")
    actor, _ = Actor.load_export(ROOT/"artifacts/player-agents/ppo-20260907-032230/actor.json")
    actor.eval()
    summaries = []
    for run in range(plan["repeats"]):
        report_path = folder/f"run-{run}.json"
        report = json.loads(report_path.read_text())
        if done["reportHashes"][report_path.name] != file_hash(report_path):
            raise ValueError("Report changed")
        for suffix, key in [("steps.jsonl.gz", "stepsHash"), ("decisions.jsonl", "decisionsHash")]:
            if file_hash(folder/f"run-{run}.{suffix}") != report[key]:
                raise ValueError("Trace changed")
        if report["run"] != run or report["seed"] != plan["seed"]:
            raise ValueError("Report ownership mismatch")
        if not report["complete"]:
            raise ValueError("Incomplete game retained: " + report["reason"])
        score, winner = report["score"], report["winner"]
        if winner not in (0, 1) or score[winner] < 11 or score[winner]-score[1-winner] < 2:
            raise ValueError("Invalid game score")
        count = 0; previous_rally = -1; previous_tick = -1; step_count = 0
        for row in records(folder/f"run-{run}.steps.jsonl.gz"):
            state = row["state"]; rally = state["rally"]; tick = state["tick"]
            if rally == previous_rally:
                if tick != previous_tick+1:
                    raise ValueError("Missing physics tick")
                step_count += 1
            elif rally != previous_rally+1 or tick != 0:
                raise ValueError("Invalid rally reset")
            previous_rally, previous_tick = rally, tick
            count += 1
        if step_count != report["steps"] or count != report["steps"]+report["completedRallies"]:
            raise ValueError("Physics trace count mismatch")
        decisions = list(records(folder/f"run-{run}.decisions.jsonl"))
        if len(decisions) != report["decisionCount"] or len(decisions) % 2:
            raise ValueError("Decision trace count mismatch")
        for a, b in zip(decisions[::2], decisions[1::2]):
            if (a["player"] != 0 or b["player"] != 1 or a["identity"] != 0 or b["identity"] != 1
                    or a["rally"] != b["rally"] or a["observationTick"] != b["observationTick"]
                    or a["observationTick"] % 12 or a["applyTick"] != a["observationTick"]+6
                    or b["applyTick"] != b["observationTick"]+6):
                raise ValueError("Independent decision ownership or timing mismatch")
        with torch.no_grad():
            for offset in range(0, len(decisions), 1024):
                batch = decisions[offset:offset+1024]
                outputs = actor(torch.tensor([r["observation"] for r in batch]))
                for row, output in zip(batch, outputs):
                    validate_replayed_action(row["action"], Actor.movement(output[:2]),
                                             bool(output[2] >= 0), int(output[3:].argmax()))
        summaries.append(dict(run=run, score=score, rallies=report["completedRallies"],
                              steps=report["steps"], decisions=len(decisions),
                              candidateLegalReturns=sum(report["metrics"]["legalHits"][:2])))
    pairs = []
    for other in (1, 2):
        pairs.append(dict(left=0, right=other,
            physics=first_difference(records(folder/"run-0.steps.jsonl.gz"), records(folder/f"run-{other}.steps.jsonl.gz")),
            decisions=first_difference(records(folder/"run-0.decisions.jsonl"), records(folder/f"run-{other}.decisions.jsonl"))))
    return dict(folder=str(folder), sourceHash=plan["sourceHash"], planHash=done["planHash"],
                completionHash=file_hash(folder/"completion.json"), summaries=summaries, pairs=pairs,
                wallSeconds=done["wallSeconds"], provenanceAndStructurePassed=True,
                replayedSinglePolicyDecisions=sum(r["decisions"] for r in summaries),
                exactRepeat=all(p["physics"]["equal"] and p["decisions"]["equal"] for p in pairs),
                limitation="Same-seed development diagnosis. Exact equality covers recorded public state only. No policy gain or internal physics-state claim.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    print(json.dumps(audit(parser.parse_args().folder), indent=2))
