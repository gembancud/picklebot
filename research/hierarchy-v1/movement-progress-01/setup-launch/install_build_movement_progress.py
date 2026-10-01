"""Install a reviewed reward patch, or build it after completed Unity checks.

Separate explicit phases prevent building untested edits. Never stops an Editor,
launches training, rewrites old evidence, or repeats an existing build directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

BASE = "artifacts/hierarchy-v1/movement-progress-01"
OLD = "artifacts/hierarchy-v1/axes-recovery-01"
MODEL = "Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx"
MODEL_HASH = "bc6f8be16b791a2cd253b150b3f4c4c2492cdc0e65f94fa305ab4addefe78d51"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def inside(root, relative):
    path = (root / relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(root), "Path escapes repository")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--phase", choices=("install", "build"), required=True)
    parser.add_argument("--tests", type=Path)
    parser.add_argument("--additional-tests", type=Path, action="append", default=[])
    args = parser.parse_args()
    root, here = args.root.resolve(), Path(__file__).resolve().parent
    metadata_path = args.metadata.resolve()
    metadata, old = read(metadata_path), read(root / OLD / "source-records.json")
    require(metadata["oldSourceIdentity"] == old["sourceIdentity"], "Wrong reward patch baseline")
    require(sha(Path(metadata["patchPath"])) == metadata["patchSha256"], "Reviewed patch changed")
    require(read(root / OLD / "audit/analysis.json")["status"] == "complete_axes_recovery_final_assessment", "Finish the control assessment first")
    require(read(root / "docs/research/execution-v1-evidence/axes-recovery-01/results/archive-manifest.json")["status"] == "complete_axes_results_archive", "Archive the control first")
    changed, added = metadata["changedFiles"], metadata["addedFiles"]
    require(changed and added and not (set(changed) & set(added)), "Invalid patch inventory")
    for relative, item in {**changed, **added}.items():
        inside(root, relative)
        require(sha(Path(item["workspacePath"])) == item["proposedSha256"], "Prepared patch bytes changed: " + relative)
        if relative in changed:
            require(old["files"][relative] == item["oldSha256"], "Unexpected patch parent: " + relative)
    installed = here / "movement-progress-installed.json"
    if args.phase == "install":
        require(not installed.exists(), "Patch install already recorded")
        for relative, digest in old["files"].items():
            require(sha(root / relative) == digest, "Source changed before reward installation: " + relative)
        require(all(not (root / path).exists() for path in added), "New reward files already exist")
        for relative, item in {**changed, **added}.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(Path(item["workspacePath"]).read_bytes())
            require(sha(path) == item["proposedSha256"], "Installed bytes differ")
        write(installed, dict(status="installed_for_testing", metadataHash=sha(metadata_path),
            patchHash=metadata["patchSha256"], files={p: i["proposedSha256"] for p, i in {**changed, **added}.items()}))
        print(json.dumps(dict(status="installed_for_testing", files=len(changed) + len(added))))
        return
    require(args.tests is not None and installed.is_file(), "Install and complete Unity checks before building")
    require(read(installed)["metadataHash"] == sha(metadata_path), "Patch metadata changed after installation")
    tests_path = args.tests.resolve()
    tests = ET.parse(tests_path).getroot()
    require(tests.attrib.get("result") == "Passed", "Unity checks did not pass")
    cases = list(tests.iter("test-case"))
    additional_tests = []
    for path in args.additional_tests:
        path = path.resolve()
        supplement = ET.parse(path).getroot()
        require(supplement.attrib.get("result") == "Passed", "Supplemental Unity checks did not pass")
        cases.extend(supplement.iter("test-case"))
        additional_tests.append(dict(path=str(path), sha256=sha(path)))
    require(metadata.get("requiredPassedTestClasses"), "Explicit required test classes are missing")
    for name, minimum in metadata["requiredPassedTestClasses"].items():
        matching = [c for c in cases if name + "." in c.attrib.get("fullname", "")]
        require(len(matching) >= minimum and all(c.attrib.get("result") == "Passed" for c in matching), "Missing or failed checks: " + name)
    paths = [p for p in (root / "Assets/Picklebot").rglob("*") if p.is_file() and p.suffix in (".cs", ".asmdef")]
    paths += [root / p for p in old["files"] if not p.startswith("Assets/")]
    files = {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}
    added_source = {p for p in added if Path(p).suffix in (".cs", ".asmdef")}
    require(set(files) == set(old["files"]) | added_source, "Source inventory changed beyond reward patch")
    for relative, digest in files.items():
        expected = {**changed, **added}.get(relative, {}).get("proposedSha256", old["files"].get(relative))
        require(digest == expected, "Source changed outside reviewed patch: " + relative)
    for relative, item in added.items():
        require(sha(root / relative) == item["proposedSha256"], "Added file differs from reviewed proposal")
    require(sha(root / MODEL) == MODEL_HASH, "Embedded initializer changed")
    identity = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(identity != old["sourceIdentity"], "Reward branch requires a new source identity")
    base, output = root / BASE, root / BASE / "execution-movement-progress-build-01"
    require(not base.exists(), "Preserve existing build campaign")
    cli = Path.home() / "AppData/Local/Unity/bin/unity.exe"
    require(cli.is_file(), "Official Unity CLI missing")
    command = [str(cli), "run", str(root), "--timeout", "900", "--format", "json", "--", "-executeMethod",
        "Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine", "--execution-output", str(output),
        "--execution-source", identity, "--execution-model-hash", MODEL_HASH, "--execution-model", MODEL]
    base.mkdir()
    write(base / "source-records.json", dict(sourceIdentity=identity, files=files, contract=old["contract"],
        parentSourceIdentity=old["sourceIdentity"], changes=sorted(changed), addedFiles=sorted(added),
        patchHash=metadata["patchSha256"], patchMetadataHash=sha(metadata_path), testsPath=str(tests_path), testsHash=sha(tests_path),
        additionalTests=additional_tests, totalPassedTestCases=len(cases)))
    write(base / "build-launch.json", dict(args=command, scriptHash=sha(Path(__file__)), sourceIdentity=identity,
        sourceRecordHash=sha(base / "source-records.json"), unityCliHash=sha(cli)))
    with (base / "build-console.log").open("x", encoding="utf-8") as console:
        result = subprocess.run(command, cwd=root, stdout=console, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    require(result.returncode == 0, "Build failed; preserve its log")
    result = read(output / "build-result.json")
    require(result["status"] == "Succeeded" and result["errors"] == 0 and result["sourceIdentity"] == identity
        and result["modelHash"] == MODEL_HASH, "Unexpected build result")
    require(all(sha(root / p) == digest for p, digest in files.items()), "Source changed during build")
    build_files = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    build_id = hashlib.sha256(json.dumps(build_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(build_id != read(root / OLD / "build-verification.json")["buildIdentity"], "Control worker build reused")
    write(base / "build-verification.json", dict(directory=str(output), sourceIdentity=identity, buildIdentity=build_id, files=build_files))
    print(json.dumps(dict(sourceIdentity=identity, buildIdentity=build_id, trainingLaunched=False)))


if __name__ == "__main__":
    main()
