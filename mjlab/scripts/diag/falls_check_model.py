# Cross-check for falls_by_length.py: implied time-out fraction per episode (time_out rate x episode steps / envs) must be <= 1.
import re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import lam_from_sum
for p, steps in [(a.split(":")[0], int(a.split(":")[1])) for a in sys.argv[1:]]:
    t = open(p, errors="ignore").read()
    m = {}
    for k, v in re.findall(r"Episode_Termination/(\w+): ([0-9.]+)", t):
        m.setdefault(k, []).append(float(v))
    m = {k: sum(v) / len(v) for k, v in m.items()}
    s = sum(m.values()); lam = lam_from_sum(s)
    to = m["time_out"] * lam / s; fo = m["fell_over"] * lam / s
    print(f"{p:30s} episodes ending per step {lam:.3f}; time-out share {to/lam:.3f}; implied episodes per env per {steps} steps {lam*steps/1024:.3f}")
