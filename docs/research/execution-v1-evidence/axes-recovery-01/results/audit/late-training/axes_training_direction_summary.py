"""Summarize current axes-run early/late quarters; no models or rollouts."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

root = Path("F:/dev/picklebot")
base = root / "artifacts/hierarchy-v1/axes-recovery-01/training"
out = Path(__file__).resolve().parent / "axes-training-late-summary.json"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows = lambda p: [json.loads(line) for line in p.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
verification = read(base / "verification.json")
assert verification["status"] == "completed_continuation_check" and verification["experiences"] == 2097159
phases = defaultdict(list)
windows, hashes = [], {}
directions = {3: "left", 5: "right", 1: "shallow", 7: "deep"}
for worker in range(8):
    folder = base / f"worker-{worker:02}"
    paths = [folder / name for name in ("episodes.jsonl", "execution-goals.jsonl", "worker-startup.json", "report.json")]
    episodes, goals = rows(paths[0]), rows(paths[1])
    startup, report = read(paths[2]), read(paths[3])
    assert startup["workerId"] == worker and startup["trainerRequired"] and startup["status"] == "configured"
    assert startup["sourceIdentity"] == report["sourceIdentity"] == verification["sourceIdentity"]
    assert report["trainerConnected"] and report["split"] == "training" and not report["failure"]
    assert report["movementPattern"] == "axes" and report["movementRange"] == .0625
    assert len(episodes) == len(goals) == report["completedEpisodes"]
    for episode, goal in zip(episodes, goals):
        assert episode["seed"] == goal["seed"] and episode["player"] == goal["player"]
        assert goal["legalLanding"] == (episode["outcome"] in ("legal_return", "legal_serve"))
    quarter = len(episodes) // 4
    windows.append({"worker": worker, "allEpisodes": len(episodes), "quarterEpisodes": quarter,
                    "earlyCompletionRows": [0, quarter], "lateCompletionRows": [len(episodes)-quarter, len(episodes)]})
    paired = list(zip(episodes, goals))
    for phase, selected in (("early", paired[:quarter]), ("late", paired[-quarter:])):
        for episode, goal in selected:
            if episode["movementPattern"] != "axes":
                continue
            cm = round(400 * episode["movementRange"], 5)
            assert cm in (6.25, 12.5, 18.75, 25)
            phases[phase].append({"worker": worker, "seed": episode["seed"], "player": episode["player"],
                                  "task": episode["task"], "direction": directions[episode["movementRegion"]], "cm": cm,
                                  "contact": episode["faceContact"], "crossedNet": episode["netCrossed"],
                                  "legal": goal["legalLanding"], "target": goal["targetHit"],
                                  "instruction": "A" if goal["targetX"] < 0 else "B",
                                  "outcome": episode["outcome"], "rootPath": episode["travelBeforeContact"][episode["player"]]})
    hashes.update({path.relative_to(root).as_posix(): sha(path) for path in paths})


def summarize(values):
    n = len(values)
    counts = {name: sum(row[name] for row in values) for name in ("contact", "crossedNet", "legal", "target")}
    return {"attempts": n, **counts, "legalRate": counts["legal"]/n if n else None,
            "contactRate": counts["contact"]/n if n else None, "targetRate": counts["target"]/n if n else None,
            "outcomes": dict(Counter(row["outcome"] for row in values)),
            "meanRootPath": sum(row["rootPath"] for row in values)/n if n else None}


def grouped(values, columns):
    cells = defaultdict(list)
    for row in values:
        cells[tuple(row[key] for key in columns)].append(row)
    return [{**dict(zip(columns, key)), **summarize(group)} for key, group in sorted(cells.items())]


summary = {"scope": "Only the completed axes-recovery-01 run after1048609, not copied parent history",
           "windowDefinition": "Equal floor(N/4) earliest and latest completed episodes separately within each worker; then retain actual axes focus rows. Completion order is not exact wall time/global policy step.",
           "initialStep": verification["initialStep"], "finalStep": verification["experiences"], "workers": windows,
           "inputSha256": hashes,
           "phases": {phase: {"total": summarize(values), "byDirection": grouped(values, ["direction"]),
                              "byDirectionDistance": grouped(values, ["direction", "cm"]),
                              "byTaskDirection": grouped(values, ["task", "direction"]),
                              "byDirectionInstruction": grouped(values, ["direction", "instruction"])} for phase, values in phases.items()},
           "limitations": ["Changing stochastic training policies and different reset draws; these counts do not measure the frozen final policy.",
                           "Completion windows are per-worker episode quantiles, not synchronized global-step slices.",
                           "Target success depends on both incoming geometry and requested A/B instruction; all attempts remain in each denominator."]}
for relative, expected in hashes.items():
    assert sha(root / relative) == expected
with out.open("x", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2, allow_nan=False)
    handle.write("\n")
print(json.dumps({"output": str(out), "earlyDirections": summary["phases"]["early"]["byDirection"],
                  "lateDirections": summary["phases"]["late"]["byDirection"],
                  "lateDirectionDistance": summary["phases"]["late"]["byDirectionDistance"],
                  "lateTaskDirection": summary["phases"]["late"]["byTaskDirection"]}, indent=2))
