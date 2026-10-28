"""Evaluation interface guard and read metadata (audit 2026-10-28, docs/research/audit-2026-10-28-maintainability.md).

Evaluation tasks take the residual's range (lam_r), the leg residual (leg_r) and the teacher gain from PICKLEBOT_*
environment variables. A forgotten variable reads a checkpoint through the wrong action interface: the shapes match,
the strict load passes, and nothing records it. `guard` compares the evaluation config with the training run's own
params/env.yaml (next to the checkpoint) and stops on a mismatch; `meta` is what every result JSON records about the
read. Checkpoints in hand-made dirs without params/env.yaml (init and surgery copies) are read but marked unverified.
"""

from __future__ import annotations

import os
import re

KEYS = ("lam", "lam_r", "leg_r", "wrist_r")


def checkpoint_interface(checkpoint: str) -> dict | None:
    """The latent action term's interface as the training run saved it, or None without params/env.yaml."""
    p = os.path.join(os.path.dirname(os.path.abspath(checkpoint)), "params", "env.yaml")
    if not os.path.exists(p):
        return None
    text = open(p, encoding="utf-8", errors="replace").read()
    out = {}
    for k in KEYS:
        m = re.search(rf"^\s+{k}: ([-0-9.e]+)\s*$", text, re.M)
        if m:
            out[k] = float(m.group(1))
    out["teacher_obs"] = "teacher_contact_obs" in text
    return out


def cfg_interface(cfg) -> dict:
    lt = cfg.actions.get("latent")
    out = {k: float(getattr(lt, k)) for k in KEYS if lt is not None and getattr(lt, k, None) is not None}
    out["teacher_obs"] = any("teacher" in name for g in cfg.observations.values() for name in g.terms)
    return out


def guard(checkpoint: str, cfg) -> dict:
    """Stop if the evaluation config's action interface differs from the checkpoint's training run; return the read
    metadata for the result JSON."""
    ck, ev = checkpoint_interface(checkpoint), cfg_interface(cfg)
    if ck is None:
        print(f"interface guard: no params/env.yaml beside {checkpoint}; interface unverified")
    else:
        bad = {k: (ck[k], ev.get(k)) for k in ck if k in ev and ck[k] != ev[k]}
        if bad:
            raise SystemExit(f"interface guard: the evaluation config differs from the checkpoint's training run "
                             f"(checkpoint, evaluation): {bad}. Set the matching PICKLEBOT_* variables.")
    return {"interface_eval": ev, "interface_checkpoint": ck, "interface_verified": ck is not None,
            "env": {k: v for k, v in sorted(os.environ.items()) if k.startswith("PICKLEBOT_")}}
