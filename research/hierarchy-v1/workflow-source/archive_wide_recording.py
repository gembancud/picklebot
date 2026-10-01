"""Archive verified recording evidence without committing the local JPEG gallery.

Run after the original wider diagnostic archive and Editor restoration. All
destinations are exclusive. Pose JSON is losslessly gzip-preserved; JPEGs and the
redundant browser data.js remain local with their exact hashes and byte lengths.
When archiving retry02, preserve failed01 independently; never reconstruct poses.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import traceback

CAMPAIGN = "artifacts/hierarchy-v1/wide-movement-fixture-01"
ORIGINAL = "docs/research/execution-v1-evidence/wide-movement-01"
EVIDENCE = "docs/research/execution-v1-evidence/wide-movement-review-01"
WORKFLOW = "research/hierarchy-v1/wide-movement-review-01"
REPORT = "docs/research/execution-v1-wide-movement-review.md"
WORKSPACE = Path(__file__).resolve().parents[2]
SCRIPT_NAMES = ("prepare_wide_recording.py", "wide_recording_capture.cs", "build_wide_recording.py", "wide_recording_plan.md", "archive_wide_recording.py")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_text(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--output-name", default="wide-movement-review-01")
    parser.add_argument("--failed-output-name", default="wide-movement-review-01")
    args = parser.parse_args()
    root = args.root.resolve()
    out = (WORKSPACE/"outputs"/args.output_name).resolve()
    require(out.is_relative_to((WORKSPACE/"outputs").resolve()), "Recording must be inside workspace outputs")
    base, original, evidence, workflow = (root/name for name in (CAMPAIGN,ORIGINAL,EVIDENCE,WORKFLOW))
    report_path=root/REPORT
    require(not evidence.exists() and not workflow.exists() and not report_path.exists(), "Archive destinations must be new")
    require(not (out/"error.json").exists(), "Failed capture must not be archived as verified")
    require(read(base/"candidate-evaluation-editor-restored.json")["restored"] is True, "Owned Editor must be restored first")
    manifest, verified, complete, parity = (read(out/name) for name in ("manifest.json","verification.json","complete.json","parity.json"))
    ui_paths=list(out.glob("*ui-validation.json"))
    require(len(ui_paths) == 1, "Preserve the local UI validation limitation before archiving")
    ui_validation=read(ui_paths[0])
    old=read(original/"archive-manifest.json")
    require(old["status"] == "complete_byte_preserved_archive" and old["masteryAccepted"] is False, "Original wider diagnostic archive is incomplete")
    require(verified["status"] == "verified_policy_recordings" and complete["status"] == "complete_verified_replay"
            and parity["status"] == "exact_float32_parity" and parity["mismatches"] == [], "Unverified recording")
    require(verified["episodes"] == verified["referenceMatches"] == complete["episodes"] == complete["matchesReference"] == 512
            and manifest["goalRecipe"]["conditions"] == ["A"] and verified["condition"] == "A", "Replay scope mismatch")
    require(manifest["checkpoint"] == verified["checkpoint"] == 1048609
            and manifest["sourceIdentity"] == verified["sourceIdentity"] == old["sourceIdentity"], "Model/source identity mismatch")
    require(sha(out/"manifest.json") == complete["manifestHash"] and sha(out/"capture.cs") == manifest["captureScriptSha256"], "Frozen manifest/capture mismatch")
    require(sha(out/"evaluation-analysis.json") == manifest["analysisHash"] == old["analysisHash"], "Original outcome analysis changed")
    for field,name in (("preparationScriptSha256","prepare_wide_recording.py"),("captureTemplateSha256","wide_recording_capture.cs")):
        require(sha(Path(__file__).with_name(name)) == manifest[field], "Preparation/template script changed")
    require(sha(Path(__file__).with_name("build_wide_recording.py")) == verified["builderSha256"], "Executed builder changed")
    source=read(out/"source-records.json")
    require(all(sha(root/name) == expected for name,expected in source["files"].items()), "Runtime source changed before archive")
    ledger=root/"artifacts/player-v3/seed-ledger.json"
    require(sha(ledger) == manifest["ledgerHash"] == read(base/"allocation.json")["ledgerAfterHash"]
            and read(ledger)["finalSeedsConsumed"] == [], "Seed ledger changed")
    canonical={}
    for path,expected,label in ((root/manifest["model"],manifest["modelHash"],"canonical frozen model"),
                               (root/manifest["checkpointPath"],manifest["checkpointHash"],"canonical checkpoint")):
        require(sha(path) == expected, "Frozen model/checkpoint changed")
        canonical[path.resolve()] = dict(mode=label,path=path.relative_to(root).as_posix(),sha256=expected)
    # Reference original evidence by already verified archive path, without a
    # second copy of the entire512-reset A/B diagnostic or its source tree.
    for item in old["files"]:
        path=root/item["archivePath"]
        require(path.is_file() and sha(path) == item["sha256"], "Original diagnostic archive bytes changed")
        canonical[Path(item["source"]).resolve()] = dict(mode="original wider diagnostic archive",path=item["archivePath"],sha256=item["sha256"])
    old_manifest_sha=sha(original/"archive-manifest.json")
    copies, compressed, local_only = {}, {}, {}
    failed_attempt=None
    def queue(path, target):
        path=path.resolve()
        require(path.is_file() and not target.exists(), f"Missing source/existing destination: {path}")
        digest=sha(path)
        if path in copies:
            require(copies[path][1] == digest, "Changing queued input")
        else:
            copies[path]=(target,digest)
    image_names=set(verified["imageHashes"])
    actual_images={path.relative_to(out).as_posix() for path in out.rglob("*.jpg")}
    require(image_names == actual_images and len(image_names) == verified["images"] == complete["images"], "JPEG coverage mismatch")
    for relative,expected in verified["imageHashes"].items():
        path=(out/relative).resolve()
        require(path.is_relative_to(out) and sha(path) == expected, "Local JPEG changed")
        local_only[relative]=dict(sha256=expected,bytes=path.stat().st_size,kind="JPEG frame")
    for name,expected in verified["viewerSha256"].items():
        require(sha(out/name) == expected, "Built viewer changed")
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        relative=path.relative_to(out)
        if path.suffix.lower() in (".jpg",".jpeg"):
            continue
        if relative.as_posix() == "data.js":
            local_only["data.js"]=dict(sha256=sha(path),bytes=path.stat().st_size,kind="browser payload duplicating archived pose JSON")
        elif path.name == "recording.json" and relative.parts[0] == "clips":
            compressed[path.resolve()] = (evidence/relative.with_suffix(".json.gz"),sha(path))
        else:
            queue(path,evidence/relative)
    if args.output_name != args.failed_output_name:
        failed=(WORKSPACE/"outputs"/args.failed_output_name).resolve()
        require(failed.is_relative_to((WORKSPACE/"outputs").resolve()) and failed != out, "Invalid failed-attempt directory")
        require((failed/"error.json").is_file() and not (failed/"complete.json").exists(), "Expected preserved failed01 capture")
        failure=read(failed/"error.json")
        failed_manifest=read(failed/"manifest.json")
        require(failed_manifest["modelHash"] == manifest["modelHash"] and failed_manifest["selected"] == manifest["selected"]
                and failed_manifest["firstSeed"] == manifest["firstSeed"] and failed_manifest["sourceIdentity"] == manifest["sourceIdentity"], "Retry changed selected cases/model/source")
        failed_images={}
        failed_pose_records=[]
        for path in failed.rglob("*"):
            if not path.is_file():
                continue
            relative=path.relative_to(failed)
            if path.suffix.lower() in (".jpg",".jpeg"):
                failed_images[relative.as_posix()]=dict(sha256=sha(path),bytes=path.stat().st_size)
            else:
                queue(path,evidence/"failed-attempt-01"/relative)
                if path.name == "recording.json": failed_pose_records.append(relative.as_posix())
        require(not failed_pose_records, "Failed01 unexpectedly has pose records; review lifecycle provenance before archiving")
        require(failure["completedEpisodes"] == 512, "Unexpected earlier capture failure scope")
        amendments=list(out.glob("*amendment*.json")) + list(out.glob("*revision*.json"))
        require(amendments, "Retry must preserve its writer-lifecycle correction amendment")
        revision=read(out/"revision.json")
        require(revision["script"] == "retry_wide_recording.py" and revision["selectionUnchanged"] is True
                and revision["sourceChanged"] is False and revision["newSeedsAllocated"] is False, "Unexpected retry amendment")
        helper=Path(__file__).with_name("retry_wide_recording.py")
        require(sha(helper) == revision["scriptSha256"] and sha(failed/"capture.cs") == revision["oldCaptureSha256"]
                and sha(out/"capture.cs") == revision["newCaptureSha256"], "Retry script/capture identity mismatch")
        require(manifest["originalManifestSha256"] == sha(failed/"manifest.json")
                and manifest["originalErrorSha256"] == sha(failed/"error.json"), "Retry origin identity mismatch")
        queue(helper,workflow/helper.name)
        failed_attempt=dict(localDirectory=str(failed),recordingManifestHash=sha(failed/"manifest.json"),errorHash=sha(failed/"error.json"),
                            status="failed_capture_preserved",completedSimulatorEpisodes=512,poseRecordingFiles=0,
                            jpegFiles=failed_images,imagesKeptLocal=len(failed_images),
                            failureMeaning="Capture completed its simulations, but terminal evidence verification tried to read an open writer. Cleanup discarded unsaved closure-only pose records. JPEGs and raw evidence remain preserved; no reconstructed poses or verified gallery claim.",
                            retryAmendments=[path.name for path in amendments])
    require(len(compressed) == manifest["clipCount"] == complete["clips"] == verified["clips"] <= 8, "Pose recording coverage mismatch")
    for name in SCRIPT_NAMES:
        queue(Path(__file__).with_name(name),workflow/name)
    input_coverage={}
    for key,expected in verified["inputSha256"].items():
        path=Path(key).resolve()
        require(path.is_file() and sha(path) == expected, "Verification input changed: "+key)
        if path in copies:
            target,digest=copies[path]
            require(digest == expected,"Copied input digest mismatch")
            record=dict(mode="byte-preserved copy",path=target.relative_to(root).as_posix(),sha256=expected)
        elif path in compressed:
            target,digest=compressed[path]
            require(digest == expected,"Pose input digest mismatch")
            record=dict(mode="gzip preserving exact original bytes",path=target.relative_to(root).as_posix(),uncompressedSha256=expected)
        elif path in canonical:
            record=canonical[path]
            require(record["sha256"] == expected,"Canonical input digest mismatch")
        elif path.is_relative_to(WORKSPACE/"outputs/drill-museum-01"):
            target=workflow/"legacy-viewer"/path.name
            queue(path,target)
            record=dict(mode="byte-preserved legacy viewer dependency",path=target.relative_to(root).as_posix(),sha256=expected)
        else:
            raise ValueError("Unclassified verification dependency: "+key)
        input_coverage[key]=record
    # Preparation hashes also identify reference summary/model-sidecar files.
    for relative,expected in manifest["referenceInputSha256"].items():
        path=(root/relative).resolve()
        require(path in canonical and canonical[path]["sha256"] == expected and sha(path) == expected, "Missing archived diagnostic reference")
    require(all((out/name).is_file() for name in ("index.html","museum.css","museum.js","data.js")), "Viewer is incomplete")
    evidence.mkdir(parents=True,exist_ok=False)
    workflow.mkdir(parents=True,exist_ok=False)
    written=[]
    try:
        for source_path,(target,expected) in sorted(copies.items(),key=lambda item:str(item[1][0])):
            require(sha(source_path) == expected,"Input changed during archive")
            target.parent.mkdir(parents=True,exist_ok=True)
            require(not target.exists(),"Archive target appeared unexpectedly")
            shutil.copy2(source_path,target)
            require(sha(target) == expected,"Archive copy mismatch")
            written.append(dict(source=str(source_path),archivePath=target.relative_to(root).as_posix(),sha256=expected,mode="byte-preserved copy",bytes=target.stat().st_size))
        for source_path,(target,expected) in sorted(compressed.items(),key=lambda item:str(item[1][0])):
            raw=source_path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == expected,"Pose record changed during archive")
            data=gzip.compress(raw,compresslevel=9,mtime=0)
            require(gzip.decompress(data) == raw,"Pose compression is not lossless")
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as handle: handle.write(data)
            require(hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest() == expected,"Archived pose verification failed")
            written.append(dict(source=str(source_path),archivePath=target.relative_to(root).as_posix(),sha256=sha(target),uncompressedSha256=expected,mode="gzip preserving exact original bytes",bytes=len(data),uncompressedBytes=len(raw)))
        require(all(sha(path) == expected for path,(_,expected) in copies.items()),"Copied source input changed")
        require(all(sha(path) == expected for path,(_,expected) in compressed.items()),"Pose source changed")
        require(all(sha(out/relative) == item["sha256"] for relative,item in local_only.items()),"Local frame/payload changed")
        if failed_attempt:
            failed=Path(failed_attempt["localDirectory"])
            require(all(sha(failed/relative) == item["sha256"] for relative,item in failed_attempt["jpegFiles"].items()),"Failed-attempt image changed")
            write_json(evidence/"failed-attempt-01/local-image-hashes.json",failed_attempt)
        require(sha(ledger) == manifest["ledgerHash"] and read(ledger)["finalSeedsConsumed"] == [],"Ledger changed during archive")
        require(all(sha(root/name) == expected for name,expected in source["files"].items()),"Source changed during archive")
        require(sha(root/manifest["model"]) == manifest["modelHash"] and sha(root/manifest["checkpointPath"]) == manifest["checkpointHash"],"Model changed during archive")
        write_json(evidence/"local-viewer-files.json",dict(localDirectory=str(out),files=local_only,
                   includedInRepository=False,reason="JPEGs remain in the local viewer. data.js duplicates the archived pose records and can be rebuilt with the preserved builder."))
        archive=dict(status="complete_recording_evidence_archive",sourceIdentity=manifest["sourceIdentity"],modelHash=manifest["modelHash"],checkpoint=1048609,
                     originalDiagnosticArchive=ORIGINAL,originalArchiveManifestHash=old_manifest_sha,sourceGitCommit=old["sourceGitCommit"],
                     recordings=manifest["clipCount"],replayedEpisodes=512,condition="A",imagesKeptLocal=len(image_names),
                     archivedFiles=written,verificationInputCoverage=input_coverage,localViewerDirectory=str(out),
                     selectionRule=manifest["selectionRule"],unavailableCategories=manifest["unavailable"],
                     analysisHash=manifest["analysisHash"],recordingManifestHash=sha(out/"manifest.json"),verificationHash=sha(out/"verification.json"),
                     ledgerHash=manifest["ledgerHash"],ledgerModified=False,finalSeedsConsumed=False,masteryAccepted=False)
        archive["successfulLocalAttempt"] = args.output_name
        archive["preservedFailedAttempt"] = ({key:value for key,value in failed_attempt.items() if key != "jpegFiles"} if failed_attempt else None)
        archive["uiValidation"] = dict(file=ui_paths[0].name,sha256=sha(ui_paths[0]),record=ui_validation,
                                       interactivePlaybackVerified=False)
        write_text(workflow/"README.md", "# Wider movement recording workflow\n\n"
                   "The frozen executor at 1,048,609 experiences replays the same 512 condition-A resets as the wider diagnostic. The selection rule chooses the first legal and unsuccessful return per direction when available. These clips illustrate behavior; their balance is not an estimate of success rate.\n\n"
                   "The capture stores actual 20 fps Unity JPEGs and body/ball poses, and verifies all 512 physical episode/goal/first-decision records against the diagnostic. Rendering changes only renderer visibility. No policy, simulation source or ledger changes occur.\n\n"
                   "Metadata, replay evidence and exact scripts are preserved alongside losslessly compressed pose recordings. Decompress each recording.json.gz to recover the original byte-identical recording.json. JPEGs and redundant data.js remain in the local output directory with hashes in local-viewer-files.json; this Git archive is not a standalone playable gallery.\n")
        rows=["# Wider movement recordings", "", f"The frozen executor at **1,048,609 experiences** replayed all **512 condition-A attempts** with matching physical episodes, goal/landing evidence and first observations/actions. The local viewer contains **{manifest['clipCount']} clips** selected systematically to show available successes and failures.", "",
              "| Direction | Legal returns / all directional A attempts | Selected illustrations |", "|---|---:|---|"]
        analysis=read(out/"evaluation-analysis.json")
        for direction in ("left","right","shallow","deep"):
            stats=analysis["summaries"]["axis/"+direction][manifest["modelName"]]["A"]
            chosen=[entry["categoryUnderA"] for entry in manifest["selected"] if entry["direction"] == direction]
            rows.append(f"| {direction.title()} | {stats['legal']} / {stats['attempts']} | {', '.join(chosen)} |")
        rows += ["", "Nominal feed displacement and measured player travel are different quantities. The camera detail follows the player; the full-court view makes repositioning easier to judge. A legal return and a target hit are separate outcomes.", "",
                 "The right-direction cohort has no successful A return, so no successful right clip is invented. Directional results include all 256 challenges; familiar drills make up the other 256 replayed attempts. No mastery or generalization is claimed.", "",
                 "[Recording evidence](execution-v1-evidence/wide-movement-review-01/archive-manifest.json) · [Original diagnostic](execution-v1-wide-movement.md)", "",
                 "The JPEG gallery remains local. The repository preserves replay evidence, compressed actual pose records, the viewer/capture workflow and image hashes without a large image commit.", "",
                 f"All {verified['images']} JPEGs passed image-decoding checks. Interactive browser playback remains unverified: the in-app browser's local-file URL policy blocked opening the gallery. The local UI-validation record preserves this limitation.", ""]
        if failed_attempt:
            rows += ["The first capture attempt completed its simulations but failed while reading an evidence file whose writer was still open. Its failure, raw evidence and JPEG hashes are preserved separately. Its unsaved pose records were lost; none were reconstructed. The successful retry uses the same selected cases with a terminal writer-lifecycle correction, recorded in its amendment.", ""]
        write_text(report_path,"\n".join(rows))
        archive["report"] = dict(path=REPORT,sha256=sha(report_path))
        write_json(evidence/"archive-manifest.json",archive)
        print(json.dumps(dict(evidence=str(evidence),workflow=str(workflow),report=str(report_path),poseRecordings=len(compressed),JPEGsKeptLocal=len(image_names),masteryAccepted=False),indent=2))
    except Exception:
        failure=evidence/"archive-failure.json"
        if not failure.exists(): write_json(failure,dict(status="partial_archive_preserved",error=traceback.format_exc(),writtenFiles=written))
        raise


if __name__ == "__main__":
    main()
