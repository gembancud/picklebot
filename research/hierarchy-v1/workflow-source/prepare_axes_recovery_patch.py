"""Produce an unapplied source patch and old-evidence golden in this workspace."""
from pathlib import Path
from collections import Counter
import difflib
import hashlib
import json

root = Path("F:/dev/picklebot")
out = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
changes = {
    "Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs": "2fcf7a49663fe1a198f6c398c516369c2e4543f09c532664b9be09d4237640ac",
    "Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs": "7cfaafbf056491b831a786ae34d30a0ccfd534e6545d569c88ae5d1c7d05e57a",
}
replacements = {
    "Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs": [
        ("public static Episode For(int index,float lateralRange,float priorRange,float receiveDifficulty)",
         'public static Episode For(int index,float lateralRange,float priorRange,float receiveDifficulty,string focusPattern="lateral")'),
        ('if(index<0)throw new ArgumentOutOfRangeException(nameof(index));',
         'if(index<0)throw new ArgumentOutOfRangeException(nameof(index));\n            if(focusPattern!="lateral"&&focusPattern!="axes")throw new ArgumentException("Recovery focus must be lateral or axes.",nameof(focusPattern));'),
        ('left?"lateral-left":"lateral-right","focus",lateralRange*fraction,0);',
         'focusPattern=="axes"?"axes":left?"lateral-left":"lateral-right","focus",lateralRange*fraction,0);'),
        ('task!="movement-maintenance"||pattern!="lateral"||',
         'task!="movement-maintenance"||(pattern!="lateral"&&pattern!="axes")||'),
        ('Recovery mix requires solo lateral practice,', 'Recovery mix requires solo lateral or axes practice,'),
    ],
    "Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs": [
        ('PlayerRecoveryScheduleV3.For(index,MovementRange,MovementRehearsalRange,MaximumReturnDifficulty);',
         'PlayerRecoveryScheduleV3.For(index,MovementRange,MovementRehearsalRange,MaximumReturnDifficulty,MovementPattern);'),
    ],
}
patch = ""
files = {}
for relative, expected in changes.items():
    path = root / relative
    if sha(path) != expected:
        raise RuntimeError(f"Original source changed: {relative}")
    original = path.read_text(encoding="utf-8")
    proposed = original
    for before, after in replacements[relative]:
        if proposed.count(before) != 1:
            raise RuntimeError(f"Expected unique patch anchor: {before}")
        proposed = proposed.replace(before, after)
    patch += "".join(difflib.unified_diff(original.splitlines(True), proposed.splitlines(True),
                                        fromfile=f"a/{relative}", tofile=f"b/{relative}"))
    files[relative] = {"oldSha256": expected, "proposedLfSha256": hashlib.sha256(proposed.encode()).hexdigest(),
                       "proposedCrlfSha256": hashlib.sha256(proposed.replace("\n", "\r\n").encode()).hexdigest()}

campaign = root / "artifacts/hierarchy-v1/fresh-placement-01"
evaluation = campaign / "evaluation/ExecutionV1SmoothContinuedFinal01/A"
source = root / "artifacts/hierarchy-v1/smooth-distance-01/source-records.json"
report = read(evaluation / "report.json")
if report["sourceIdentity"] != "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9" or report["firstSeed"] != 1109593 or report["completedEpisodes"] != 256:
    raise RuntimeError("Golden cohort/source mismatch")
if not report["movementRecoveryMix"] or report["movementPattern"] != "lateral":
    raise RuntimeError("Golden is not the old lateral recovery cohort")
episodes = [json.loads(line) for line in (evaluation / "episodes.jsonl").read_text().splitlines() if line.strip()]
rows = []
for episode in sorted(episodes, key=lambda row: row["seed"]):
    index = episode["seed"] - report["firstSeed"]
    pattern, extent = episode["movementPattern"], episode["movementRange"]
    # Classify immutable recorded reset fields. Do not reimplement For(index).
    group = "focus" if pattern in ("lateral-left", "lateral-right") else "prior" if extent > 0 else "familiar"
    rows.append({"index": index, "seed": episode["seed"], "player": episode["player"], "task": episode["task"],
                 "pattern": pattern, "range": extent, "difficulty": episode["feedDifficulty"],
                 "serveFromLeft": episode["serveFromLeft"], "group": group,
                 "resetRejections": episode["resetRejections"]})
if [row["index"] for row in rows] != list(range(256)) or any(row["player"] != row["index"] % 4 for row in rows):
    raise RuntimeError("Golden does not contain every original reset and seat")
if Counter(row["group"] for row in rows) != {"familiar": 64, "prior": 64, "focus": 128}:
    raise RuntimeError("Unexpected golden group composition")
golden = {"status": "recorded_old_reset_descriptors", "sourceIdentity": report["sourceIdentity"],
          "firstSeed": report["firstSeed"], "seedCount": 256, "focusRange": report["movementRange"],
          "priorRange": report["movementRehearsalRange"], "receiveDifficulty": report["maximumReturnDifficulty"],
          "origin": "Immutable reset fields from all256 completed episodes; outcomes/actions are excluded; no synthetic For() implementation.",
          "inputSha256": {path.relative_to(root).as_posix(): sha(path) for path in
                          (evaluation / "episodes.jsonl", evaluation / "report.json", evaluation / "model-identity.json", source)},
          "rows": rows}
patch_path, golden_path = out / "axes-recovery-opt-in.patch", out / "axes-recovery-golden.json"
for path, text in [(patch_path, patch), (golden_path, json.dumps(golden, indent=2)+"\n")]:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
metadata = {"status": "prepared_not_applied", "oldSourceIdentity": report["sourceIdentity"], "changedFiles": files,
            "unchangedValidatorCaller": {"path": "Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs",
                                         "sha256": sha(root / "Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs"),
                                         "reason": "Already passes manifest.movementPattern to the same shared Validate() method."},
            "patchSha256": sha(patch_path), "goldenSha256": sha(golden_path), "goldenRows": 256,
            "defaultMode": "lateral; exact old descriptors retained", "optInMode": "axes for focus group only",
            "bodyRewardsObservationsInterleavingChanged": False, "unityExecuted": False, "sourceApplied": False}
with (out / "axes-recovery-patch.json").open("x", encoding="utf-8") as stream:
    json.dump(metadata, stream, indent=2)
    stream.write("\n")
print(json.dumps({"patch": str(patch_path), "patchHash": sha(patch_path), "goldenHash": sha(golden_path), "sourceApplied": False}))
