"""Body-speed test summary and pre-registered rule (scripts/diag/bodyspeed54.sh; counters from tasks/body_speed.py).

Per MoveDrill sector (0 forward / toward the net, 2 left, 4 back, 6 right; odd sectors diagonal): sustained speed =
p50 over finished spots of each spot's best 1-s mean pelvis speed toward the spot; untimed arrival = arrived / (arrived
+ timed out + fell); censored share = censored / (finished + fell + censored), all sectors pooled.
Rule:
  VOID if forward sustained < 1.8 m/s (positive control) OR censored share > 10 % OR an override is missing;
  BODY-OK if back, left and right >= 1.8 m/s AND untimed arrival >= 90 % in every sector AND falls <= 4.157 / 1,000 env-s;
  BODY-LIMIT if back < 1.3 AND (left < 1.3 OR right < 1.3) m/s;
  else MIXED.
"""

from __future__ import annotations

from picklebot_mj.ballidx_rule import quantile

N_SECTORS = 8
SECTOR_NAMES = ("forward", "forward-left", "left", "back-left", "back", "back-right", "right", "forward-right")
CARDINAL = {"forward": 0, "left": 2, "back": 4, "right": 6}
SPEED_BIN = 0.1
OK_SPEED, LIMIT_SPEED, ARRIVAL_MIN, CENSOR_MAX, FALLS_MAX = 1.8, 1.3, 0.90, 0.10, 4.157


def sectors(c: dict) -> list[dict]:
    out = []
    for i in range(N_SECTORS):
        arr, to, fell, cen = c["arrived"][i], c["timed_out"][i], c["fell"][i], c["censored"][i]
        fin = arr + to + fell
        out.append({"sector": i, "name": SECTOR_NAMES[i], "spots": fin + cen, "arrived": arr, "timed_out": to,
                    "fell": fell, "censored": cen, "booked": c["booked"][i],
                    "sustained_p50": quantile(c["best_hist"][i], 0.5, SPEED_BIN),
                    "sustained_p90": quantile(c["best_hist"][i], 0.9, SPEED_BIN),
                    "peak_p50": quantile(c["peak_hist"][i], 0.5, SPEED_BIN),
                    "arrival": round(arr / fin, 4) if fin else None})
    return out


def censored_share(c: dict) -> float | None:
    cen = sum(c["censored"])
    tot = sum(c["arrived"]) + sum(c["timed_out"]) + sum(c["fell"]) + cen
    return cen / tot if tot else None


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def route(c: dict, falls: float | None, missing: list) -> dict:
    s = sectors(c)
    sp = {k: s[i]["sustained_p50"] for k, i in CARDINAL.items()}
    cs = censored_share(c)
    lines = []

    def line(text, ok):
        lines.append(f"{text} -> {'PASS' if ok else 'FAIL'}")
        return ok

    ge = lambda x, t: x is not None and x >= t - 1e-12  # noqa: E731
    lt = lambda x, t: x is not None and x < t  # noqa: E731
    v1 = line(f"VOID (a) forward sustained {_f(sp['forward'])} m/s < {OK_SPEED} (positive control fails)", lt(sp["forward"], OK_SPEED) or sp["forward"] is None)
    v2 = line(f"VOID (b) censored share {_f(cs)} > {CENSOR_MAX}", cs is None or cs > CENSOR_MAX)
    v3 = line(f"VOID (c) overrides missing from params/env.yaml: {missing}", bool(missing))
    ok_b = line(f"BODY-OK (a) back sustained {_f(sp['back'])} m/s >= {OK_SPEED}", ge(sp["back"], OK_SPEED))
    ok_l = line(f"BODY-OK (b) left sustained {_f(sp['left'])} m/s >= {OK_SPEED}", ge(sp["left"], OK_SPEED))
    ok_r = line(f"BODY-OK (c) right sustained {_f(sp['right'])} m/s >= {OK_SPEED}", ge(sp["right"], OK_SPEED))
    arr = [x["arrival"] for x in s]
    ok_a = line(f"BODY-OK (d) untimed arrival min over sectors {_f(min([a for a in arr if a is not None], default=None))} >= "
                f"{ARRIVAL_MIN}", all(ge(a, ARRIVAL_MIN) for a in arr))
    ok_f = line(f"BODY-OK (e) falls {_f(falls)} per 1,000 env-s <= {FALLS_MAX}", falls is not None and falls <= FALLS_MAX)
    lim_b = line(f"BODY-LIMIT (a) back sustained {_f(sp['back'])} m/s < {LIMIT_SPEED}", lt(sp["back"], LIMIT_SPEED))
    lim_s = line(f"BODY-LIMIT (b) left {_f(sp['left'])} or right {_f(sp['right'])} m/s < {LIMIT_SPEED}",
                 lt(sp["left"], LIMIT_SPEED) or lt(sp["right"], LIMIT_SPEED))
    if v1 or v2 or v3:
        verdict = "VOID"
    elif ok_b and ok_l and ok_r and ok_a and ok_f:
        verdict = "BODY-OK"
    elif lim_b and lim_s:
        verdict = "BODY-LIMIT"
    else:
        verdict = "MIXED"
    return {"sectors": s, "censored_share": cs, "falls": falls, "lines": lines, "verdict": verdict}
