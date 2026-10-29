"""Falls per env-second from rsl_rl training logs, independent of episode length (D-170).

mjlab logs Episode_Termination/<term> as the count of envs ending by <term> in a step, and rsl_rl averages it only
over steps with at least one reset (steps without resets log an empty dict). The logged value is therefore
E[count | count >= 1], which grows when resets get rarer (longer episodes). With resets per step ~ Poisson(lam),
the logged sum S of all terms is lam / (1 - exp(-lam)); solve for lam, then falls per step = fell * lam / S.
"""
import math, re, sys

DT, ENVS = 0.02, 1024


def lam_from_sum(s):
    lo, hi = 1e-9, 50.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid / (1 - math.exp(-mid)) < s:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def falls_per_1000_env_s(path, envs=ENVS):
    t = open(path, errors="ignore").read()
    terms = {}
    for k, v in re.findall(r"Episode_Termination/(\w+): ([0-9.]+)", t):
        terms.setdefault(k, []).append(float(v))
    m = {k: sum(v) / len(v) for k, v in terms.items()}
    s = sum(m.values())
    lam = lam_from_sum(s) if s > 1 else 0.0
    per_step = m.get("fell_over", 0.0) * lam / s if s > 0 else 0.0
    return 1000 * per_step / (envs * DT), m.get("fell_over", 0.0), s


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r, fell, s = falls_per_1000_env_s(p)
        print(f"{p:36s} logged fell_over {fell:.3f} (sum of terms {s:.3f}) -> falls per 1,000 env-seconds {r:.3f}")
