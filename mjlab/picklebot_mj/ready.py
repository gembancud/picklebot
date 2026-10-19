"""Ready position and split step at the feed launch (Stage 5F shot item 1, D-111 metric, D-115 run).

A coach's ready position: feet apart, both feet down, when the opponent hits. The split step: a small unweighting
dip timed to the opponent's contact, so the legs are loaded to move. Measured at each refeed (the feeder's "contact")
from the pelvis height and the two ankle positions, per physics step, without host syncs:
- ready:  stance width (ankle-to-ankle, horizontal) >= READY_WIDTH_M and both ankles below FOOT_DOWN_Z at the launch;
- dip:    (highest pelvis in [-W, 0]) - (lowest pelvis in [-W, +W]) >= DIP_M, W = WINDOW_S around the launch;
- both:   ready and dip (the D-111 shot-item metric).
Feeds within WINDOW_S of a robot reset (no pelvis history yet) are not scored.

Rewards (optional, one-shot): at the launch a soft ready score, both-down x clamp((width - 0.20) / 0.15, 0, 1); at the
window end a soft dip score, clamp(dip / DIP_M, 0, 1). Both read by `ready_reward` and cleared with the step events.
"""

from __future__ import annotations

import torch

WINDOW_S = 0.25
READY_WIDTH_M = 0.35
DIP_M = 0.03
FOOT_DOWN_Z = 0.12  # ankle-roll link height, as the kitchen rule's "foot down" (return_stand.py)


class ReadyTracker:
    def __init__(self, n: int, device, physics_dt: float, foot_ids: list[int]):
        self.h = int(round(WINDOW_S / physics_dt)) + 1  # pelvis history length (physics steps) covering WINDOW_S
        self.dt = physics_dt
        self.foot_ids = foot_ids
        z = lambda dtype=torch.float32: torch.zeros(n, dtype=dtype, device=device)  # noqa: E731
        self.z_hist = torch.zeros(self.h, n, device=device)
        self.age = z(torch.long)  # physics steps since the robot's reset
        self.open = z(torch.bool)  # a launch window still running
        self.t_open, self.z_top, self.z_min = z(), z(), z()
        self.ready_ok = z(torch.bool)
        self.launch_now, self.split_now = z(), z()  # one-shot reward scores
        self.stats = torch.zeros(4, dtype=torch.long, device=device)  # feeds scored, ready, dip, both

    def reset(self, env_ids: torch.Tensor) -> None:
        self.age[env_ids] = 0
        self.open[env_ids] = False

    def step(self, pelvis_z: torch.Tensor) -> None:
        """Every physics step, before the refeed: push the pelvis height and advance open windows."""
        self.z_hist = torch.cat([self.z_hist[1:], pelvis_z.unsqueeze(0)], 0)  # oldest first
        self.age += 1
        self.z_min = torch.where(self.open, torch.minimum(self.z_min, pelvis_z), self.z_min)
        self.t_open = torch.where(self.open, self.t_open + self.dt, self.t_open)
        done = self.open & (self.t_open >= WINDOW_S - 1e-6)
        dip = self.z_top - self.z_min
        self.split_now = torch.where(done, (dip / DIP_M).clamp(0.0, 1.0), self.split_now)
        dip_ok = done & (dip >= DIP_M)
        self.stats += torch.stack([done.sum(), (done & self.ready_ok).sum(), dip_ok.sum(),
                                   (dip_ok & self.ready_ok).sum()])
        self.open = self.open & ~done

    def launch(self, fire: torch.Tensor, feet_pos: torch.Tensor) -> None:
        """At a refeed (fire mask); feet_pos [n, 2, 3] court-local ankle positions."""
        valid = fire & (self.age >= self.h)
        width = (feet_pos[:, 0, :2] - feet_pos[:, 1, :2]).norm(dim=-1)
        down = (feet_pos[..., 2] < FOOT_DOWN_Z).all(-1)
        self.ready_ok = torch.where(valid, down & (width >= READY_WIDTH_M), self.ready_ok)
        score = down.float() * ((width - 0.20) / 0.15).clamp(0.0, 1.0)
        self.launch_now = torch.where(valid, score, self.launch_now)
        self.z_top = torch.where(valid, self.z_hist.max(0).values, self.z_top)
        self.z_min = torch.where(valid, self.z_hist.min(0).values, self.z_min)
        self.t_open = torch.where(valid, torch.zeros_like(self.t_open), self.t_open)
        self.open = self.open | valid

    def consume(self) -> None:
        self.launch_now.zero_()
        self.split_now.zero_()

    def summary(self) -> dict:
        n, r, d, b = (int(x) for x in self.stats.tolist())
        share = lambda k: round(k / n, 4) if n else None  # noqa: E731
        return {"feeds_scored": n, "ready": share(r), "dip": share(d), "ready_and_dip": share(b),
                "definition": f"width >= {READY_WIDTH_M} m and both ankles < {FOOT_DOWN_Z} m at the launch; "
                              f"pelvis dip >= {DIP_M} m within +-{WINDOW_S} s"}
