"""Print selected per-iteration training-log terms at a few iterations (rsl_rl console log).

Usage: python scripts/train_curve.py LOG [--every 200] [--terms legal_return,paddle_contact,...]
"""
import argparse
import re

ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("--every", type=int, default=200)
ap.add_argument("--terms", default="Episode_Reward/legal_return,Episode_Reward/paddle_contact,"
                "Episode_Reward/approach_ball,Episode_Termination/fell_over,Mean episode length,Mean action std")
a = ap.parse_args()
terms = a.terms.split(",")
rows, cur = [], None
for line in open(a.log, encoding="utf-8", errors="ignore"):
    m = re.search(r"Learning iteration (\d+)/", line)
    if m:
        cur = {"it": int(m.group(1))}
        rows.append(cur)
        continue
    if cur is not None and ":" in line:
        k, _, v = line.strip().rpartition(":")
        try:
            cur[k.strip()] = float(v.strip().split()[0])
        except (ValueError, IndexError):
            pass
short = [t.split("/")[-1][:14] for t in terms]
print("it     " + " ".join(f"{s:>14s}" for s in short))
for r in rows:
    if r["it"] % a.every == 0 or r is rows[-1]:
        print(f"{r['it']:<6d} " + " ".join(f"{r.get(t, float('nan')):14.4f}" for t in terms))
