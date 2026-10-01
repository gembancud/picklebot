"""Freeze a systematic illustrative clip selection after the wide audit completes.

Reads repository evidence; writes only a new output directory below this workspace.
Does not run Unity, alter a ledger, or change any evaluation denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

MODEL = "ExecutionV1SmoothContinuedFinal01"
CAMPAIGN = "artifacts/hierarchy-v1/wide-movement-fixture-01"
SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"
FILES = ("episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "summary.json", "model-identity.json")
WORKSPACE = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--output-name", default="wide-movement-review-01")
    args = parser.parse_args()
    root = args.root.resolve()
    base = root / CAMPAIGN
    output_root = (WORKSPACE / "outputs").resolve()
    output = (output_root / args.output_name).resolve()
    require(output.is_relative_to(output_root) and output != output_root and not output.exists(), "Need a new workspace output directory")
    plan, analysis = read(base / "plan.json"), read(base / "audit/analysis.json")
    require(analysis["status"] == "complete_wide_movement_diagnostic" and analysis["diagnosticOnly"] is True
            and analysis["masteryAccepted"] is False, "Completed diagnostic is required before choosing clips")
    require(plan["sourceIdentity"] == analysis["sourceIdentity"] == SOURCE and plan["conditions"] == ["A", "B"], "Wrong source/condition plan")
    for relative, expected in analysis["inputSha256"].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and sha(path) == expected, f"Audited input changed: {relative}")
    require(read(root / "artifacts/player-v3/seed-ledger.json")["finalSeedsConsumed"] == [], "Final seeds changed")
    identity = plan["modelIdentities"][MODEL]
    require(identity["step"] == 1048609 and sha(root / identity["assetPath"]) == identity["modelHash"], "Wrong frozen selected model")
    fixtures = []
    for ordinal in range(0, 512, 64):
        fixtures.extend(read(base / f"fixture/wide-fixture-{ordinal:04d}.json")["rows"])
    descriptions = {row["seed"]:row for row in fixtures}
    require(len(descriptions) == 512, "Fixture reset coverage changed")
    by_condition, inputs, stages = {}, {}, []
    for condition in ("A",):
        folder = base / "evaluation" / MODEL / condition
        episodes = {row["seed"]:row for row in [json.loads(line) for line in (folder / "episodes.jsonl").read_text().splitlines() if line.strip()]}
        require(len(episodes) == 512 and set(episodes) == set(descriptions), "Reference episode coverage changed")
        by_condition[condition] = episodes
        for name in FILES:
            inputs[(folder/name).relative_to(root).as_posix()] = sha(folder/name)
        stages.append(dict(label=condition, condition=condition, task="movement-maintenance", firstSeed=plan["firstSeed"], seedCount=512,
                           arenas=8, referenceDirectory=folder.as_posix(), reference=(folder/"episodes.jsonl").as_posix(),
                           referenceHash=sha(folder/"episodes.jsonl")))
    selected, unavailable = [], []
    for direction in ("left", "right", "shallow", "deep"):
        for category, legal in (("legal-return", True), ("unsuccessful-return", False)):
            eligible = sorted(seed for seed, desc in descriptions.items() if desc["challenge"]
                              and desc["direction"] == direction
                              and (by_condition["A"][seed]["outcome"] == "legal_return") == legal)
            if not eligible:
                unavailable.append(dict(direction=direction, category=category, eligibleCount=0))
                continue
            seed = eligible[0]
            desc = descriptions[seed]
            selected.append(dict(seed=seed, direction=direction, nominalShiftCm=desc["centimetres"],
                                 task=desc["task"], player=desc["player"], categoryUnderA=category,
                                 eligibleCount=len(eligible), selectionRank=1,
                                 outcomes={"A":by_condition["A"][seed]["outcome"]}))
    require(selected, "No illustrative challenge cases")
    for stage in stages:
        stage["clipSeeds"] = [row["seed"] for row in selected]
    manifest = dict(version="wide-recording-selection-01", purpose="Illustrative actual-policy replay, not a new estimate of success rate",
                    model=identity["assetPath"], modelName=MODEL, modelHash=identity["modelHash"], checkpoint=identity["step"],
                    checkpointHash=identity["checkpointHash"], checkpointPath=identity["checkpoint"], sourceIdentity=SOURCE,
                    firstSeed=plan["firstSeed"], seedCount=512, stages=stages, physicalRecipe=plan["physicalRecipe"],
                    decisionSchedule="Eight arenas, alignedDecisions=false, interleavedRecovery=false, exact original ordinal schedule",
                    goalRecipe=dict(intent="PlayBall", movementTarget=False, targetLayout="two-regions", conditions=["A"], radius=1, rewardMode="linear-radius", legalTargetReward=.25),
                    selectionRule="For each canonical axis direction, choose the lowest seed with a legal return under A and the lowest seed without a legal return under A. Replay condition A. Missing categories remain unavailable; no substitution based on visual appeal.",
                    selected=selected, unavailable=unavailable, selectionWasOutcomeStratified=True,
                    statisticalDenominators="Keep the full512 attempts per condition in museum score cards. Clips deliberately include outcomes of both kinds and cannot estimate prevalence.",
                    fullReplayEpisodes=512, clipCount=len(selected), frameStrideTicks=12, physicsHz=240, fps=20,
                    referenceInputSha256=inputs, evaluationPlanHash=sha(base/"plan.json"), analysisHash=sha(base/"audit/analysis.json"),
                    preparationScriptSha256=sha(Path(__file__)), finalSeedsConsumed=False, masteryAccepted=False,
                    ledgerHash=sha(root/"artifacts/player-v3/seed-ledger.json"),
                    ledgerRequirement="Same reserved wide campaign and reset cases reused for diagnostic recording; no new allocation or ledger modification.")
    template = Path(__file__).with_name("wide_recording_capture.cs")
    capture = template.read_text(encoding="utf-8").replace("__DESTINATION__", '@"'+output.as_posix().replace('"','""')+'"')
    require("__DESTINATION__" not in capture, "Unresolved capture destination")
    manifest["captureTemplateSha256"] = sha(template)
    manifest["captureScriptSha256"] = hashlib.sha256(capture.encode("utf-8")).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    with (output/"manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    for name in ("source-records.json", "plan.json", "fixture-summary.json"):
        shutil.copyfile(base/name, output/name)
    shutil.copyfile(base/"audit/analysis.json", output/"evaluation-analysis.json")
    (output/"capture.cs").write_text(capture, encoding="utf-8", newline="")
    print(json.dumps(dict(output=str(output), selectedSeedCount=len(selected), clips=manifest["clipCount"], unavailable=unavailable,
                         simulationsRun=0, repositoryWrites=0), indent=2))


if __name__ == "__main__":
    main()
