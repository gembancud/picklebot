"""Preserve the complete fresh-placement-01 screen, without filtering or promotion.

Use the pinned Python, --root <repository>, and optionally --scripts <workspace
directory or a script in it>. All source inputs are read-only. Destinations are
exclusive; a partial archive is preserved and marked instead of overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import traceback


CAMPAIGN = "artifacts/hierarchy-v1/fresh-placement-01"
EVIDENCE = "docs/research/execution-v1-evidence/fresh-placement-01"
WORKFLOW = "research/hierarchy-v1/fresh-placement-01"
REPORT = "docs/research/execution-v1-fresh-placement.md"
MODELS = ("ExecutionV1Initial", "ExecutionV1SmoothContinuedFinal01")
CONDITIONS = ("A", "B", "random")
EVAL_FILES = {"episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "summary.json", "model-identity.json"}
SOURCE = "5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, relative):
    path = root / relative
    require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root), f"Path escapes repository: {relative}")
    return path


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_text(path, text):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def jsonl_count(path):
    return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines())


def render_report(analysis, plan):
    initial, candidate = MODELS
    counts = analysis["summaries"]["all"]
    novelty = analysis["novelty"]
    reset = analysis["causalResetWeighted"]["all"][candidate]["assignmentGain"]
    unique = analysis["causalUniqueClusterWeighted"]["all"][candidate]
    n = analysis["seedCount"]
    labels = {initial: "Initializer", candidate: f"Candidate ({plan['modelIdentities'][candidate]['step']:,} experiences)"}
    lines = ["# Fresh placement development screen", "",
             f"Both frozen models were evaluated anew on **{n} paired base resets**, each repeated under target A, target B and random targets. The candidate is fixed at {plan['modelIdentities'][candidate]['step']:,} training experiences; this campaign adds evaluation only.", "",
             f"The predeclared diagnostic screen **{'passed' if analysis['screen']['promising'] else 'did not pass'}**. No model promotion or drill-mastery acceptance follows from this result.", "",
             f"| Model | A legal / target hits (of {n}) | B legal / target hits (of {n}) | Random legal / target hits (of {n}) |",
             "|---|---:|---:|---:|"]
    for model in MODELS:
        lines.append("| " + labels[model] + " | " + " | ".join(f"{counts[model][condition]['legal']} / {counts[model][condition]['targets']}" for condition in CONDITIONS) + " |")
    lines += ["", "Target hits require a legal landing within 1 m for A/B or 1.5 m for random targets. Nonzero training reward is not a target hit. A/B/random are repeated conditions of the same base resets, not three independent sets of situations.", "",
              "| Candidate assignment-gain estimate | Mean | Pointwise 95% interval | Weighting |",
              "|---|---:|---:|---|",
              f"| Paired reset estimate | {reset['mean']:.5f} | [{reset['ci95'][0]:.5f}, {reset['ci95'][1]:.5f}] | Every base reset equally |",
              f"| Unique-observation cluster estimate | {unique['mean']:.5f} | [{unique['ci95'][0]:.5f}, {unique['ci95'][1]:.5f}] | Average within identical observations, then each cluster equally |", "",
              "Assignment gain measures requested-versus-opposite-region success on paired feeds. Target-blind shots cancel; attempts without legal landings contribute zero. The two estimates use different weights and need not agree. Their intervals do not establish independent training replication or broad generalization.", "",
              "| Predeclared check | Result |", "|---|---|"]
    descriptions = {
        "resetWeightedAssignmentGainCiLowerAboveZero": "Reset-weighted gain interval lower bound above zero",
        "uniqueClusterWeightedAssignmentGainCiLowerAboveZero": "Unique-cluster gain interval lower bound above zero",
        "bothRegionTargetRatesExceedInitializer": "A and B target-hit rates both exceed the initializer",
        "noDrillLegalDropGreaterThanFivePercentagePoints": "No drill loses more than 5 percentage points of legality in any condition",
    }
    require(set(analysis["screen"]["tests"]) == set(descriptions), "Unexpected screen tests; report must be updated explicitly")
    for key, description in descriptions.items():
        lines.append(f"| {description} | {'Pass' if analysis['screen']['tests'][key] else 'Fail'} |")
    lines += ["", "The retention limit uses per-drill point estimates; it is not a statistical noninferiority guarantee."]
    failed_retention = [row for row in analysis["screen"]["retentionChecks"] if row["mean"] < -.05 - 1e-12]
    if failed_retention:
        lines += ["", "| Retention guard triggered | Candidate minus initializer | Paired 95% interval |", "|---|---:|---:|"]
        for row in failed_retention:
            lines.append(f"| {row['drill']} / {row['condition']} | {100 * row['mean']:+.2f} percentage points | [{100 * row['ci95'][0]:+.2f}, {100 * row['ci95'][1]:+.2f}] percentage points |")
        lines += ["", "These point estimates trigger the predeclared guard. Wide intervals that include zero do not establish a reliable regression; all per-drill checks remain available in the analysis."]
    lines += ["",
              "## Requested targets and actual landings", "",
              "Each cell lists **in A / in B / legal outside both / no legal landing**. A/B means shallower/deeper for serves and canonical left/right for rally and receiving shots. Every attempt remains included.", "",
              "| Drill | Model | Requested A | Requested B |", "|---|---|---:|---:|"]
    for drill in ("stationary-serve", "receive-feed", "rally-air-feed", "rally-bounce-feed"):
        for model in MODELS:
            matrix = analysis["targetConfusionMatrices"][f"drill/{drill}"][model]
            cells = [" / ".join(str(matrix[condition][key]) for key in ("legalInA", "legalInB", "legalOutsideBoth", "illegalOrNoLegalLanding")) for condition in ("A", "B")]
            lines.append(f"| {drill} | {'Initializer' if model == initial else 'Candidate'} | {cells[0]} | {cells[1]} |")
    lines += ["", "## What was physically new", "",
              f"The {n} reset IDs produced **{novelty['currentUniquePhysicalObservations']} distinct first-observation vectors**. Compared with the pinned prior set of {novelty['priorUniquePhysicalObservations']} vectors, **{novelty['exactNovelResets']} resets were exactly novel** and **{novelty['exactRepeatedResets']} repeated a prior vector**. This is observed-state novelty, not proof of new hidden simulator states or harder shots.", "",
              "| Drill | Base resets | Exactly novel observations (resets) | Repeated observations (resets) |", "|---|---:|---:|---:|"]
    for drill, row in novelty["byDrill"].items():
        lines.append(f"| {drill} | {row['resets']} | {row['exactNovelResets']} | {row['exactRepeatedResets']} |")
    nearest = novelty["nearestPriorMaximumAbsoluteNormalizedFeatureDifference"]
    lines += ["", f"{nearest['resetsAtOrBelow1eMinus5']}/{n} resets are within a maximum normalized-feature difference of 0.00001 from a prior observation; {nearest['resetsAtOrBelow1eMinus4']}/{n} are within 0.0001. These thresholds are descriptive, are not measured in metres, and exclude no cases.", "",
              "| Descriptive subset | Base resets | Candidate A legal / targets | Candidate B legal / targets | Reset-weighted gain [95% interval] |", "|---|---:|---:|---:|---:|"]
    for label, group in (("Exactly novel", "novelty/exact-novel"), ("Exactly repeated", "novelty/exact-repeated")):
        if group in analysis["summaries"]:
            subset = analysis["summaries"][group][candidate]
            subset_gain = analysis["causalResetWeighted"][group][candidate]["assignmentGain"]
            lines.append(f"| {label} | {subset['A']['attempts']} | {subset['A']['legal']} / {subset['A']['targets']} | {subset['B']['legal']} / {subset['B']['targets']} | {subset_gain['mean']:.5f} [{subset_gain['ci95'][0]:.5f}, {subset_gain['ci95'][1]:.5f}] |")
    lines += ["", "Exact-novel/repeated subsets and their per-drill results are descriptive. The predeclared screen uses all cases. A repeated first observation can conceal other state differences, while an exactly novel vector can differ only slightly.", "",
              "## Coverage still needed for mastery", "",
              "This remains the existing small-shift recovery recipe. It does not deliberately cover broad left/right/shallow/deep footwork, independent start positions and flight times, varied mandatory-bounce receiver contexts, or kitchen-line/momentum decisions. An accepted shifted-ball return does not prove that substantial body movement was required.", "",
              "Actual `incomingServeLanded` and `contactWasVolley` indicators are included in the analysis. Rally-bounce feeds already permit volleys and are not substitutes for mandatory-bounce receiving. A false volley flag without contact is not counted as a groundstroke.", "",
              "The goal still requires per-skill and per-variation acceptance thresholds, repeat evidence with uncertainty, preservation in the same checkpoint, and representative movement recordings for human review. Passing this screen alone cannot satisfy those requirements. Final acceptance seeds remain untouched; freshness here is limited to the recorded V3 ledger.", "",
              "[Complete analysis](execution-v1-evidence/fresh-placement-01/analysis.json) · [Frozen plan](execution-v1-evidence/fresh-placement-01/plan.json) · [Input archive and coverage](execution-v1-evidence/fresh-placement-01/archive-manifest.json) · [Coverage audit](drill-mastery-coverage.md)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--scripts", type=Path, default=Path(__file__).resolve().parent,
                        help="Workspace script directory, or a script located inside it")
    args = parser.parse_args()
    root = args.root.resolve()
    here = args.scripts.resolve()
    if here.is_file():
        here = here.parent
    require(here.is_dir(), "Workspace script directory is missing")
    base, dest, workflow, report_path = (inside(root, value) for value in (CAMPAIGN, EVIDENCE, WORKFLOW, REPORT))
    require(not dest.exists() and not workflow.exists() and not report_path.exists(), "Archive/report destinations must be exclusive; preserve previous/partial outputs")
    analysis = read(base / "audit/analysis.json")
    plan, source, allocation = (read(base / name) for name in ("plan.json", "source-records.json", "allocation.json"))
    require(analysis["status"] == "complete_fresh_development_screen", "Fresh analysis is incomplete")
    require(analysis["promoted"] is False and analysis["masteryAccepted"] is False and analysis["finalSeedsConsumed"] is False, "Unexpected acceptance or final-seed claim")
    require(plan["automaticPromotion"] is False and plan["masteryAccepted"] is False and plan["finalSeedsConsumed"] is False, "Plan acceptance declaration changed")
    require(plan["sourceIdentity"] == analysis["sourceIdentity"] == source["sourceIdentity"] == SOURCE, "Source provenance mismatch")
    require(tuple(plan["models"]) == tuple(analysis["models"]) == MODELS and tuple(plan["conditions"]) == CONDITIONS, "Model/condition coverage changed")
    require(analysis["modelIdentities"] == plan["modelIdentities"], "Analysis model selection differs from frozen plan")
    require(plan["firstSeed"] == analysis["firstSeed"] == allocation["firstSeed"]
            and plan["seedCount"] == analysis["seedCount"] == allocation["count"] == 256, "Reset budget mismatch")
    require(analysis["attemptsPerModel"] == 3 * plan["seedCount"] and analysis["baselineWasReevaluated"] is True
            and tuple(analysis["newlyEvaluatedModels"]) == MODELS, "Incomplete actual re-evaluation coverage")
    require(sha(base / "plan.json") == allocation["planHash"], "Plan changed after allocation")
    require(read(base / "candidate-evaluation-editor-restored.json")["restored"] is True, "Task-owned evaluation scene has not been restored")
    require(hashlib.sha256(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == SOURCE,
            "Source manifest identity is not internally consistent")
    for relative, expected in source["files"].items():
        require(sha(inside(root, relative)) == expected, f"Runtime source changed: {relative}")
    required_inputs = {f"{CAMPAIGN}/plan.json"}
    for model in MODELS:
        identity = plan["modelIdentities"][model]
        for key, digest_key in (("assetPath", "modelHash"), ("checkpoint", "checkpointHash")):
            relative = identity[key]
            require(sha(inside(root, relative)) == identity[digest_key], f"Selected model changed: {relative}")
            required_inputs.add(relative)
        for condition in CONDITIONS:
            folder = base / "evaluation" / model / condition
            require(folder.is_dir() and EVAL_FILES.issubset({path.name for path in folder.iterdir() if path.is_file()}), f"Missing raw evaluation evidence: {folder}")
            report = read(folder / "report.json")
            require(report["status"] == "seed_budget_complete" and not report.get("failure")
                    and report["trainerConnected"] is False and report["completedEpisodes"] == plan["seedCount"], f"Evaluation not complete: {folder}")
            require(jsonl_count(folder / "episodes.jsonl") == jsonl_count(folder / "execution-goals.jsonl") == plan["seedCount"], "Raw completed-attempt count mismatch")
            sidecar = read(folder / "model-identity.json")
            require(sidecar["model"] == model and all(sidecar[key] == identity[key] for key in ("modelHash", "checkpointHash", "step", "sourceIdentity")), "Actual evaluation model identity mismatch")
            for name in EVAL_FILES - {"summary.json"}:
                required_inputs.add(f"{CAMPAIGN}/evaluation/{model}/{condition}/{name}")
    required_inputs.update(plan["priorObservationInputs"])
    require(required_inputs.issubset(analysis["inputSha256"]), "Analysis input manifest does not cover all planned raw outcomes/models/novelty inputs")
    for relative, expected in analysis["inputSha256"].items():
        require(sha(inside(root, relative)) == expected, f"Analysis input changed: {relative}")
    analyzer = here / "analyze_fresh_placement.py"
    require(sha(analyzer) == analysis["analysisScriptSha256"], "Workspace analyzer is not the code that produced the analysis")
    frozen_scripts = read(base / "script-hashes.json")
    expected_scripts = {f"fresh-{label}-{condition}.cs" for label in ("initial", "final") for condition in CONDITIONS}
    expected_scripts.update(("fresh-prepare_scene.cs", "fresh-restore_editor.cs"))
    require(set(frozen_scripts) == expected_scripts, "Frozen evaluation/setup script coverage is incomplete")
    for name, expected in frozen_scripts.items():
        require(Path(name).name == name and sha(here / name) == expected, f"Frozen evaluation script changed: {name}")

    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    before, current = read(base / "seed-ledger-before.json"), read(ledger_path)
    require(before["finalSeedsConsumed"] == [] and current["finalSeedsConsumed"] == [], "Final acceptance seeds were consumed")
    require(allocation["finalSeedsConsumed"] is False
            and sha(base / "seed-ledger-before.json") == allocation["ledgerBeforeHash"] == plan["freshness"]["ledgerBeforeHash"]
            and sha(ledger_path) == allocation["ledgerAfterHash"], "Seed allocation provenance or current ledger changed")
    require(current["developmentBlocks"][:-1] == before["developmentBlocks"], "Unexpected changes to prior development allocations")
    fresh_entry = current["developmentBlocks"][-1]
    require(fresh_entry["firstSeed"] == plan["firstSeed"] and fresh_entry["count"] == plan["seedCount"] and fresh_entry["run"] == CAMPAIGN, "Current ledger does not contain the declared allocation")
    require({key: value for key, value in current.items() if key != "developmentBlocks"}
            == {key: value for key, value in before.items() if key != "developmentBlocks"}, "Other seed-ledger sections changed during evaluation")
    low, high = plan["firstSeed"], plan["firstSeed"] + plan["seedCount"]
    for entries in before.values():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and "firstSeed" in entry and "count" in entry:
                    require(max(int(entry["firstSeed"]), low) >= min(int(entry["firstSeed"]) + int(entry["count"]), high), "Fresh allocation overlaps a recorded prior interval")

    # Freeze a complete copy inventory before creating any destination directory.
    copies = {}

    def queue(source_path, destination_path):
        require(source_path.is_file(), f"Missing archive input: {source_path}")
        require(destination_path.resolve().is_relative_to(dest.resolve()) or destination_path.resolve().is_relative_to(workflow.resolve()), "Archive destination escaped scope")
        if destination_path in copies:
            require(copies[destination_path][1] == sha(source_path), "Archive destination collision")
        else:
            copies[destination_path] = (source_path, sha(source_path))

    for path in sorted(base.iterdir()):
        if path.is_file():
            queue(path, dest / path.name)
    queue(base / "audit/analysis.json", dest / "analysis.json")
    queue(ledger_path, dest / "seed-ledger-after.json")
    for model in MODELS:
        for condition in CONDITIONS:
            folder = base / "evaluation" / model / condition
            for path in sorted(folder.rglob("*")):
                require(not path.is_symlink() and path.resolve().is_relative_to(folder.resolve()), "Linked evaluation archive input")
                if path.is_file():
                    queue(path, dest / model / condition / path.relative_to(folder))
    script_names = {*expected_scripts, "prepare_fresh_placement.py", "analyze_fresh_placement.py"}
    for name in sorted(script_names):
        queue(here / name, workflow / name)
    queue(Path(__file__).resolve(), workflow / "archive_fresh_placement.py")
    queue(base / "plan.json", workflow / "plan.json")
    queue(base / "script-hashes.json", workflow / "script-hashes.json")
    # Preserve the exact prior observations so novelty can be recomputed without
    # depending on ignored runtime artifacts. Keep the original-path mapping.
    for relative in plan["priorObservationInputs"]:
        queue(inside(root, relative), dest / "prior-observation-inputs" / relative)
    canonical_references = {}
    model_paths = {identity[key] for identity in plan["modelIdentities"].values() for key in ("assetPath", "checkpoint")}
    covered_sources = {source_path.resolve(): destination for destination, (source_path, _) in copies.items()}
    for relative, expected in analysis["inputSha256"].items():
        path = inside(root, relative)
        if relative in model_paths:
            canonical_references[relative] = {"sha256": expected, "mode": "canonical_repository_model_or_checkpoint"}
        elif path.resolve() not in covered_sources:
            queue(path, workflow / "dependencies" / relative)
    covered_sources = {source_path.resolve(): destination for destination, (source_path, _) in copies.items()}
    input_coverage = {}
    for relative, expected in analysis["inputSha256"].items():
        path = inside(root, relative)
        if relative in canonical_references:
            input_coverage[relative] = canonical_references[relative]
        else:
            require(path.resolve() in covered_sources, f"Uncovered analysis input: {relative}")
            input_coverage[relative] = {"sha256": expected, "mode": "byte_preserved_copy",
                                        "archivePath": covered_sources[path.resolve()].relative_to(root).as_posix()}
    report_text = render_report(analysis, plan)
    initial_hashes = {source_path.resolve(): digest for source_path, digest in copies.values()}
    initial_hashes.update({inside(root, relative).resolve(): digest for relative, digest in analysis["inputSha256"].items()})
    dest.mkdir(parents=True, exist_ok=False)
    workflow.mkdir(parents=True, exist_ok=False)
    try:
        archived = []
        for target, (original, expected) in sorted(copies.items(), key=lambda item: str(item[0])):
            require(not target.exists() and sha(original) == expected, f"Archive input changed or destination exists: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            require(sha(target) == expected and target.read_bytes() == original.read_bytes(), f"Byte preservation failed: {target}")
            archived.append({"source": str(original.resolve()), "archivePath": target.relative_to(root).as_posix(), "sha256": expected})
        for path, expected in initial_hashes.items():
            require(sha(path) == expected, f"Input changed during archiving: {path}")
        for relative, expected in source["files"].items():
            require(sha(inside(root, relative)) == expected, f"Runtime source changed during archiving: {relative}")
        require(read(ledger_path)["finalSeedsConsumed"] == [] and sha(ledger_path) == allocation["ledgerAfterHash"], "Ledger changed during archiving")
        write_text(workflow / "README.md", "# Fresh placement evaluation archive\n\n"
                   "Both selected frozen models were evaluated anew on the plan's 256 base resets under A/B/random instructions. "
                   "This is an evaluation-only, same-recipe screen. New seed IDs are not treated as proof of new physical situations.\n\n"
                   "The eight C# evaluation/setup scripts match hashes frozen before execution. The analyzer matches the digest recorded in its output. "
                   "The preparer and archiver are preserved orchestration snapshots. Scripts may contain original Windows paths; they are historical evidence, not a portable one-command campaign.\n\n"
                   "Raw outcomes, prior observations, plan, source manifest, and allocation ledgers are preserved under docs/research/execution-v1-evidence/fresh-placement-01. "
                   "archive-manifest.json maps every analysis input to its exact archived copy or existing canonical model/checkpoint. Model binaries are already kept under Assets and training/snapshots.\n\n"
                   "All completed attempts are included. The archive does not promote a model or complete the mastery goal. "
                   "Per-variation receiving, kitchen behavior, larger measured positioning, repeat evidence and human movement review remain required.\n")
        write_text(report_path, report_text)
        manifest = {"status": "complete_byte_preserved_archive", "campaign": CAMPAIGN,
                    "sourceIdentity": SOURCE, "planHash": sha(base / "plan.json"), "analysisHash": sha(base / "audit/analysis.json"),
                    "analysisScriptHash": analysis["analysisScriptSha256"], "archiverScriptHash": sha(Path(__file__)),
                    "allCompletedAttemptsPreserved": True, "outcomeFiltering": False,
                    "evaluationRuns": len(MODELS) * len(CONDITIONS), "baseResets": plan["seedCount"],
                    "attemptsPerModel": analysis["attemptsPerModel"], "newlyEvaluatedModels": list(MODELS),
                    "analysisInputCoverage": input_coverage, "files": archived,
                    "generatedFiles": {REPORT: sha(report_path), f"{WORKFLOW}/README.md": sha(workflow / "README.md")},
                    "frozenEvaluationScriptHashes": frozen_scripts, "seedLedgerBeforeHash": allocation["ledgerBeforeHash"],
                    "seedLedgerAfterHash": allocation["ledgerAfterHash"], "sourceAndSelectedModelsVerified": True,
                    "inputCoverageVerified": True, "finalSeedLedgerRepresentation": "empty list in both saved before/current ledgers",
                    "finalSeedsConsumed": False, "promoted": False, "masteryAccepted": False,
                    "limitations": ["Model/checkpoint bytes remain in their verified canonical repository paths, not duplicated in this evidence folder.",
                                    "Current ledger freshness does not establish historical V1/V2 novelty or physical novelty.",
                                    "Exact observed-state novelty, cluster estimates and actual contact modes must be read separately from aggregate success."]}
        write(dest / "archive-manifest.json", manifest)
        print(json.dumps({"report": str(report_path), "evidence": str(dest), "workflow": str(workflow),
                          "archivedFileCount": len(archived), "analysisInputsCovered": len(input_coverage),
                          "screenPromising": analysis["screen"]["promising"], "finalSeedsConsumed": False,
                          "masteryAccepted": False}, indent=2))
    except BaseException as error:
        failure = {"status": "partial_archive_preserved", "error": repr(error), "traceback": traceback.format_exc(),
                   "promoted": False, "masteryAccepted": False}
        if not (dest / "archive-failure.json").exists():
            write(dest / "archive-failure.json", failure)
        raise


if __name__ == "__main__":
    main()
