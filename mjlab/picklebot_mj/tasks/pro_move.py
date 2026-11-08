"""D-249 (panel round 108, 5 of 5): the pro-move drill. New file: move_drill.py is unchanged; ProMoveDrill is swapped in by
BallPhysicsAction (return_stand.py) when its cfg sets move_pro_moves.

ProMoveDrill (a MoveDrill) differs only in where a new spot comes from: the robot's pelvis plus one pro displacement drawn
uniformly (on the drill's own stream) from the frozen table picklebot_mj/pro_moves_v1.json (167 single moves of the near
player in one PPA singles match; scripts/diag/freeze_pro_moves.py; sha256 pinned below). Court frame -> robot frame:
toward the net (dy) is +x, the player's left (-dx) is +y, so robot (dx, dy) = (dy, -dx). Distances are not scaled.
MoveDrill's box rule is kept: reverse when even DIST_RANGE[0] leaves SPOT_BOX, then shrink to the room left (counted as
flipped / clipped). The sector is the issued direction's MoveDrill sector (0 toward the net, CCW). Arrival, the arrival
bonus, the untimed limit (1.5 s + 1.25 s/m of the issued distance) and the command are MoveDrill's.
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import torch

from picklebot_mj.tasks import move_drill as md

PRO_TABLE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pro_moves_v1.json")
PRO_TABLE_SHA256 = "3a0680ab20bcafe38e3bb859c3b3c718c633728bd64dc05e43eece1006c239ee"
PRO_CLASSES = ("forward", "left", "back", "right")  # issued direction, robot frame, 90-degree classes


def load_table(path: str = PRO_TABLE) -> list:
    b = open(path, "rb").read()
    assert hashlib.sha256(b).hexdigest() == PRO_TABLE_SHA256, "pro-move table changed"
    return json.loads(b)["moves"]


def robot_disp(moves: list) -> torch.Tensor:
    """Court (dx across, player's right +; dy toward the net +) -> robot frame (+x toward the net, +y the left)."""
    return torch.tensor([[m["dy"], -m["dx"]] for m in moves], dtype=torch.float32)


def pro_class(u: torch.Tensor) -> torch.Tensor:
    """0 forward, 1 left, 2 back, 3 right (45-degree boundaries, as pb_moves.py classes the pro's moves)."""
    a = torch.atan2(u[..., 1], u[..., 0])
    return torch.floor((a + math.pi / 4) / (math.pi / 2)).long() % 4


def sector(u: torch.Tensor) -> torch.Tensor:
    a = torch.atan2(u[..., 1], u[..., 0])
    return torch.floor((a + math.pi / md.N_SECTORS) / (2 * math.pi / md.N_SECTORS)).long() % md.N_SECTORS


class ProMoveDrill(md.MoveDrill):
    def __init__(self, term, move_prob: float, seed: int, sector_weights=None, path: str = PRO_TABLE):
        assert sector_weights is None, "the pro-move drill draws directions from the table"
        super().__init__(term, move_prob, seed)
        self.disp = robot_disp(load_table(path)).to(self.dev)
        z = lambda *s: torch.zeros(*s, dtype=torch.long, device=self.dev)  # noqa: E731
        self.stats["flipped"], self.stats["clipped"] = z(md.N_SECTORS), z(md.N_SECTORS)
        self.stats["pro_class"] = z(len(PRO_CLASSES))

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Issue a spot = pelvis + a drawn pro displacement (MoveDrill's flip / shrink in SPOT_BOX) for envs in mask."""
        t = self.t
        here = t.pelvis_xy()
        k = torch.randint(len(self.disp), (self.n,), generator=self.gen, device=self.dev)
        v = self.disp[k]
        dist = v.norm(dim=-1)
        u = v / dist.unsqueeze(-1).clamp(min=1e-6)
        flip = self._room(here, u) < md.DIST_RANGE[0]
        u = torch.where(flip.unsqueeze(-1), -u, u)
        room = self._room(here, u)
        clip = room < dist
        dist = torch.minimum(dist, room).clamp(min=0.0)
        spot = (here + dist.unsqueeze(-1) * u).clamp(self._lo, self._hi)
        sec = sector(u)
        m = mask.unsqueeze(-1)
        t.recover_xy = torch.where(m, spot, t.recover_xy)
        self.start_xy = torch.where(m, here, self.start_xy)
        self.sector = torch.where(mask, sec, self.sector)
        d0 = (spot - here).norm(dim=-1)
        self.limit = torch.where(mask, md.TIME_BASE_S + md.TIME_PER_M * d0, self.limit)
        self.elapsed = torch.where(mask, torch.zeros_like(self.elapsed), self.elapsed)
        self.hold = torch.where(mask, torch.zeros_like(self.hold), self.hold)
        self.stats["issued"].index_add_(0, self.sector, mask.long())
        self.stats["flipped"].index_add_(0, sec, (mask & flip).long())
        self.stats["clipped"].index_add_(0, sec, (mask & clip).long())
        self.stats["pro_class"].index_add_(0, pro_class(u), mask.long())
