"""Verify actual condition-A replay frames and reuse the existing museum viewer."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from PIL import Image

WORKSPACE = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(same(x, y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):
        if type(a) is int and type(b) is int:
            return a == b
        return math.isfinite(a) and math.isfinite(b) and struct.unpack("<f", struct.pack("<f", a))[0] == struct.unpack("<f", struct.pack("<f", b))[0]
    return type(a) is type(b) and a == b


def rows(path):
    items = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    result = {row["seed"]:row for row in items}
    require(len(result) == len(items) == 512, f"Incomplete/duplicate replay evidence: {path}")
    require(sorted(result) == list(range(1109849,1110361)), "Wrong replay reset interval")
    return result


def write_new(path, text):
    with path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/dev/picklebot"))
    parser.add_argument("--output-name", default="wide-movement-review-01")
    args = parser.parse_args()
    root = args.root.resolve()
    output_root = (WORKSPACE/"outputs").resolve()
    out = (output_root/args.output_name).resolve()
    require(out.is_relative_to(output_root) and out != output_root, "Output must be an existing workspace recording")
    require(not (out/"error.json").exists() and not (out/"verification.json").exists(), "Failed/already-built recording")
    for name in ("index.html","museum.css","museum.js","data.js"):
        require(not (out/name).exists(), "Refusing to overwrite an existing viewer")
    manifest, complete, parity = (read(out/name) for name in ("manifest.json","complete.json","parity.json"))
    require(complete["status"] == "complete_verified_replay" and complete["condition"] == "A"
            and complete["episodes"] == complete["matchesReference"] == 512, "Incomplete verified capture")
    require(parity["status"] == "exact_float32_parity" and parity["mismatches"] == [], "Capture parity failed")
    require(complete["manifestHash"] == sha(out/"manifest.json") and sha(out/"capture.cs") == manifest["captureScriptSha256"], "Manifest/capture identity changed")
    require(manifest["checkpoint"] == 1048609 and manifest["fullReplayEpisodes"] == 512
            and manifest["goalRecipe"]["conditions"] == ["A"], "Unexpected recording model/conditions")
    source = read(out/"source-records.json")
    require(source["sourceIdentity"] == manifest["sourceIdentity"] == complete["sourceIdentity"], "Source identity mismatch")
    inputs = {str(out/name):sha(out/name) for name in ("manifest.json","complete.json","parity.json","capture.cs","source-records.json","evaluation-analysis.json")}
    for relative, expected in source["files"].items():
        path=(root/relative).resolve()
        require(path.is_relative_to(root) and sha(path) == expected, f"Source changed: {relative}")
    for relative, expected in manifest["referenceInputSha256"].items():
        path=(root/relative).resolve()
        require(path.is_relative_to(root) and sha(path) == expected, f"Audited reference changed: {relative}")
        inputs[str(path)] = expected
    for path, expected in ((root/manifest["model"],manifest["modelHash"]),
                           (root/manifest["checkpointPath"],manifest["checkpointHash"]),
                           (root/"artifacts/player-v3/seed-ledger.json",manifest["ledgerHash"])):
        require(sha(path) == expected, f"Model/checkpoint/ledger changed: {path}")
        inputs[str(path)] = expected
    require(read(root/"artifacts/player-v3/seed-ledger.json")["finalSeedsConsumed"] == [], "Final seed declaration changed")
    stage = manifest["stages"][0]
    reference = Path(stage["referenceDirectory"])
    replay = out/"evaluations/A"
    episodes, goals = rows(replay/"episodes.jsonl"), rows(replay/"execution-goals.jsonl")
    require(same(episodes,rows(reference/"episodes.jsonl")), "Physical episode parity failed")
    require(same(goals,rows(reference/"execution-goals.jsonl")), "Goal/landing parity failed")
    require(same(read(replay/"first-decisions.json"),read(reference/"first-decisions.json")), "First-observation/action parity failed")
    require(same(read(replay/"model-identity.json"),read(reference/"model-identity.json")), "Replay model identity mismatch")
    report = read(replay/"report.json")
    require(report["status"] == "seed_budget_complete" and report["completedEpisodes"] == 512
            and report["sourceIdentity"] == manifest["sourceIdentity"] and report["trainerConnected"] is False, "Unexpected replay report")
    for path in replay.iterdir():
        if path.is_file(): inputs[str(path)] = sha(path)
    analysis = read(out/"evaluation-analysis.json")
    require(sha(out/"evaluation-analysis.json") == manifest["analysisHash"], "Original completed analysis changed")
    images, clips = {}, []
    for selection in manifest["selected"]:
        seed = selection["seed"]
        ident = f"A-{seed}"
        directory=out/"clips"/ident
        recording=read(directory/"recording.json")
        inputs[str(directory/"recording.json")] = sha(directory/"recording.json")
        require(recording["matchesReference"] is True and recording["modelHash"] == manifest["modelHash"]
                and recording["sourceIdentity"] == manifest["sourceIdentity"] and recording["manifestHash"] == sha(out/"manifest.json"), "Clip identity/parity mismatch")
        require(same(recording["episode"],episodes[seed]) and same(recording["goal"],goals[seed]), "Clip outcome differs from actual full replay")
        frames=recording["frames"]
        require(len(frames) >= 2 and [frame["tick"] for frame in frames] == list(range(0,len(frames)*12,12)), "Nonuniform/missing frame sequence")
        for index, frame in enumerate(frames):
            require(frame["player"] == selection["player"] and len(frame["players"]) == 4 and len(frame["ball"]) == 3
                    and len(frame["observation124"]) == 124, "Missing actual player/ball pose")
            for player in frame["players"]:
                require(len(player["root"]) == 3 and len(player["paddleRotation"]) == 4 and len(player["parts"]) >= 14, "Incomplete articulated body pose")
            for view in (0,1):
                path=directory/f"frame-{index:04d}-{view}.jpg"
                with Image.open(path) as image:
                    require(image.size == (800,600), "Wrong frame resolution")
                    extrema=image.getextrema()
                    require(any(high-low > 20 for low,high in extrema), "Blank/flat capture frame")
                    image.verify()
                images[path.relative_to(out).as_posix()] = sha(path)
        episode=episodes[seed]
        path=episode["travelBeforeContact"][episode["player"]]
        displacement=f'{episode["contactDisplacement"]:.2f} m' if episode["faceContact"] else "no contact"
        outcome="Legal return" if episode["outcome"] == "legal_return" else "Unsuccessful return"
        target="target hit" if goals[seed]["targetHit"] else "target missed"
        title=f'{selection["direction"].title()} · {selection["nominalShiftCm"]} cm feed shift · P{episode["player"]+1} · {outcome} · {target}'
        clips.append(dict(id=ident,title=title,selection=selection,measuredRootPathMetres=path,contactDisplacementLabel=displacement,**recording))
    require(len(clips) == manifest["clipCount"] == complete["clips"] <= 8
            and len(images) == complete["images"] and sum(len(c["frames"]) for c in clips) == complete["frames"], "Capture frame/clip accounting mismatch")
    names={3:"left",5:"right",1:"shallow",7:"deep"}
    exhibits=[]
    for direction in ("left","right","shallow","deep"):
        selected=[episode for episode in episodes.values() if episode["movementRange"] > 0 and names[episode["movementRegion"]] == direction]
        legal=sum(e["outcome"] == "legal_return" for e in selected)
        target_count=sum(goals[e["seed"]]["targetHit"] for e in selected)
        summary=analysis["summaries"][f"axis/{direction}"][manifest["modelName"]]["A"]
        require(summary["attempts"] == len(selected) and summary["legal"] == legal and summary["targets"] == target_count, "Museum score diverges from original diagnostic")
        unavailable=[item["category"] for item in manifest["unavailable"] if item["direction"] == direction]
        clip_ids=[clip["id"] for clip in clips if clip["selection"]["direction"] == direction]
        require(clip_ids,"No example available for a direction")
        counts=[]
        for cm in (25,50,75,100):
            group=[e for e in selected if round(e["movementRange"]*400) == cm]
            counts.append(dict(label=f"{cm} cm nominal feed shift", attempts=len(group),legal=sum(e["outcome"] == "legal_return" for e in group),contacts=sum(e["faceContact"] for e in group)))
        missing_text=" No successful A return exists in this direction's full cohort; the available example is a failure." if "legal-return" in unavailable else " No failed A return exists in this direction's full cohort." if "unsuccessful-return" in unavailable else ""
        exhibits.append(dict(id=direction,title=f"{direction.title()} movement",subtitle="Actual policy · target A",stages=["A"],
                             description="The feed's nominal point shifts 25–100 cm from the initial paddle face in this direction. These centimetres describe the feed shift, not required footsteps. Target A is the left area across the net, relative to the player's attacking direction.",
                             success="A physical paddle contact followed by a legal return. A target hit is an additional placement result, counted separately.",
                             watch="Compare the whole-court position with the player detail. The detail camera follows the body; it can hide travel. Clips are the first available success and failure by seed, not typical frequencies."+missing_text,
                             status="Frozen development diagnostic",rows=counts,targets=target_count,clipIds=clip_ids,
                             context="Condition A only; all 512 replay outcomes/goals and first observations/actions match the recorded diagnostic. Solo drills; other players are inactive."))
    payload=dict(checkpoint=manifest["checkpoint"],modelHash=manifest["modelHash"],sourceIdentity=manifest["sourceIdentity"],
                 episodes=512,clips=clips,exhibits=exhibits)
    old=WORKSPACE/"outputs/drill-museum-01"
    original_html=(old/"index.html").read_text(encoding="utf-8")
    original_js=(old/"museum.js").read_text(encoding="utf-8")
    html=original_html.replace('href="#serve"','href="#left"').replace("FIELD NOTES / 01","WIDER MOVEMENT")
    html=html.replace("Recorded model · Before paired training","Recorded model · Wider movement diagnostic")
    html=html.replace("A tour of the current player.","Watch the wider returns.")
    html=html.replace("One model, from its first serve to a ball shared with a teammate. Watch its decisions, its successful shots, and the attempts that still need work.","The current model attempts left, right, shallow and deep feeds. Scores cover all 256 directional challenges; the full 512-attempt replay also checked familiar drills.")
    html=html.replace("Rally feed 01","Execution model · Target A").replace("Checkpoint 3,818,028","Checkpoint 1,048,609")
    html=html.replace("This collection ends at paired practice. Sustained 2v2 play and the final gameplay acceptance tests remain ahead.","Wider movement remains an open skill. These are frozen solo-policy recordings; paired teamwork and sustained 2v2 remain ahead.")
    html=html.replace('alt="Unity recording of the full court"','alt="Actual Unity recording of the wider movement drill"')
    js=original_js.replace("function clipName(c){const e=c.episode;","function clipName(c){if(c.title)return c.title;const e=c.episode;")
    js=js.replace("/ 07`","/ ${data.exhibits.length}`")
    js=js.replace("activate(location.hash.slice(1)||'serve',false)","activate(location.hash.slice(1)||'left',false)")
    js=js.replace("$('breakdown').replaceChildren();", "if(Number.isInteger(exhibit.targets))$('metrics').insertAdjacentHTML('beforeend',`<div class=\"metric\"><strong>${exhibit.targets} / ${total}</strong><span>Requested target hit</span></div>`);$('breakdown').replaceChildren();")
    js=js.replace("$('detail-label').textContent=clip.episode.cooperativePairs?'TEAMMATE DETAIL':'PLAYER DETAIL';draw();", "$('detail-label').textContent='PLAYER DETAIL';$('clip-result').textContent+=` · path ${clip.measuredRootPathMetres.toFixed(2)} m · contact displacement ${clip.contactDisplacementLabel}`;draw();")
    require(js != original_js and html != original_html and "/ 07`" not in js, "Museum adaptation failed")
    write_new(out/"data.js","window.DRILL_MUSEUM="+json.dumps(payload,separators=(",",":"),allow_nan=False)+";\n")
    css=(old/"museum.css").read_text(encoding="utf-8")
    css+='\n.score-strip{grid-template-columns:repeat(4,minmax(0,1fr))}.clip-picker{flex-wrap:wrap}.clip-picker #clip-result{flex-basis:100%;white-space:normal}@media(max-width:780px){.score-strip{grid-template-columns:repeat(2,minmax(0,1fr))}nav{grid-template-columns:repeat(4,minmax(115px,1fr))}}\n'
    write_new(out/"museum.css",css)
    write_new(out/"museum.js",js)
    write_new(out/"index.html",html)
    for path in (old/"index.html",old/"museum.js",old/"museum.css"):
        inputs[str(path)]=sha(path)
    require(all(sha(Path(path)) == digest for path,digest in inputs.items()), "Input changed while building museum")
    verification=dict(status="verified_policy_recordings",condition="A",checkpoint=manifest["checkpoint"],modelHash=manifest["modelHash"],
                      sourceIdentity=manifest["sourceIdentity"],episodes=512,referenceMatches=512,clips=len(clips),images=len(images),
                      imageHashes=images,inputSha256=inputs,builderSha256=sha(Path(__file__)),
                      viewerSha256={name:sha(out/name) for name in ("index.html","museum.css","museum.js","data.js")},
                      parityDefinition=parity["definition"],sampling=manifest["selectionRule"],unavailableCategories=manifest["unavailable"],
                      actualPosesRecorded=True,finalSeedsConsumed=False,masteryAccepted=False,
                      limitations="Clips are outcome-stratified illustrations, not a success-rate sample. The 20 fps frame poses are sampled from the 240 Hz simulation; terminal outcomes may occur between frames. Nominal feed shift and measured root travel are different quantities.")
    write_new(out/"verification.json",json.dumps(verification,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:value for key,value in verification.items() if key not in ("imageHashes","inputSha256","viewerSha256")},indent=2))
    print(out/"index.html")


if __name__ == "__main__":
    main()
