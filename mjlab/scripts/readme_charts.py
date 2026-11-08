"""README charts (2026-11-09): rally progress (P(5+) by milestone, two read protocols) and the pro footwork moves.

Usage: python scripts/readme_charts.py   (writes ../docs/media/rally-progress.png and ../docs/media/pro-moves.png)
Numbers are copied from the decision log (D-132 .. D-243) and results/*-summary.txt; the pro moves from
picklebot_mj/pro_moves_v1.json. Palette: the dataviz reference instance (slots 1-2, light surface).
"""
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURF, "axes.facecolor": SURF})

# --- rally progress -------------------------------------------------------------------------------------------------
labels = ["Self-play\nstart", "Run 2", "Run 10", "Run 14", "Run 18b", "Run 19", "Run 22b", "C", "M", "N", "P", "Q"]
open_read = [0.3, 7.9, 13.3, 18.7, 25.8, 33.2, 39.0, 40.6, None, None, None, 36.5]
set_read = [None] * 7 + [56.5, 74.5, 76.6, 78.2, 77.6]
x = list(range(len(labels)))
fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
ax.axhline(80, color=INK2, lw=1, ls=(0, (4, 3)))
ax.text(len(labels) - 0.6, 81.5, "target 80 %", ha="right", va="bottom", color=INK2, fontsize=10)
xo = [i for i, v in enumerate(open_read) if v is not None]
ax.plot(xo, [open_read[i] for i in xo], color=ORANGE, lw=2, marker="o", ms=6, mec=SURF, mew=1.5,
        label="Open read: rallies start wherever the robots ended")
xs = [i for i, v in enumerate(set_read) if v is not None]
ax.plot(xs, [set_read[i] for i in xs], color=BLUE, lw=2, marker="o", ms=6, mec=SURF, mew=1.5,
        label="Set-start read: both robots start set on their ready spot (D-229)")
ax.annotate("77.6 %", (11, 77.6), xytext=(6, -14), textcoords="offset points", color=INK, fontsize=10)
ax.annotate("36.5 %", (11, 36.5), xytext=(6, -4), textcoords="offset points", color=INK, fontsize=10)
ax.set_xticks(x, labels, fontsize=9)
ax.set_ylim(0, 90)
ax.set_ylabel("Rallies reaching 5 good shots (%)")
ax.yaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("Two-robot rallies, 21 October to 8 November 2026", loc="left", fontsize=12, color=INK)
fig.tight_layout()
fig.savefig("../docs/media/rally-progress.png")

# --- pro moves -------------------------------------------------------------------------------------------------------
moves = json.load(open("picklebot_mj/pro_moves_v1.json"))["moves"]
fig, ax = plt.subplots(figsize=(5.6, 5.6), dpi=150)
for m in moves:
    ax.annotate("", xy=(m["dx"], m["dy"]), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.0, alpha=0.55, mutation_scale=8, shrinkA=0, shrinkB=0))
for r in (1, 2, 3, 4, 5):
    ax.add_patch(plt.Circle((0, 0), r, fill=False, color=GRID, lw=0.8))
    ax.text(r * math.cos(math.radians(60)), r * math.sin(math.radians(60)), f"{r} m", color=MUTED, fontsize=8)
ax.text(0, 6.4, "toward the net", ha="center", color=INK2, fontsize=9)
ax.text(0, -6.6, "back", ha="center", color=INK2, fontsize=9)
ax.text(-6.4, 0, "left", ha="center", va="center", rotation=90, color=INK2, fontsize=9)
ax.text(6.4, 0, "right", ha="center", va="center", rotation=270, color=INK2, fontsize=9)
ax.set_xlim(-6.8, 6.8)
ax.set_ylim(-6.8, 6.8)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title(f"{len(moves)} footwork moves of a pro, one singles match", loc="left", fontsize=12, color=INK)
fig.tight_layout()
fig.savefig("../docs/media/pro-moves.png")
print("ok")
