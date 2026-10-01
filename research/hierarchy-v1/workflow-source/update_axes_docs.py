"""Update four current-status documents after the archived axes assessment.

Requires an explicit next-step decision. No evaluation, training or promotion.
Historical reports are untouched; exact before/after document bytes are archived.
No work on import. Run with --root REPOSITORY --next-step 'Agreed next action'.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import traceback

BASE = "artifacts/hierarchy-v1/axes-recovery-01"
ARCHIVE = "docs/research/execution-v1-evidence/axes-recovery-01"
REPORT = "docs/research/execution-v1-axes-recovery-final.md"
OLD_REPORT = "docs/research/execution-v1-axes-recovery.md"
PARENT = "ExecutionV1SmoothContinuedFinal01"
INITIAL = "ExecutionV1Initial"
FINAL = "ExecutionV1AxesRecoveryFinal01"
FILES = ("docs/CURRENT_STATE.md", "docs/DRILL_MASTERY_GOAL.md", "docs/HIERARCHICAL_CONTROL.md", "docs/research/drill-mastery-coverage.md")
MARKER = "<!-- axes-recovery-final-status -->"
DIRECTIONS = ("left", "right", "shallow", "deep")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def interval(row):
    if row["mean"] is None:
        return "not measured"
    return f"{row['mean']:+.5f} [{row['ci95'][0]:+.5f}, {row['ci95'][1]:+.5f}]"


def comparisons(battery, group, metric, conditions):
    counts = battery["summaries"][group]
    cells = []
    for condition in conditions:
        before, after = counts[PARENT][condition], counts[FINAL][condition]
        require(before["attempts"] == after["attempts"], "Comparison denominator differs")
        cells.append(f"{condition} **{before[metric]} → {after[metric]} / {after['attempts']}**")
    return "; ".join(cells)


def direction_25cm(wide):
    """Render existing disjoint joint-cell counts; do not generate new outcomes."""
    totals = {}
    for direction in DIRECTIONS:
        rows = [row for row in wide["descriptiveWideJointCells"] if row["direction"] == direction and row["nominalShiftCm"] == 25]
        require(len(rows) == 8, "Missing drill/player cells for 25 cm direction")
        totals[direction] = {}
        for model in (PARENT, FINAL):
            totals[direction][model] = {}
            for condition in ("A", "B"):
                require(all(row["counts"][model][condition]["attempts"] == row["attempts"] for row in rows), "Joint-cell denominators differ")
                totals[direction][model][condition] = {key: sum(row["counts"][model][condition][key] for row in rows) for key in ("attempts", "legal", "targets")}
    for model in (PARENT, FINAL):
        for condition in ("A", "B"):
            for key in ("attempts", "legal", "targets"):
                require(sum(totals[d][model][condition][key] for d in DIRECTIONS) == wide["summaries"]["nominal-shift/25cm"][model][condition][key], "25 cm directions do not sum to the analyzed marginal")
    return totals


def movement_table(totals):
    lines = ["| Nominal 25 cm direction | A: legal; targets (previous → final) | B: legal; targets (previous → final) |", "|---|---:|---:|"]
    for direction in DIRECTIONS:
        cells = []
        for condition in ("A", "B"):
            before, after = (totals[direction][model][condition] for model in (PARENT, FINAL))
            require(before["attempts"] == after["attempts"], "Paired 25 cm denominator differs")
            cells.append(f"{before['legal']} → {after['legal']}; {before['targets']} → {after['targets']} (each / {after['attempts']})")
        lines.append(f"| {direction.title()} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines)


def retention_statement(narrow):
    screens = narrow["existingNarrowScreen"]
    fragments = []
    for model, label in ((INITIAL, "initializer"), (PARENT, "previous endpoint")):
        screen = screens[model]
        guards = [row for row in screen["retentionChecks"] if row["mean"] < -.05 - 1e-12]
        detail = f"{len(guards)} drill/condition legal-retention point estimates exceeded the 5 percentage-point loss limit" if guards else "no drill/condition legal-retention point estimate exceeded the 5 percentage-point loss limit"
        fragments.append(f"Against the {label}, the existing narrow screen **{'passed' if screen['descriptivePass'] else 'failed'}**; {detail}.")
    return " ".join(fragments) + " These are development checks, not mastery or statistical noninferiority guarantees."


def render_blocks(analysis, next_step):
    narrow, wide = analysis["batteries"]["narrow"], analysis["batteries"]["wide"]
    step = analysis["finalTrainingStep"]
    table = movement_table(direction_25cm(wide))
    legal_narrow = comparisons(narrow, "all", "legal", ("A", "B", "random"))
    aim_narrow = comparisons(narrow, "all", "targets", ("A", "B", "random"))
    legal_axes = comparisons(wide, "schedule/axis-challenge", "legal", ("A", "B"))
    aim_axes = comparisons(wide, "schedule/axis-challenge", "targets", ("A", "B"))
    legal25 = comparisons(wide, "nominal-shift/25cm", "legal", ("A", "B"))
    aim25 = comparisons(wide, "nominal-shift/25cm", "targets", ("A", "B"))
    retention = retention_statement(narrow)
    current = ["# Active drill-mastery goal — graded movement assessed", "", MARKER, "",
        f"The fixed **{step:,}-experience executor** completed all five frozen development evaluations: narrow A/B/random at 256 resets each and wide A/B at 512 each. The full checkpoint resumed from 1,048,609 experiences; the changed focus practised nominal 6.25–25 cm shifts in four directions while retaining the 25/25/50 familiar/prior/focus mixture.", "",
        f"Previous endpoint → final, narrow legal landings: {legal_narrow}. Target hits: {aim_narrow}.", "",
        f"Across all 256 directional movement challenges, legal returns changed {legal_axes}; target hits changed {aim_axes}. At nominal 25 cm specifically, legality changed {legal25}; aiming changed {aim25}.", "", table, "",
        "Each table cell keeps the same cases and denominator. Nominal feed displacement is measured from the starting paddle face; it is not required or actual root travel. The 50–100 cm probes measure transfer beyond the trained focus range.", "", retention, "",
        "The owned evaluation Editor is restored. These are reused development anchors from one training lineage; final acceptance seeds remain unused. No promotion, mastery acceptance or automatic extension.", "",
        f"Next action: {next_step}", "",
        "[Final experiment results](research/execution-v1-axes-recovery-final.md) · [Coverage](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)", "", "---", ""]
    goal = (f"Current work: the fixed {step:,}-experience axes endpoint completed all five narrow/wide development evaluations. "
            f"At nominal 25 cm, previous → final legal returns changed {legal25}; target hits changed {aim25}. "
            f"{retention} Next action: {next_step} "
            "Balanced targeting, broader movement and mandatory-bounce variations, deliberate kitchen behavior, mastery thresholds and repeated acceptance remain open. "
            "No automatic training extension or model promotion; final acceptance seeds remain unused. "
            "[Final experiment](research/execution-v1-axes-recovery-final.md) · [Movement evidence](research/execution-v1-wide-movement.md). "
            "Movement-goal, paired ownership and strategy training remain later stages. " + MARKER)
    hierarchy = (f"[Graded movement continuation: final assessment](research/execution-v1-axes-recovery-final.md) completed at {step:,} experiences. "
                 "Recovery accepts opt-in axes focus while preserving default lateral behavior. Fourteen curriculum checks passed; the final executor was compared on unchanged narrow and wide development anchors with exact paired observations. "
                 f"Narrow target hits changed {aim_narrow}. At nominal 25 cm, legal returns changed {legal25} and target hits changed {aim25}. "
                 "This changes executor practice, not the number of actors. Movement-goal/recover/cover/yield training and the strategy actor remain unimplemented. "
                 f"No executor promotion or mastery acceptance. Next action: {next_step} " + MARKER)
    lines = ["", "## Graded movement continuation: final follow-up", "", MARKER, "",
        f"The [fixed {step:,}-experience endpoint](execution-v1-axes-recovery-final.md) completed the two preserved batteries: narrow 256 base resets under A/B/random and wide 512 under A/B. The new focus trained 6.25–25 cm nominal left/right/shallow/deep shifts; the retained narrow evaluation recipe stays lateral and the standalone wide recipe disables recovery. Full initial physical and goal observations matched the historical comparisons.", "",
        f"Previous endpoint → final narrow legality: {legal_narrow}. Narrow target hits: {aim_narrow}.", "",
        f"Across the 256 axes challenges, legal returns changed {legal_axes}; target hits changed {aim_axes}.", "", table, "",
        "| Wider transfer distance | A legal / targets / attempts: previous → final | B legal / targets / attempts: previous → final |", "|---|---:|---:|"]
    for cm in (50, 75, 100):
        counts = wide["summaries"][f"nominal-shift/{cm}cm"]
        cells = []
        for condition in ("A", "B"):
            before, after = counts[PARENT][condition], counts[FINAL][condition]
            cells.append(f"{before['legal']} / {before['targets']} / {before['attempts']} → {after['legal']} / {after['targets']} / {after['attempts']}")
        lines.append(f"| {cm} cm | {cells[0]} | {cells[1]} |")
    lines += ["", "| A/B assignment gain, final minus previous endpoint | Reset-weighted estimate [pointwise 95% interval] | Equal-observation-cluster estimate [pointwise 95% interval] |", "|---|---:|---:|"]
    for label, battery, group in (("Narrow all", narrow, "all"), ("Wide all", wide, "all"), ("Wide axes challenges", wide, "schedule/axis-challenge")):
        delta = battery["pairedFinalMinusBaseline"][group][PARENT]
        lines.append(f"| {label} | {interval(delta['assignmentGainResetWeighted'])} | {interval(delta['assignmentGainUniqueClusterWeighted'])} |")
    lines += ["", retention, "",
        "These counts do not close the coverage gaps above. Nominal shift is not body travel, each A/B condition reuses the same physical cases, and the player/direction/feed joint cells remain sparse. The 50–100 cm tests probe beyond the trained focus. Actual bounce and volley contact flags, accepted-contact root displacement and no-contact travel remain in the complete analysis; a feed name alone does not establish a contact mode.", "",
        "The same selected checkpoint must still meet predeclared per-skill criteria with repeat evidence before mastery can be considered. Wider starts/timing, varied mandatory-bounce receiving, kitchen decisions, paired cooperation and full 2v2 are not established by this comparison. Final acceptance seeds remain unused. No automatic extension or model promotion.", "",
        f"Next action: {next_step}", ""]
    return "\n".join(current), goal, hierarchy, "\n".join(lines)


def replace_paragraph(text, prefix, replacement):
    matches = list(re.finditer(r"(?m)^" + re.escape(prefix) + r"[^\r\n]*(?:\r?\n(?!\r?$)[^\r\n]+)*", text))
    require(len(matches) == 1, f"Expected one current paragraph starting {prefix!r}; review changed document")
    match = matches[0]
    return text[:match.start()] + replacement + text[match.end():]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--next-step", required=True, help="Root's explicit next action after reviewing all final results")
    args = parser.parse_args()
    root = args.root.resolve()
    next_step = args.next_step.strip()
    require(next_step and "\x00" not in next_step, "Explicit next-step prose is required")
    next_step = " ".join(next_step.split())
    base, archive = root / BASE, root / ARCHIVE
    audit = archive / "doc-update"
    require(not audit.exists(), "Document update already exists; preserve prior/partial result")
    analysis, plan = read(base / "audit/analysis.json"), read(base / "plan.json")
    manifest = read(archive / "results/archive-manifest.json")
    require(manifest["status"] == "complete_axes_results_archive" and analysis["status"] == "complete_axes_recovery_final_assessment", "Final results must be complete and archived")
    require(manifest["analysisHash"] == sha(base / "audit/analysis.json") and manifest["planHash"] == sha(base / "plan.json"), "Final results changed after archive")
    require(manifest["report"]["path"] == REPORT and sha(root / REPORT) == manifest["report"]["sha256"], "Final report differs from archive")
    require(analysis["sourceIdentity"] == plan["sourceIdentity"] == manifest["sourceIdentity"], "Final source identities differ")
    require(all(analysis[key] is False for key in ("promoted", "automaticExtension", "masteryAccepted", "finalSeedsConsumed")), "Unexpected acceptance declaration")
    require(read(base / "candidate-evaluation-editor-restored.json")["restored"] is True, "Evaluation Editor not restored")
    ledger = root / "artifacts/player-v3/seed-ledger.json"
    require(read(ledger)["finalSeedsConsumed"] == [] and sha(ledger) == analysis["inputSha256"][ledger.relative_to(root).as_posix()], "Seed ledger changed since assessment")
    for identity in analysis["modelIdentities"].values():
        for field, hash_field in (("assetPath", "modelHash"), ("checkpoint", "checkpointHash")):
            require(sha(root / identity[field]) == identity[hash_field], "Selected model/checkpoint changed")
    current, goal, hierarchy, coverage = render_blocks(analysis, next_step)
    before = {relative: (root / relative).read_bytes() for relative in FILES}
    text = {relative: raw.decode("utf-8-sig") for relative, raw in before.items()}
    require(all(MARKER not in value for value in text.values()), "Latest axes result has already been documented")
    require("execution-axes-recovery-01" in text[FILES[1]] and "graded four-direction training is running" in text[FILES[1]], "Goal no longer contains the expected running state; review before updating")
    require("[Graded movement continuation](research/execution-v1-axes-recovery.md) is running" in text[FILES[2]], "Hierarchy running paragraph changed; review before updating")
    after = {}
    for relative in FILES:
        newline = "\r\n" if b"\r\n" in before[relative] else "\n"
        bom = b"\xef\xbb\xbf" if before[relative].startswith(b"\xef\xbb\xbf") else b""
        if relative == FILES[0]:
            # Preserve the complete previous status history byte-for-byte.
            after[relative] = bom + current.replace("\n", newline).encode() + before[relative][len(bom):]
        elif relative == FILES[1]:
            after[relative] = bom + replace_paragraph(text[relative], "Current work:", goal.replace("\n", newline)).encode()
        elif relative == FILES[2]:
            after[relative] = bom + replace_paragraph(text[relative], "[Graded movement continuation](research/execution-v1-axes-recovery.md) is running", hierarchy.replace("\n", newline)).encode()
        else:
            after[relative] = before[relative] + coverage.replace("\n", newline).encode()
        require(after[relative] != before[relative], "Document update is empty")
    # Snapshot history/report/evidence hashes before creating the additive audit.
    historical = {root / OLD_REPORT: sha(root / OLD_REPORT), root / REPORT: sha(root / REPORT)}
    for folder in (archive / "setup", archive / "launch", archive / "results"):
        historical.update({path: sha(path) for path in folder.rglob("*") if path.is_file()})
    audit.mkdir(parents=True, exist_ok=False)
    try:
        records = []
        for relative in FILES:
            original, proposed = audit / "before" / relative, audit / "after" / relative
            original.parent.mkdir(parents=True, exist_ok=True)
            proposed.parent.mkdir(parents=True, exist_ok=True)
            with original.open("xb") as handle: handle.write(before[relative])
            with proposed.open("xb") as handle: handle.write(after[relative])
            records.append(dict(path=relative, beforeSha256=digest(before[relative]), afterSha256=digest(after[relative]),
                                beforeCopy=original.relative_to(root).as_posix(), afterCopy=proposed.relative_to(root).as_posix()))
        script = audit / Path(__file__).name
        with script.open("xb") as handle: handle.write(Path(__file__).read_bytes())
        for relative in FILES:
            require((root / relative).read_bytes() == before[relative], "Document changed during update preflight")
        for relative in FILES:
            (root / relative).write_bytes(after[relative])
        require(all((root / relative).read_bytes() == after[relative] for relative in FILES), "Written document differs from preserved proposal")
        require(all(sha(path) == expected for path, expected in historical.items()), "Historical evidence/report bytes changed")
        write_json(audit / "manifest.json", dict(status="current_documents_updated", files=records, nextStep=next_step,
            analysisHash=sha(base / "audit/analysis.json"), sourceIdentity=analysis["sourceIdentity"], scriptSha256=sha(script),
            historicalInputs={path.relative_to(root).as_posix(): expected for path, expected in historical.items()},
            noNewEvaluation=True, noTrainingLaunched=True, noHistoricalReportsChanged=True,
            promoted=False, automaticExtension=False, masteryAccepted=False, finalSeedsConsumed=False))
        print(json.dumps(dict(updated=list(FILES), audit=str(audit), nextStep=next_step, masteryAccepted=False), indent=2))
    except BaseException as error:
        write_json(audit / "failure.json", dict(status="partial_update_preserved", error=repr(error), traceback=traceback.format_exc(),
                                               message="Exact before/after bytes are preserved; do not rerun over this audit.", masteryAccepted=False))
        raise


if __name__ == "__main__":
    main()
