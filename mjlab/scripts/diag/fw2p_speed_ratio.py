import json
import numpy as np
for t in ("h0", "lat07"):
    pc = json.load(open(f"/mnt/f/dev/picklebot-mjlab/mjlab/results/fw2p-{t}.json"))["per_clip"]
    for lo in (0.0, 1.0, 1.3):
        u = [x for x in pc if x["ref_pelvis_speed"] >= lo]
        r = np.array([x["pelvis_speed"] / x["ref_pelvis_speed"] for x in u])
        print(t, f"ref>={lo}", len(u), "robot", round(np.mean([x["pelvis_speed"] for x in u]), 3),
              "ref", round(np.mean([x["ref_pelvis_speed"] for x in u]), 3), "ratio p50", round(float(np.median(r)), 3),
              "mpkpe", round(np.mean([x["mpkpe"] for x in u]), 3), "r_mpkpe", round(np.mean([x["r_mpkpe"] for x in u]), 3))
for f in ("speed-ladder-h0", "speed-ladder-lat07"):
    try:
        d = json.load(open(f"/mnt/f/dev/picklebot-mjlab/mjlab/results/{f}.json"))
        print(f, "robot", round(d["pelvis_speed"], 3), "ref", round(d["ref_pelvis_speed"], 3))
    except FileNotFoundError:
        pass
