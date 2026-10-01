"""Run the reviewed reward checks through Unity CLI; preserve exact test evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--attempt", type=int, default=2)
    args = parser.parse_args()
    root, here = Path("F:/dev/picklebot"), Path(__file__).resolve().parent
    metadata = json.loads(args.metadata.read_text(encoding="utf-8-sig"))
    name = f"movement-progress-tests-{args.attempt:02}"
    xml = root / "artifacts/hierarchy-v1" / (name + ".xml")
    console, editor_log = here / (name + "-console.log"), here / (name + "-editor.log")
    before_path, after_path = here / (name + "-settings-before.asset"), here / (name + "-settings-after.asset")
    record_path = here / (name + "-result.json")
    if any(p.exists() for p in (xml, console, editor_log, before_path, after_path, record_path)):
        raise RuntimeError("Preserve the existing test attempt; use a new attempt number after fixing a failure")
    settings = root / "ProjectSettings/ProjectSettings.asset"
    before = settings.read_bytes()
    before_path.write_bytes(before)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    command = [str(Path.home() / "AppData/Local/Unity/bin/unity.exe"), "test", str(root), "--mode", "EditMode",
        "--filter", "Picklebot.PlayerControlsIntegration.Tests.PlayerReturnProgressV3Tests", "--output", str(xml), "--timeout", "900", "--format", "json"]
    with console.open("x", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    after = settings.read_bytes()
    after_path.write_bytes(after)
    source_log = Path.home() / "AppData/Local/Unity/Editor/Editor.log"
    if source_log.is_file():
        shutil.copyfile(source_log, editor_log)
    # The installed test runner has previously removed only this define. Restore
    # it solely on exact byte equality with that known transformation.
    unchanged = after == before
    known_runner_change = after == before.replace(b";SENTIS_ANALYTICS_ENABLED", b"")
    restored = unchanged or known_runner_change
    if known_runner_change and not unchanged:
        settings.write_bytes(before)
    record = dict(args=command, exitCode=result.returncode, metadataHash=sha(args.metadata),
        consoleHash=sha(console), editorLogHash=sha(editor_log) if editor_log.exists() else None,
        testResultHash=sha(xml) if xml.exists() else None, beforeSettingsHash=sha(before_path), afterTestSettingsHash=sha(after_path),
        knownTestRunnerDefineRemoval=known_runner_change and not unchanged, originalSettingsRestored=restored,
        finalSettingsHash=sha(settings), scriptHash=sha(Path(__file__)))
    with record_path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps(record, indent=2))
    if not restored:
        raise RuntimeError("Unexpected settings edit preserved; inspect before restoring or building")
    if result.returncode != 0 or not xml.is_file():
        raise RuntimeError("Unity test attempt failed; inspect preserved logs")


if __name__ == "__main__":
    main()
