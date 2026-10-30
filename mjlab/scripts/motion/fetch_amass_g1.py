"""Fetch a footwork subset of the G1-retargeted AMASS set (user-approved download, 2026-10-30).

Source: huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics, pinned to commit SHA below (public, not gated).
Each .npy is [T, 36]: root xyz, root quat xyzw, 29 G1 joints (README). Derived from AMASS: AMASS's non-commercial
research licence and each sub-dataset's terms apply (g1/license.txt, g1/amass.bib are fetched with the data).
Files land in OUT (a new directory used only for this data); nothing in it is executed. Usage:
  python -I scripts/motion/fetch_amass_g1.py --list LIST.json --out artifacts/motion/amass-g1-raw [--dry-run]
LIST.json is the HF API dump (/api/datasets/<repo>?blobs=true). A manifest with sha256 per file is written to OUT.
"""
import argparse, hashlib, json, os, re, sys, urllib.parse, urllib.request

REPO = "fleaven/Retargeted_AMASS_for_robotics"
SHA = "275c4c4a028cadf5241c10a613c2f11913531ad2"
META = ["g1/README.md", "g1/license.txt", "g1/amass.bib"]
WHOLE = ("g1/ACCAD/", "g1/Transitions_mocap/", "g1/SFU/")
PICK = {  # sub-dataset prefix -> clip-name pattern (fast / lateral / backward / turning footwork)
    "g1/KIT/": re.compile(r"backward|turn", re.I),
    "g1/Eyes_Japan_Dataset/": re.compile(r"dodge|backward|shuffle", re.I),
}
MAX_BYTES = 400e6


def select(siblings):
    out = []
    for s in siblings:
        p = s["rfilename"]
        if p in META:
            out.append(s); continue
        if not p.endswith(".npy"):
            continue
        if p.startswith(WHOLE):
            out.append(s); continue
        for pre, pat in PICK.items():
            if p.startswith(pre) and pat.search(p.rsplit("/", 1)[-1]):
                out.append(s); break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    info = json.load(open(a.list))
    assert info["sha"] == SHA and not info.get("gated"), (info.get("sha"), info.get("gated"))
    sel = select(info["siblings"])
    total = sum(s.get("size", 0) for s in sel)
    print(f"{len(sel)} files, {total / 1e6:.1f} MB")
    assert total < MAX_BYTES, total
    if a.dry_run:
        return
    os.makedirs(a.out, exist_ok=True)
    man = {"repo": REPO, "sha": SHA, "files": {}}
    for i, s in enumerate(sel):
        p = s["rfilename"]
        dst = os.path.join(a.out, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not (os.path.exists(dst) and os.path.getsize(dst) == s.get("size")):
            url = f"https://huggingface.co/datasets/{REPO}/resolve/{SHA}/{urllib.parse.quote(p)}"
            with urllib.request.urlopen(url, timeout=120) as r, open(dst + ".part", "wb") as f:
                f.write(r.read())
            os.replace(dst + ".part", dst)
        b = open(dst, "rb").read()
        assert len(b) == s.get("size"), (p, len(b), s.get("size"))
        man["files"][p] = {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()}
        if i % 50 == 0:
            print(i, p, flush=True)
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print("done", len(man["files"]))


if __name__ == "__main__":
    sys.exit(main())
