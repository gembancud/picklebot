"""Archive an actually launched reward arm; no training-result claim.

Requires current source at Git HEAD, passed tests, exact resume proof and eight
configured live workers. Keeps immutable launch metadata; never copies evolving
trainer console, worker rollouts, executable build or loaded checkpoint tensors.
No work on import. Exclusive destinations preserve any previous/partial attempt.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET

BASE = "artifacts/hierarchy-v1/movement-progress-01"
CONTROL = "artifacts/hierarchy-v1/axes-recovery-01"
EVIDENCE = "docs/research/execution-v1-evidence/movement-progress-01/setup-launch"
WORKFLOW = "research/hierarchy-v1/movement-progress-01/setup-launch"
REPORT = "docs/research/execution-v1-movement-progress.md"
SUPPLEMENTAL_EDITOR_LOG_HASH = "fb8dc17465f4ddad538085db49b4eb72e61454e45618a5fefeab2bfbd17cd719"


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def inside(root, relative):
    path = (root / relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(root), "Path escaped intended root")
    return path


def live_process(pid, recorded_start=None):
    """Read only the named owned PID; avoid reporting a completed run as running."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    require(handle, f"Owned process {pid} is not accessible/alive")
    try:
        code = wintypes.DWORD()
        require(kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259, f"Owned process {pid} is no longer running")
        stamps = [wintypes.FILETIME() for _ in range(4)]
        require(kernel.GetProcessTimes(handle, *(ctypes.byref(stamp) for stamp in stamps)), "Cannot read owned process creation time")
        created = ((stamps[0].dwHighDateTime << 32) + stamps[0].dwLowDateTime) / 10000000 - 11644473600
        require(recorded_start is None or abs(created - recorded_start) < 120, "Trainer PID creation time differs from launch record")
        return dict(pid=int(pid), observedAt=time.time(), creationTime=created, running=True)
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--scripts", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    require(os.name == "nt", "Use the project Windows host")
    root, here, metadata_path = args.root.resolve(), args.scripts.resolve(), args.metadata.resolve()
    base, audit = root / BASE, root / BASE / "training"
    dest, workflow, report_path = (inside(root, value) for value in (EVIDENCE, WORKFLOW, REPORT))
    require(not dest.exists() and not workflow.exists() and not report_path.exists(), "Preserve existing/partial launch archive")
    require(not any((audit / name).exists() for name in ("verification.json", "failure.json", "process-result.json")), "Use a final/failure report instead of a running-launch archive")
    plan, source, build, launch, manifest, proof, process = (read(path) for path in (
        base / "plan.json", base / "source-records.json", base / "build-verification.json", audit / "launch.json",
        audit / "manifest.json", audit / "resume-load-proof.json", audit / "process.json"))
    metadata = read(metadata_path)
    require(plan["status"] == "frozen_movement_progress_after_axes_review" and plan["initialStep"] == 1048609
            and plan["targetGlobalStep"] == 2097152 and plan["rewardChange"]["focusOnly"] is True,
            "Unexpected campaign or reward scope")
    require(source["sourceIdentity"] == build["sourceIdentity"] == plan["sourceIdentity"] == launch["sourceIdentity"], "Source identity differs")
    require(source["patchMetadataHash"] == sha(metadata_path) and source["patchHash"] == metadata["patchSha256"], "Patch metadata changed")
    require(sha(Path(metadata["patchPath"])) == metadata["patchSha256"], "Patch bytes changed")
    require(launch["planHash"] == sha(base / "plan.json") and launch["manifestHash"] == sha(audit / "manifest.json")
            and launch["configHash"] == plan["configHash"] == sha(root / plan["configPath"]), "Frozen launch inputs differ")
    require(launch["scriptHash"] == plan["runnerHash"] == sha(here / "run_movement_progress.py")
            and sha(here / "prepare_movement_progress.py") == plan["prepareScriptHash"], "Prepare/runner code changed")
    require(proof["status"] == "exact_registered_state_restored" and proof["globalStep"] == plan["initialStep"]
            and proof["actorCriticNormalizersAndAdamExact"] is True and launch["resumeProof"] == proof,
            "Exact registered-state resume proof missing")
    require(proof["copiedCheckpointHash"] == plan["parentCheckpointHash"] and sha(audit / "resume-loaded-state.pt") == proof["snapshotHash"], "Resume state proof changed")
    require(manifest == plan["trainingManifest"] and manifest["movementForwardProgressReward"] is True
            and manifest["workerCount"] == 8 and manifest["arenasPerWorker"] == 16,
            "Actual manifest differs from the frozen reward arm")
    copies, references = {}, {}

    def queue(original, target, expected=None):
        original, target = original.resolve(), target.resolve()
        require(original.is_file() and (target.is_relative_to(dest) or target.is_relative_to(workflow)), "Invalid archive path")
        digest = sha(original)
        require(expected is None or digest == expected, "Input hash mismatch: " + str(original))
        require(not target.exists(), "Archive target already exists")
        if target in copies: require(copies[target] == (original, digest), "Archive destination collision")
        copies[target] = original, digest

    for filename in ("plan.json", "source-records.json", "build-verification.json", "build-launch.json", "build-console.log"):
        queue(base / filename, dest / "setup" / filename)
    queue(Path(build["directory"]) / "build-result.json", dest / "setup/build-result.json", build["files"]["build-result.json"])
    for filename in ("launch.json", "manifest.json", "process.json", "resume-load-proof.json", "status-remap.json", "parent-training-status.json", "parent-result-inputs.json", "seed-ledger-before.json", "seed-ledger-allocation.json"):
        queue(audit / filename, dest / "launch" / filename)
    queue(root / plan["configPath"], workflow / "config" / Path(plan["configPath"]).name, plan["configHash"])
    queue(metadata_path, dest / "setup/patch-metadata.json", source["patchMetadataHash"])
    queue(Path(metadata["patchPath"]), workflow / "movement-forward-progress.patch", metadata["patchSha256"])
    for relative, item in {**metadata["changedFiles"], **metadata["addedFiles"]}.items():
        require(sha(root / relative) == item["proposedSha256"], "Installed proposal changed: " + relative)
        queue(Path(item["workspacePath"]), workflow / "proposed" / relative, item["proposedSha256"])
    installed = here / "movement-progress-installed.json"
    require(read(installed)["metadataHash"] == sha(metadata_path), "Installation record differs")
    queue(installed, dest / "setup/installation.json")
    build_launch = read(base / "build-launch.json")
    scripts = {"run_movement_progress.py": plan["runnerHash"], "prepare_movement_progress.py": plan["prepareScriptHash"],
               "install_build_movement_progress.py": build_launch["scriptHash"]}
    for filename in ("prepare_forward_progress_patch.py", "bundle_forward_progress_patch.py", "test_movement_progress.py", "test_movement_progress_editmode.py", Path(__file__).name):
        scripts.setdefault(filename, sha(here / filename))
    for filename, expected in scripts.items(): queue(here / filename, workflow / filename, expected)

    tests_path = Path(source["testsPath"])
    require(sha(tests_path) == source["testsHash"] and ET.parse(tests_path).getroot().attrib.get("result") == "Passed", "Passing tests differ")
    selected_xml = {tests_path.resolve(): dict(sha256=source["testsHash"], mode="PlayMode", expectedCases=48)}
    require(len(source["additionalTests"]) == 1 and source["totalPassedTestCases"] == 50, "Expected 48 PlayMode plus 2 EditMode checks")
    for item in source["additionalTests"]:
        path = Path(item["path"]).resolve()
        require(path not in selected_xml and sha(path) == item["sha256"], "Supplemental test XML changed or duplicated")
        selected_xml[path] = dict(sha256=item["sha256"], mode="EditMode", expectedCases=2)
    all_test_names, test_summary = [], []
    for path, expected in selected_xml.items():
        xml_root = ET.parse(path).getroot()
        cases = list(xml_root.iter("test-case"))
        require(xml_root.attrib.get("result") == "Passed" and len(cases) == expected["expectedCases"]
                and all(case.attrib.get("result") == "Passed" for case in cases), "Selected test cases incomplete or failed")
        all_test_names.extend(case.attrib["fullname"] for case in cases)
        test_summary.append(dict(path=str(path), sha256=expected["sha256"], mode=expected["mode"], passed=len(cases)))
        queue(path, dest / "tests" / path.name, expected["sha256"])
    require(len(all_test_names) == len(set(all_test_names)) == 50, "Test count contains duplicate cases")
    selected_test_records = {}
    test_records = sorted(here.glob("movement-progress-tests-*-result.json"))
    require(test_records, "Test runner records missing")
    for record_path in test_records:
        record = read(record_path)
        name = record_path.name.removesuffix("-result.json")
        queue(record_path, dest / "tests" / record_path.name)
        candidates = ((here / (name + "-console.log"), "consoleHash"), (here / (name + "-editor.log"), "editorLogHash"),
                      (here / (name + "-settings-before.asset"), "beforeSettingsHash"), (here / (name + "-settings-after.asset"), "afterTestSettingsHash"))
        for path, key in candidates:
            if record.get(key) is not None: queue(path, dest / "tests" / path.name, record[key])
        xml = Path(record["args"][record["args"].index("--output") + 1])
        if record["testResultHash"] is not None: queue(xml, dest / "tests" / xml.name, record["testResultHash"])
        if xml.resolve() in selected_xml:
            require(xml.resolve() not in selected_test_records, "Multiple wrappers claim the same selected XML")
            selected_test_records[xml.resolve()] = record
    require(set(selected_test_records) == set(selected_xml), "Selected PlayMode/EditMode wrapper records missing")
    for path, record in selected_test_records.items():
        expected = selected_xml[path]
        script_name = "test_movement_progress.py" if expected["mode"] == "PlayMode" else "test_movement_progress_editmode.py"
        require(record["exitCode"] == 0 and record["originalSettingsRestored"] is True
                and record["metadataHash"] == sha(metadata_path) and record["scriptHash"] == scripts[script_name]
                and record["testResultHash"] == expected["sha256"]
                and record["args"][record["args"].index("--mode") + 1] == expected["mode"], "Selected test/settings restoration record differs")
        require(record["finalSettingsHash"] == sha(root / "ProjectSettings/ProjectSettings.asset"), "Project settings changed after tests")
    primary_record = selected_test_records[tests_path.resolve()]
    require(primary_record["editorLogHash"] is None, "Original primary wrapper record was changed")
    supplemental_log = here / "movement-progress-tests-01-editor-supplement.log"
    queue(supplemental_log, dest / "tests" / supplemental_log.name, SUPPLEMENTAL_EDITOR_LOG_HASH)
    supplemental_log_note = dict(path=(dest / "tests" / supplemental_log.name).relative_to(root).as_posix(),
        sha256=SUPPLEMENTAL_EDITOR_LOG_HASH, originalPrimaryEditorLogHash=None,
        provenance="Copied by campaign owner from actual Unity Editor/Editor.log after the primary PlayMode test and before the next Unity invocation; original wrapper used the wrong log path and remains unchanged.")

    # Source is preserved at a commit, rather than copied as another full tree.
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    commit = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    tree = {}
    for entry in subprocess.check_output(git + ["ls-tree", "-r", "-z", "HEAD"]).split(b"\0"):
        if entry:
            record, name = entry.split(b"\t", 1)
            tree[name.decode()] = record.split()[2].decode()
    for relative, expected in source["files"].items():
        path = inside(root, relative)
        require(sha(path) == expected, "Runtime source changed")
        content = path.read_bytes()
        require(tree.get(relative) == hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(), "Commit current runtime source before archiving its launch: " + relative)
        references[str(path)] = dict(path=relative, sha256=expected, mode="runtime source at Git commit", commit=commit)

    # Reuse canonical records already preserved with the axes comparison. Keep
    # unmatched mutable training binaries explicitly local, never relabel copies.
    control_archive_path = root / "docs/research/execution-v1-evidence/axes-recovery-01/results/archive-manifest.json"
    control_archive = read(control_archive_path)
    known = {Path(row["source"]).resolve(): row for row in control_archive["files"] if row["encoding"] == "original bytes"}
    for key, expected in plan["evaluation"]["baselineInputs"].items():
        original = inside(root, key)
        require(sha(original) == expected, "Frozen control/baseline input changed")
        queued = next((target for target, (path, _) in copies.items() if path == original), None)
        if queued is not None:
            references[str(original)] = dict(path=queued.relative_to(root).as_posix(), sha256=expected, mode="new setup/launch byte copy")
            continue
        item = control_archive["analysisInputCoverage"].get(key)
        canonical = root / item["path"] if item else (root / known[original]["archivePath"] if original in known else original)
        require(sha(canonical) == expected, "Canonical control dependency differs")
        references[str(original)] = dict(path=canonical.relative_to(root).as_posix(), sha256=expected,
            mode="existing canonical/reference bytes; not copied into this archive")
    for key, expected in proof["installedSourceHashes"].items():
        original = Path(key).resolve()
        require(sha(original) == expected, "Installed loader source changed")
        prior = control_archive.get("installedLoaderSourceCoverage", {}).get(key)
        if prior and prior["sha256"] == expected:
            canonical = root / prior["archivePath"]
            require(sha(canonical) == expected, "Preserved installed-loader dependency differs")
            references[key] = dict(path=canonical.relative_to(root).as_posix(), sha256=expected, mode="existing exact loader-source archive")
        else:
            queue(original, workflow / "installed-loader" / expected[:16] / original.name, expected)
    helper = root / plan["helperPath"]
    require(sha(helper) == plan["helperHash"], "Pinned continuation helper changed")
    references[str(helper)] = dict(path=plan["helperPath"], sha256=plan["helperHash"], mode="existing helper with original import path")
    ledger = root / "artifacts/player-v3/seed-ledger.json"
    allocation = read(audit / "seed-ledger-allocation.json")
    require(read(ledger)["finalSeedsConsumed"] == [] and sha(ledger) == allocation["ledgerAfterHash"], "Seed ledger changed after this training reuse")
    queue(ledger, dest / "launch/seed-ledger-after.json", allocation["ledgerAfterHash"])
    trainer = live_process(process["pid"], process["started"])
    workers = []
    for index in range(8):
        path = audit / f"worker-{index:02}/worker-startup.json"
        startup = read(path)
        require(startup["status"] == "configured" and not startup["error"] and startup["workerId"] == index
                and startup["trainerRequired"] is True and startup["movementForwardProgressReward"] is True
                and startup["sourceIdentity"] == source["sourceIdentity"] and startup["expectedBuildIdentity"] == build["buildIdentity"]
                and startup["manifestHash"] == sha(audit / "manifest.json") and startup["arenas"] == 16
                and startup["firstSeed"] == manifest["firstSeed"] + index * manifest["seedsPerWorker"]
                and startup["seedCount"] == manifest["seedsPerWorker"], "Worker startup contract differs")
        workers.append({"worker": index, **live_process(startup["processId"])})
        queue(path, dest / f"launch/worker-{index:02}-startup.json")
    observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = ("# Focused forward-progress reward experiment\n\n"
        f"**Running at the recorded launch snapshot ({observed})** on eight workers × sixteen courts. All eight workers reported the new flag enabled. This is launch evidence; no performance improvement has been assessed.\n\n"
        "The arm resumes the complete **1,048,609-experience common-parent checkpoint**, not the regressed axes endpoint, toward the fixed **2,097,152-experience budget**. Actor, critic, normalization, Adam and global step restored exactly through the installed ML-Agents loader. Process RNG/live rollouts restarted.\n\n"
        "The sole experiment change adds up to **0.25 actual post-contact forward-progress reward** to solo positive-range **focus** rally movement episodes. Familiar, prior-court, serve and required-bounce receiving rewards remain unchanged. The axes 6.25–25 cm focus, 25/25/50 mixture, smooth placement reward, PPO, body and observations match the completed control. The flag defaults off, including frozen-policy evaluation.\n\n"
        "All **50 checks passed: 48 in PlayMode and 2 existing return-progress checks in EditMode**. Separate wrapper and XML records preserve the assembly-mode distinction. The primary wrapper's missing-log field remains unchanged; the separately captured actual Editor log is archived with its provenance.\n\n"
        "Matched training seed/reset setup is reused. One new reward arm against an already completed control is not replicated causal proof or bitwise trajectory equivalence. A capped intermediate bonus is not a legal return or a target hit; any earned bonus is not retroactively removed by a later fault.\n\n"
        "After the fixed endpoint, compare the same narrow A/B/random and wide A/B anchors against the initializer, common parent and completed no-progress axes control. Keep their original source/model identities and verify paired observations. Assess legal/all, target/all, directional and distance cells, and both assignment-gain interval estimands. No automatic extension, promotion or mastery acceptance. Final acceptance seeds remain unused.\n\n"
        "[Frozen plan](execution-v1-evidence/movement-progress-01/setup-launch/setup/plan.json) · [Launch archive](execution-v1-evidence/movement-progress-01/setup-launch/archive-manifest.json) · [Completed control](execution-v1-axes-recovery-final.md)\n")
    dest.mkdir(parents=True, exist_ok=False)
    workflow.mkdir(parents=True, exist_ok=False)
    records = []
    try:
        for target, (original, expected) in sorted(copies.items(), key=lambda item: str(item[0])):
            require(sha(original) == expected, "Launch/setup evidence changed during archive")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle: handle.write(original.read_bytes())
            require(sha(target) == expected, "Archive bytes differ")
            records.append(dict(source=str(original), path=target.relative_to(root).as_posix(), sha256=expected))
        require(not (audit / "process-result.json").exists() and not (audit / "failure.json").exists(), "Run ended while recording launch; preserve partial archive")
        for key, item in references.items():
            require(sha(Path(key)) == item["sha256"], "Referenced input changed while archiving launch")
        require(sha(ledger) == allocation["ledgerAfterHash"], "Seed ledger changed while archiving launch")
        live_process(process["pid"], process["started"])
        with report_path.open("x", encoding="utf-8", newline="\n") as handle: handle.write(report)
        write(dest / "archive-manifest.json", dict(status="verified_running_launch_archived", observedAtUtc=observed,
            sourceIdentity=source["sourceIdentity"], sourceGitCommit=commit, buildIdentity=build["buildIdentity"], files=records,
            controlArchiveHash=sha(control_archive_path),
            tests=test_summary, totalPassedTestCases=50, supplementalEditorLog=supplemental_log_note,
            referencedInputs=references, trainer=trainer, workers=workers, planHash=sha(base / "plan.json"),
            report=dict(path=REPORT, sha256=sha(report_path)), archiveScriptSha256=sha(Path(__file__)),
            localLoadedState=dict(path=(audit / "resume-loaded-state.pt").relative_to(root).as_posix(), sha256=proof["snapshotHash"], copied=False),
            noBuildOrCheckpointCopies=True, noEvolvingTrainerConsoleCopied=True, performanceEvaluated=False,
            finalSeedsConsumed=False, promoted=False, masteryAccepted=False))
        print(json.dumps(dict(evidence=str(dest), workflow=str(workflow), report=str(report_path), files=len(records), workersStarted=8, performanceEvaluated=False), indent=2))
    except BaseException as error:
        write(dest / "archive-failure.json", dict(status="partial_launch_archive_preserved", error=repr(error), traceback=traceback.format_exc(), performanceEvaluated=False))
        raise


if __name__ == "__main__": main()
