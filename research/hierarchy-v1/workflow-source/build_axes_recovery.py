"""DRAFT: record and build the applied axes patch after passing Unity checks.

The caller applies the patch, installs the integration test, completes tests and
closes/saves the Editor first. This script never applies source edits or stops an
existing Editor. It uses the established ExecutionBuildV1 CLI entry point.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

BASE = "artifacts/hierarchy-v1/axes-recovery-01"
OLD = "artifacts/hierarchy-v1/smooth-distance-01"
TEST = "Assets/Picklebot/PlayerLearning/Tests/PlayerAxesRecoveryIntegrationV3Tests.cs"
GOLDEN = "Assets/Picklebot/PlayerLearning/Tests/Fixtures/axes-recovery-golden.json"
MODEL = "Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx"
MODEL_HASH = "bc6f8be16b791a2cd253b150b3f4c4c2492cdc0e65f94fa305ab4addefe78d51"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, document):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--tests", type=Path, required=True, help="Completed Unity NUnit XML")
    parser.add_argument("--build-after-tests", action="store_true")
    args = parser.parse_args()
    require(args.build_after_tests, "Draft: apply patch and finish Unity tests before building")
    root, here = args.root.resolve(), Path(__file__).resolve().parent
    base, output = root / BASE, root / BASE / "execution-axes-build-01"
    require(not base.exists(), "Use a fresh build campaign; failed attempts remain preserved")
    tests_path = args.tests.resolve()
    tests = ET.parse(tests_path).getroot()
    require(tests.attrib.get("result") == "Passed", "Unity checks did not pass")
    cases = list(tests.iter("test-case"))
    axes = [c for c in cases if "PlayerAxesRecoveryIntegrationV3Tests." in c.attrib.get("fullname", "")]
    require(len(axes) == 9 and all(c.attrib.get("result") == "Passed" for c in axes), "All nine axes/default reset checks must pass")
    required = ["PlayerRecoveryScheduleV3Tests.MixtureBalancesEverySeatRangeAndExplicitlyOversamplesLeftBounce",
                "PlayerRecoveryScheduleV3Tests.ScheduledResetMatchesDirectDrillIncludingObservationsAndReward",
                "PlayerRecoveryScheduleV3Tests.WorkerValidationRejectsIncompleteOrIncompatibleRecoveryAndKeepsOldModeOptIn",
                "PlayerInterleavedRecoveryV3Tests.InterleavingPreservesEveryOriginalSeedAcrossAllWorkerCycles",
                "PlayerInterleavedRecoveryV3Tests.EverySlidingSixteenStartsRetainsTheExactGroupMixture"]
    for name in required:
        require(any(name in c.attrib.get("fullname", "") and c.attrib.get("result") == "Passed" for c in cases), f"Required regression check missing: {name}")
    old, patch = read(root / OLD / "source-records.json"), read(here / "axes-recovery-patch.json")
    require(old["sourceIdentity"] == patch["oldSourceIdentity"], "Patch baseline source differs")
    require(sha(here / "axes-recovery-opt-in.patch") == patch["patchSha256"], "Patch artifact changed")
    require(sha(here / "axes-recovery-golden.json") == patch["goldenSha256"], "Golden evidence changed")
    require(sha(root / GOLDEN) == patch["goldenSha256"], "Install the unchanged golden fixture in the repo test Fixtures directory")
    paths = [p for p in (root / "Assets/Picklebot").rglob("*") if p.is_file() and p.suffix in (".cs", ".asmdef")]
    paths += [root / p for p in ("Packages/manifest.json", "Packages/packages-lock.json", "ProjectSettings/ProjectVersion.txt",
                                "ProjectSettings/ProjectSettings.asset", "ProjectSettings/TimeManager.asset", "ProjectSettings/DynamicsManager.asset")]
    files = {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}
    require(set(files)-set(old["files"]) == {TEST} and not (set(old["files"])-set(files)), "Unexpected source inventory changes")
    changed = {path for path in old["files"] if files[path] != old["files"][path]}
    require(changed == set(patch["changedFiles"]), "Source changed beyond the two proposed runtime files")
    for path, entry in patch["changedFiles"].items():
        require(old["files"][path] == entry["oldSha256"] and files[path] in (entry["proposedLfSha256"], entry["proposedCrlfSha256"]), f"Applied patch differs: {path}")
    require((root / TEST).read_text(encoding="utf-8-sig") == (here / Path(TEST).name).read_text(encoding="utf-8-sig"), "Installed integration test differs from prepared test")
    identity = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(identity != old["sourceIdentity"], "Axes training must use a new source identity")
    require(sha(root / MODEL) == MODEL_HASH, "Worker embedded initializer changed")
    cli = Path.home() / "AppData/Local/Unity/bin/unity.exe"
    require(cli.is_file(), "Official Unity CLI is not at the established path")
    command = [str(cli), "run", str(root), "--timeout", "900", "--format", "json", "--", "-executeMethod",
               "Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine", "--execution-output", str(output),
               "--execution-source", identity, "--execution-model-hash", MODEL_HASH, "--execution-model", MODEL]
    base.mkdir()
    source = {"sourceIdentity": identity, "files": files, "contract": old["contract"], "parentSourceIdentity": old["sourceIdentity"],
              "changes": sorted(changed), "addedTest": TEST, "patchHash": patch["patchSha256"],
              "goldenHash": patch["goldenSha256"], "goldenPath": GOLDEN, "testsHash": sha(tests_path), "testsPath": str(tests_path)}
    write(base / "source-records.json", source)
    write(base / "build-launch.json", {"args": command, "scriptHash": sha(Path(__file__)), "sourceIdentity": identity,
                                       "sourceRecordHash": sha(base / "source-records.json"), "unityCliHash": sha(cli)})
    with (base / "build-console.log").open("x", encoding="utf-8") as console:
        completed = subprocess.run(command, cwd=root, stdout=console, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    require(completed.returncode == 0, "Build failed; preserve and inspect build-console.log")
    result = read(output / "build-result.json")
    require(result["status"] == "Succeeded" and result["errors"] == 0 and result["sourceIdentity"] == identity
            and result["modelHash"] == MODEL_HASH, "Standalone build result mismatch")
    require(all(sha(root / path) == digest for path, digest in files.items()), "Source changed during build")
    require({p.relative_to(root).as_posix() for p in (root / "Assets/Picklebot").rglob("*")
             if p.is_file() and p.suffix in (".cs", ".asmdef")} == {p for p in files if p.startswith("Assets/")},
            "Source inventory changed during build")
    require(sha(root / GOLDEN) == patch["goldenSha256"], "Golden fixture changed during build")
    build_files = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    build_id = hashlib.sha256(json.dumps(build_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(build_id != read(root / OLD / "build-verification.json")["buildIdentity"], "Old build identity cannot be reused")
    write(base / "build-verification.json", {"directory": str(output), "sourceIdentity": identity,
                                           "buildIdentity": build_id, "files": build_files})
    print(json.dumps({"base": str(base), "sourceIdentity": identity, "buildIdentity": build_id, "trainingLaunched": False}))


if __name__ == "__main__":
    main()
