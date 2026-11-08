"""D-249 (panel round 108): freeze the pro-move table for ProMoveDrill (picklebot_mj/tasks/pro_move.py).

Source: artifacts/motion/pb-pilot/ppa_moves.json (208 single moves of the near player in one PPA singles match, feet on
the court homography; sha256 prefix b69b3398). Kept: duration >= 0.5 s and mean speed <= 2.9 m/s (the shorter / faster
moves are keypoint jumps) -> 167 moves. Court frame: dx across (the player's right +), dy toward the net (+).
Writes picklebot_mj/pro_moves_v1.json and prints its sha256 (pinned in pro_move.PRO_TABLE_SHA256).
Usage: python scripts/diag/freeze_pro_moves.py
"""
import hashlib
import json

SRC = "artifacts/motion/pb-pilot/ppa_moves.json"
SRC_SHA_PREFIX = "b69b3398"
OUT = "picklebot_mj/pro_moves_v1.json"
MIN_DUR_S, MAX_MEAN_MS = 0.5, 2.9

b = open(SRC, "rb").read()
assert hashlib.sha256(b).hexdigest().startswith(SRC_SHA_PREFIX), "source table changed"
rows = [m for m in json.loads(b) if m["dur"] >= MIN_DUR_S and m["mean"] <= MAX_MEAN_MS]
assert len(rows) == 167, len(rows)
keep = [{k: m[k] for k in ("clip", "t0", "dx", "dy", "dur", "dist")} for m in rows]
doc = {"source": SRC, "source_sha256_prefix": SRC_SHA_PREFIX, "filter": {"min_dur_s": MIN_DUR_S, "max_mean_ms": MAX_MEAN_MS},
       "frame": "court: dx across (player's right +), dy toward the net (+); metres, seconds", "moves": keep}
s = json.dumps(doc, indent=0, sort_keys=True) + "\n"
open(OUT, "w", newline="\n").write(s)
print(len(keep), hashlib.sha256(s.encode()).hexdigest())
