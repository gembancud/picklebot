"""Archive completed axes results and render their report, without promotion.

Run only after all five evaluations, final analysis and Editor restoration.
Existing setup/launch archives remain unchanged. Binary builds and checkpoints
are hash-referenced at their existing locations; worker JSONL is lossless gzip.
No work on import. A failed/partial archive is preserved, never overwritten.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import traceback

BASE = "artifacts/hierarchy-v1/axes-recovery-01"
ARCHIVE = "docs/research/execution-v1-evidence/axes-recovery-01"
WORKFLOW = "research/hierarchy-v1/axes-recovery-01"
REPORT = "docs/research/execution-v1-axes-recovery-final.md"
INITIAL = "ExecutionV1Initial"
PARENT = "ExecutionV1SmoothContinuedFinal01"
FINAL = "ExecutionV1AxesRecoveryFinal01"
MODELS = (INITIAL, PARENT, FINAL)
DRILLS = ("stationary-serve", "receive-feed", "rally-air-feed", "rally-bounce-feed")
EVAL_FILES = {"episodes.jsonl", "execution-goals.jsonl", "first-decisions.json", "report.json", "summary.json", "model-identity.json"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as handle:
        return stream_sha(handle)


def stream_sha(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def inside(root, relative):
    path = (root / relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(root), "Path escapes repository: " + str(relative))
    return path


def interval(value, scale=1):
    if value["mean"] is None:
        return "not measured"
    return f"{scale * value['mean']:+.4f} [{scale * value['ci95'][0]:+.4f}, {scale * value['ci95'][1]:+.4f}]"


def render_report(analysis, plan, training):
    labels = {INITIAL: "Initializer", PARENT: "Previous endpoint", FINAL: "Axes endpoint"}
    lines = ["# Graded movement continuation", "",
        f"The fixed final executor reached **{analysis['finalTrainingStep']:,} experiences**, adding **{training['newExperiences']:,}** from the {plan['initialStep']:,}-experience checkpoint. The focus drills used 6.25/12.5/18.75/25 cm shifts in four directions, within the existing 25% familiar / 25% prior / 50% focus mixture.", "",
        "Actor, critic, normalization, Adam and global step resumed through ML-Agents. Body controls, observations, PPO settings and smooth-distance reward were unchanged. Process RNG and live rollouts restarted; training reset IDs were reused. These results assess the fixed final export, without choosing a checkpoint by performance.", "",
        "Five new evaluations reused the narrow 256-reset A/B/random battery and the wide 512-reset A/B battery. Both baselines retain their original source identities. Passed default-reset tests and exact paired first 124 physical / full 136 observation values support comparison across the opt-in scheduler change. No promotion, automatic extension or mastery acceptance follows from this report.", ""]
    for name, title in (("narrow", "Narrow retained-skill battery"), ("wide", "Wide movement battery")):
        battery = analysis["batteries"][name]
        conditions = battery["conditions"]
        clusters = battery["physicalObservationClusters"]
        lines += [f"## {title}", "",
            f"**{battery['baseResets']} base resets; {clusters['uniqueClusters']} distinct initial physical-observation clusters.** Conditions repeat the same resets; they are not independent extra situations.", "",
            "Every count below is **legal / target hits / attempts**. Target success requires a legal landing inside the requested region; nonzero distance reward does not count as target success.", "",
            "| Cases | Model | " + " | ".join(conditions) + " |",
            "|---|---|" + "---:|" * len(conditions)]
        groups = [("all", "All")]
        groups += [(f"drill/{drill}", drill) for drill in DRILLS]
        if name == "wide":
            groups += [("schedule/familiar", "Familiar/retained"), ("schedule/axis-challenge", "Axes challenges")]
            groups += [(f"axis/{direction}", direction.title()) for direction in ("left", "right", "shallow", "deep")]
            groups += [(f"nominal-shift/{cm}cm", f"Nominal {cm} cm") for cm in (25, 50, 75, 100)]
        for group, label in groups:
            for model in MODELS:
                counts = battery["summaries"][group][model]
                cells = [f"{counts[c]['legal']} / {counts[c]['targets']} / {counts[c]['attempts']}" for c in conditions]
                lines.append(f"| {label} | {labels[model]} | " + " | ".join(cells) + " |")
        lines += ["", "| Final A/B assignment gain | Reset-weighted estimate [95% interval] | Equal-observation-cluster estimate [95% interval] |",
            "|---|---:|---:|",
            "| Absolute final gain | " + interval(battery["causalResetWeighted"]["all"][FINAL]["assignmentGain"]) + " | " + interval(battery["causalUniqueClusterWeighted"]["all"][FINAL]) + " |"]
        for baseline in (INITIAL, PARENT):
            delta = battery["pairedFinalMinusBaseline"]["all"][baseline]
            lines.append(f"| Final minus {labels[baseline].lower()} | {interval(delta['assignmentGainResetWeighted'])} | {interval(delta['assignmentGainUniqueClusterWeighted'])} |")
        lines += ["", "Assignment gain compares requested versus opposite A/B regions on matched feeds. Illegal/no-landing attempts contribute zero. The initializer's target-blind actions and physical outcomes cancel exactly. Reset and cluster estimates use different weights; both intervals are pointwise and do not establish independent training replication.", "",
            "| Drill | Model | Requested A: in A / in B / legal elsewhere / no legal landing | Requested B: same categories |", "|---|---|---:|---:|"]
        for drill in DRILLS:
            for model in MODELS:
                matrix = battery["targetConfusionMatrices"][f"drill/{drill}"][model]
                cells = [" / ".join(str(matrix[c][key]) for key in ("legalInA", "legalInB", "legalOutsideBoth", "illegalOrNoLegalLanding")) for c in ("A", "B")]
                lines.append(f"| {drill} | {labels[model]} | {cells[0]} | {cells[1]} |")
        lines += ["", "A/B are shallow/deep target regions for serves and canonical left/right for receives and rallies. The complete analysis also retains player, serve-side, movement-category and paired outcome/telemetry differences.", ""]
        if name == "wide":
            lines += ["Nominal shift is the feed offset from the initial paddle face, not required or actual root travel. Training focus stopped at 25 cm; the 50–100 cm cases are transfer probes. Direction and distance tables are marginal summaries; sparse joint cells remain included.", "",
                "| Final axes movement | A | B |", "|---|---:|---:|"]
            telemetry = battery["actualContactAndMovementTelemetry"]["schedule/axis-challenge"][FINAL]
            lines.append("| Accepted face contacts / attempts | " + " | ".join(f"{telemetry[c]['acceptedFaceContacts']} / {telemetry[c]['attempts']}" for c in ("A", "B")) + " |")
            for key, label in (("rootPathThroughFirstContactOrTerminalMetres", "Root path through first contact or termination"),
                               ("rootPathBeforeAcceptedContactMetres", "Root path conditional on accepted contact"),
                               ("netRootDisplacementConditionalOnAcceptedContactMetres", "Net root displacement conditional on accepted contact"),
                               ("rootPathThroughNoContactTerminationMetres", "Root path through no-contact termination")):
                cells = []
                for condition in ("A", "B"):
                    row = telemetry[condition][key]
                    cells.append("not measured (n=0)" if row["mean"] is None else f"{row['mean']:.3f} m (n={row['measuredAttempts']})")
                lines.append(f"| {label} | " + " | ".join(cells) + " |")
            joint = battery["descriptiveWideJointCells"]
            lines += ["", f"The {len(joint)} drill/direction/distance/player cells include {sum(row['attempts'] == 0 for row in joint)} empty cells and {sum(0 < row['attempts'] < 5 for row in joint)} cells with fewer than five attempts. These remain descriptive. Longer miss trajectories can accumulate more travel; distance alone does not prove better positioning.", ""]
    screens = analysis["batteries"]["narrow"]["existingNarrowScreen"]
    descriptions = {
        "resetWeightedAssignmentGainCiLowerAboveZero": "Final reset-weighted gain interval lower bound > 0",
        "uniqueClusterWeightedAssignmentGainCiLowerAboveZero": "Final cluster-weighted gain interval lower bound > 0",
        "bothRegionTargetRatesExceedBaseline": "Final A and B target rates exceed comparison model",
        "noDrillLegalDropGreaterThanFivePercentagePoints": "No drill/condition loses >5 percentage points of legality"}
    lines += ["## Existing narrow retention screen", "", "| Check | Against initializer | Against previous endpoint |", "|---|---|---|"]
    for screen in screens.values():
        require(set(screen["tests"]) == set(descriptions), "Unexpected screen tests; update report explicitly")
    for key, label in descriptions.items():
        lines.append(f"| {label} | " + " | ".join("Pass" if screens[m]["tests"][key] else "Fail" for m in (INITIAL, PARENT)) + " |")
    lines.append("| Combined descriptive screen | " + " | ".join("Pass" if screens[m]["descriptivePass"] else "Fail" for m in (INITIAL, PARENT)) + " |")
    lines += ["", "The original retention rule uses point estimates; it is not a statistical noninferiority guarantee. Absolute final assignment gain and changes versus each baseline are reported separately. No new pass threshold is imposed on wide movement.", "",
        "| Drill / condition | Legal-rate change vs initializer, pp [95% interval] | Vs previous endpoint, pp [95% interval] |", "|---|---:|---:|"]
    indexed = {m: {(r["drill"], r["condition"]): r for r in screens[m]["retentionChecks"]} for m in (INITIAL, PARENT)}
    for drill in DRILLS:
        for condition in ("A", "B", "random"):
            lines.append(f"| {drill} / {condition} | " + " | ".join(interval(indexed[m][drill, condition], 100) for m in (INITIAL, PARENT)) + " |")
    lines += ["", "## Actual receiving and volley contacts", "",
        "| Final battery / condition | Required-bounce legal / attempts | Volley legal / accepted volley contacts | Bounced-rally legal / accepted bounced contacts | Rally attempts |", "|---|---:|---:|---:|---:|"]
    for name, battery in analysis["batteries"].items():
        for condition in battery["conditions"]:
            row = battery["actualContactAndMovementTelemetry"]["all"][FINAL][condition]
            lines.append(f"| {name} / {condition} | {row['legalRequiredBounceReturns']} / {row['requiredBounceReceiveAttempts']} | {row['legalVolleyReturns']} / {row['acceptedVolleyContacts']} | {row['legalRallyReturnsAfterBounce']} / {row['acceptedRallyContactsAfterBounce']} | {row['rallyAttempts']} |")
    lines += ["", "Volley/bounced-contact columns are explicitly conditional contact outcomes; the earlier legal/all tables include misses. A rally-bounce feed permits a volley after the opening rule has cleared. A false volley flag without contact is not counted as a groundstroke.", "",
        "## Evidence limits", "",
        "This is one continuing training lineage on reused development situations. Repeated observations and exact reset parity do not establish broad generalization or prove each difficult feed is physically reachable. Varied starts and timing, broader required-bounce receiving, kitchen-line/momentum decisions, paired ownership and full 2v2 play remain outside this battery's mastery claim.", "",
        "The source, tests, seeds, selection, all five raw evaluations and complete analysis are preserved. Worker rollout JSONL is stored as lossless gzip with compressed and uncompressed hashes. Existing canonical model/checkpoint files and previously archived helper dependencies are referenced by hash, without duplicating large binaries. Final acceptance seeds remain unused.", "",
        "[Analysis](execution-v1-evidence/axes-recovery-01/results/audit/analysis.json) · [Frozen plan](execution-v1-evidence/axes-recovery-01/results/plan.json) · [Training verification](execution-v1-evidence/axes-recovery-01/results/training/verification.json) · [Archive coverage](execution-v1-evidence/axes-recovery-01/results/archive-manifest.json) · [Coverage gaps](drill-mastery-coverage.md)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--scripts", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root, here = args.root.resolve(), args.scripts.resolve()
    if here.is_file(): here = here.parent
    base, archive, workflow = (inside(root, value) for value in (BASE, ARCHIVE, WORKFLOW))
    dest, work = archive / "results", workflow / "results"
    report_path = inside(root, REPORT)
    require(not dest.exists() and not work.exists() and not report_path.exists(), "Exclusive result destinations already exist; preserve previous/partial archive")
    require((archive / "setup/archive-manifest.json").is_file() and (archive / "launch/archive-manifest.json").is_file(), "Prior setup/launch archives are missing")
    for item in read(archive / "setup/archive-manifest.json")["files"]:
        require(sha(inside(root, item["path"])) == item["sha256"], "Existing setup archive changed")
    for filename, expected in read(archive / "launch/archive-manifest.json")["files"].items():
        require(sha(inside(archive / "launch", filename)) == expected, "Existing launch archive changed")
    analysis, plan, selected, training = (read(base / name) for name in ("audit/analysis.json", "plan.json", "selected-models.json", "training/verification.json"))
    require(analysis["status"] == "complete_axes_recovery_final_assessment" and set(analysis["batteries"]) == {"narrow", "wide"}, "Mandatory final analysis incomplete")
    require(all(analysis[k] is False for k in ("promoted", "automaticExtension", "masteryAccepted", "finalSeedsConsumed")), "Unexpected promotion/extension/final-seed claim")
    require(training["status"] == "completed_continuation_check" and training["resumeStateExact"] and training["parentRunUnchanged"], "Training verification incomplete")
    require(read(base / "candidate-evaluation-editor-restored.json")["restored"] is True, "Owned evaluation Editor not restored")
    require(sha(here / "analyze_axes_recovery.py") == analysis["analysisScriptSha256"], "Analyzer changed after analysis")
    require(sha(base / "plan.json") == selected["planHash"] and sha(base / "training/verification.json") == selected["trainingVerificationHash"], "Endpoint selection inputs changed")
    require(selected["final"] == analysis["modelIdentities"][FINAL] and selected["final"]["step"] == training["experiences"] == analysis["finalTrainingStep"], "Final endpoint mismatch")
    source = read(inside(root, plan["sourceRecordPath"]))
    require(source["sourceIdentity"] == plan["sourceIdentity"] == analysis["sourceIdentity"] == training["sourceIdentity"], "Source identity mismatch")
    source_paths = {inside(root, relative): digest for relative, digest in source["files"].items()}
    for path, digest in source_paths.items(): require(sha(path) == digest, "Runtime source changed: " + str(path))
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    commit = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    tree = {}
    for entry in subprocess.check_output(git + ["ls-tree", "-r", "-z", "HEAD"]).split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            tree[name.decode()] = metadata.split()[2].decode()
    for path in source_paths:
        content = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        require(tree.get(path.relative_to(root).as_posix()) == blob, "Runtime source is not preserved at current commit: " + str(path))
    ledger_path = root / "artifacts/player-v3/seed-ledger.json"
    ledger = read(ledger_path)
    require(ledger["finalSeedsConsumed"] == [] and sum(row["run"] == BASE + "/training" for row in ledger["trainingReuses"]) == 1, "Final-seed/training reuse ledger differs")
    copies, compressed, referenced, coverage, local_binaries = {}, {}, {}, {}, {}

    def queue(path, target, compress=False):
        path, target = path.resolve(), target.resolve()
        require(path.is_file() and (target.is_relative_to(dest) or target.is_relative_to(work)), "Invalid archive mapping")
        require(not target.exists(), "Archive target already exists: " + str(target))
        digest = sha(path)
        inventory = compressed if compress else copies
        require(target not in (copies if compress else compressed), "Archive encoding collision")
        if target in inventory: require(inventory[target] == (path, digest), "Archive path collision")
        inventory[target] = path, digest

    build = read(inside(root, plan["buildRecordPath"]))
    binary = Path(build["directory"]).resolve()
    require(build["sourceIdentity"] == source["sourceIdentity"] and build["buildIdentity"] == plan["buildIdentity"], "Build provenance differs")
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_relative_to(binary): continue
        if path == base / "training/resume-loaded-state.pt":
            digest = read(base / "training/resume-load-proof.json")["snapshotHash"]
            require(sha(path) == digest, "Installed-loader state snapshot changed")
            referenced[path] = digest
            local_binaries[path.relative_to(root).as_posix()] = dict(sha256=digest, bytesCopied=False,
                role="Exact loaded parent state; equality and installed loader identities recorded in resume-load-proof.json")
            continue
        require(path.suffix.lower() not in (".pt", ".onnx", ".dll", ".exe"), "Unexpected bulk binary in audit: " + str(path))
        zipped = path.is_relative_to(base / "training") and path.suffix == ".jsonl"
        target = dest / path.relative_to(base)
        queue(path, Path(str(target) + ".gz") if zipped else target, zipped)
    for filename in ("build-result.json",):
        if (binary / filename).is_file(): queue(binary / filename, dest / "build-metadata" / filename)
    queue(ledger_path, dest / "seed-ledger-after.json")
    config = inside(root, plan["configPath"])
    require(sha(config) == plan["configHash"], "Frozen training config changed")
    queue(config, work / "dependencies" / plan["configPath"])
    training_helper = inside(root, plan["helperPath"])
    require(sha(training_helper) == plan["helperHash"], "Pinned training helper changed")
    referenced[training_helper] = plan["helperHash"]
    for relative, digest in training["workerInputSha256"].items():
        path = inside(base / "training", relative)
        require(sha(path) == digest and any(p == path for p, _ in [*copies.values(), *compressed.values()]), "Worker evidence not covered: " + relative)
    expected_scripts = {"narrow/A", "narrow/B", "narrow/random", "wide/A", "wide/B"}
    require(set(selected["scripts"]) == expected_scripts, "Five final evaluation scripts not selected")
    for item in selected["scripts"].values():
        path = Path(item["path"]).resolve()
        require(sha(path) == item["sha256"], "Generated evaluation script changed")
        queue(path, work / path.name)
    editor_scripts_path = base / "evaluation-editor-script-hashes.json"
    require(editor_scripts_path.is_file(), "Editor prepare/restore script hashes must be frozen for archival")
    for original, expected in read(editor_scripts_path).items():
        path = Path(original).resolve()
        require(Path(original).is_absolute() and sha(path) == expected, "Editor script hash changed")
        queue(path, work / "editor" / path.name)
    loader_coverage = {}
    for original, expected in read(base / "training/resume-load-proof.json")["installedSourceHashes"].items():
        path = Path(original).resolve()
        require(sha(path) == expected, "Installed loader source changed")
        target = work / "dependencies/installed-loader" / expected[:16] / path.name
        queue(path, target)
        loader_coverage[original] = dict(sha256=expected, archivePath=target.relative_to(root).as_posix())
    for filename, expected in (("prepare_axes_evaluation.py", selected["preparerHash"]), ("analyze_axes_recovery.py", analysis["analysisScriptSha256"]), ("run_axes_recovery.py", plan["runnerHash"]), ("prepare_axes_recovery.py", plan["prepareScriptHash"])):
        require(sha(here / filename) == expected, "Workflow script changed: " + filename)
        queue(here / filename, work / filename)
    queue(Path(__file__).resolve(), work / Path(__file__).name)

    # Existing canonical models/checkpoints are kept once. Byte-identical numbered
    # exports can reference them; mutable differently serialized checkpoints are
    # recorded honestly as retained local files, not claimed as byte-copied.
    canonical_by_hash = {}
    for identity in analysis["modelIdentities"].values():
        for field, hash_field in (("assetPath", "modelHash"), ("checkpoint", "checkpointHash")):
            path = inside(root, identity[field])
            require(sha(path) == identity[hash_field], "Canonical model/checkpoint changed")
            canonical_by_hash[identity[hash_field]] = path
    for name, expected_count, conditions in (("narrow", 256, ("A", "B", "random")), ("wide", 512, ("A", "B"))):
        battery = analysis["batteries"][name]
        require(battery["baseResets"] == expected_count and tuple(battery["conditions"]) == conditions and battery["physicalObservationAndGoalParity"] is True, "Evaluation battery mismatch")
        for condition in conditions:
            folder = base / "evaluation" / name / FINAL / condition
            require(EVAL_FILES.issubset({p.name for p in folder.iterdir() if p.is_file()}), "Missing evaluation evidence")
            report = read(folder / "report.json")
            require(report["status"] == "seed_budget_complete" and not report.get("failure") and report["completedEpisodes"] == expected_count, "Evaluation not complete")
            sidecar = read(folder / "model-identity.json")
            require(all(sidecar[key] == selected["final"][key] for key in ("model", "modelHash", "checkpointHash", "step", "sourceIdentity")), "Evaluation endpoint identity changed")
            for filename in EVAL_FILES:
                require((folder / filename).relative_to(root).as_posix() in analysis["inputSha256"], "Analysis omitted evaluation input")

    for key, expected in analysis["inputSha256"].items():
        path = (Path(key) if Path(key).is_absolute() else inside(root, key)).resolve()
        require(sha(path) == expected, "Analysis input changed: " + key)
        target = next((target for target, (original, _) in copies.items() if original == path), None)
        if target is not None:
            item = dict(mode="byte-preserved copy", path=target.relative_to(root).as_posix())
        elif path in source_paths:
            item = dict(mode="runtime source at Git commit", path=path.relative_to(root).as_posix(), commit=commit)
        elif expected in canonical_by_hash:
            canonical = canonical_by_hash[expected]
            item = dict(mode="existing canonical model/checkpoint bytes", path=canonical.relative_to(root).as_posix())
        elif path.is_relative_to(root / "research") or path.is_relative_to(root / "docs/research"):
            # Preserve original root-relative import locations used by hash-pinned
            # helpers, rather than rewriting their imports or source identities.
            item = dict(mode="existing byte-preserved research dependency", path=path.relative_to(root).as_posix())
        elif path.suffix.lower() in (".pt", ".onnx"):
            item = dict(mode="retained local binary; no duplicate bytes archived", path=path.relative_to(root).as_posix(),
                        note="Final mutable/numbered/snapshot state equality is in selection/analysis; differently serialized checkpoint bytes retain their own hash.")
        else:
            relative = path.relative_to(root) if path.is_relative_to(root) else Path("external") / expected[:16] / path.name
            target = work / "dependencies" / relative
            queue(path, target)
            item = dict(mode="byte-preserved dependency copy", path=target.relative_to(root).as_posix())
        coverage[key] = {**item, "sha256": expected}
        referenced[path] = expected
    require(ledger_path.relative_to(root).as_posix() in analysis["inputSha256"], "Final ledger not checked by analysis")
    for relative, expected in plan["evaluation"]["baselineInputs"].items():
        require(analysis["inputSha256"].get(relative) == expected, "Frozen baseline not covered by analysis: " + relative)
    report_text = render_report(analysis, plan, training)
    immutable_before = {p: sha(p) for parent in (archive / "setup", archive / "launch", workflow) for p in parent.rglob("*") if p.is_file()}
    dest.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    records = []
    try:
        for target, (original, expected) in sorted(copies.items(), key=lambda item: str(item[0])):
            require(sha(original) == expected, "Input changed during archive")
            target.parent.mkdir(parents=True, exist_ok=True)
            with original.open("rb") as source_handle, target.open("xb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
            require(sha(target) == expected, "Copied bytes differ")
            records.append(dict(source=str(original), archivePath=target.relative_to(root).as_posix(), sha256=expected, encoding="original bytes"))
        for target, (original, expected) in sorted(compressed.items(), key=lambda item: str(item[0])):
            require(sha(original) == expected, "Worker input changed during archive")
            target.parent.mkdir(parents=True, exist_ok=True)
            with original.open("rb") as source_handle, target.open("xb") as raw_target:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw_target, mtime=0) as zipped:
                    shutil.copyfileobj(source_handle, zipped)
            with gzip.open(target, "rb") as handle: require(stream_sha(handle) == expected, "Compressed evidence round trip differs")
            records.append(dict(source=str(original), archivePath=target.relative_to(root).as_posix(), sha256=sha(target),
                                encoding="gzip", uncompressedSha256=expected, uncompressedBytes=original.stat().st_size))
        for original, expected in [*copies.values(), *compressed.values(), *referenced.items(), *source_paths.items(), *immutable_before.items()]:
            require(sha(original) == expected, "Original evidence/source changed during archive: " + str(original))
        require(read(ledger_path)["finalSeedsConsumed"] == [], "Final acceptance seed use changed during archive")
        with report_path.open("x", encoding="utf-8", newline="\n") as handle: handle.write(report_text)
        readme = ("# Axes final assessment workflow\n\n"
                  "These exact scripts generated and assessed the fixed final endpoint on five paired development evaluations. Original setup and launch files remain in the parent archive.\n\n"
                  "Python helpers retain their original hash-pinned root-relative imports under research/hierarchy-v1. Existing helper files are dependencies, not modified copies. Generated Unity scripts contain historical absolute Windows paths. This is provenance evidence, not a portable one-command replay bundle.\n\n"
                  "Worker JSONL is losslessly compressed. Model/checkpoint and build binaries remain at their recorded locations without duplicate binary commits. archive-manifest.json distinguishes byte copies, existing canonical dependencies, Git source and local binary hash references. No new acceptance threshold or promotion is introduced.\n")
        with (work / "README.md").open("x", encoding="utf-8", newline="\n") as handle: handle.write(readme)
        manifest = dict(status="complete_axes_results_archive", sourceIdentity=source["sourceIdentity"], sourceGitCommit=commit,
            planHash=sha(base / "plan.json"), analysisHash=sha(base / "audit/analysis.json"), archiveScriptSha256=sha(Path(__file__)),
            files=records, analysisInputCoverage=coverage,
            trainingHelper=dict(path=plan["helperPath"], sha256=plan["helperHash"], mode="existing byte-preserved helper with original import path"),
            installedLoaderSourceCoverage=loader_coverage, retainedLocalAuditBinaries=local_binaries,
            workerInputCoverage={relative: next(row for row in records if Path(row["source"]) == (base / "training" / relative).resolve()) for relative in training["workerInputSha256"]},
            existingSetupAndLaunchPreserved=True, priorArchiveHashes={str(path): digest for path, digest in immutable_before.items()},
            build=dict(manifest=plan["buildRecordPath"], buildIdentity=build["buildIdentity"], directory=str(binary), binaryBytesCopied=False),
            report=dict(path=REPORT, sha256=sha(report_path)), modelIdentities=analysis["modelIdentities"],
            newEvaluations=5, newAttempts=3 * 256 + 2 * 512, allAttemptsIncluded=True,
            finalSeedsConsumed=False, promoted=False, automaticExtension=False, masteryAccepted=False)
        write(dest / "archive-manifest.json", manifest)
        print(json.dumps(dict(evidence=str(dest), workflow=str(work), report=str(report_path), files=len(records),
                              compressedFiles=len(compressed), analysisInputsCovered=len(coverage), masteryAccepted=False), indent=2))
    except BaseException as error:
        if not (dest / "archive-failure.json").exists():
            write(dest / "archive-failure.json", dict(status="partial_archive_preserved", error=repr(error), traceback=traceback.format_exc(), masteryAccepted=False))
        raise


if __name__ == "__main__":
    main()
