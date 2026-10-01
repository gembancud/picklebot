"""Regulation pickleball court, net and line geometry as a MuJoCo spec.

Frame: x runs along the court length with the net plane at x = 0 (near side
x < 0), y runs across the court (centre line y = 0), z is up. Units are metres.
Dimensions match the Unity reference (CourtGeometryV0/V1).
"""

from __future__ import annotations

import math

import mujoco

# Court dimensions (Unity CourtGeometryV0 / V1).
COURT_LENGTH = 13.4112  # 44 ft
COURT_WIDTH = 6.0960  # 20 ft
HALF_LENGTH = COURT_LENGTH / 2
HALF_WIDTH = COURT_WIDTH / 2
KITCHEN_DEPTH = 2.1336  # non-volley zone, 7 ft from the net
NET_SIDELINE_HEIGHT = 0.9144  # 36 in
NET_CENTER_HEIGHT = 0.8636  # 34 in
NET_POST_SPAN = 6.7056  # 22 ft
HALF_NET_POST_SPAN = NET_POST_SPAN / 2
LINE_WIDTH = 0.0508  # 2 in; lines are part of the area they bound

NET_THICKNESS = 0.02
NET_POST_RADIUS = 0.03
RUNOFF = 4.0  # floor margin around the court

# Geom groups: 0 = physical court, 3 = visual-only markings.
PHYSICAL_GROUP = 0
MARKING_GROUP = 3

# The net's top edge rises linearly from the centre to the sidelines.
_NET_SLOPE = (NET_SIDELINE_HEIGHT - NET_CENTER_HEIGHT) / HALF_WIDTH


def net_height_at(y: float) -> float:
    """Height of the net's top edge at lateral position y (0 beyond the posts)."""
    ay = abs(y)
    if ay > HALF_NET_POST_SPAN:
        return 0.0
    return NET_CENTER_HEIGHT + _NET_SLOPE * ay


def _net_half(side: int) -> dict:
    """Box geom for one net half; side = +1 (y > 0) or -1 (y < 0).

    The box is tilted about x so its top edge follows net_height_at. Each half
    starts 5 cm past the centre so the halves overlap and leave no gap.
    """
    overlap = 0.05
    theta = math.atan(_NET_SLOPE)
    c, s = math.cos(theta), math.sin(theta)
    span = HALF_NET_POST_SPAN + overlap
    half_len = span / (2 * c)
    half_h = 0.5 * NET_SIDELINE_HEIGHT
    # Top-inner corner sits at (y = -overlap, z = net_height_at(-overlap)) for side +1.
    z_inner = NET_CENTER_HEIGHT - _NET_SLOPE * overlap
    cy = -overlap + half_len * c + half_h * s
    cz = z_inner + half_len * s - half_h * c
    angle = theta * side
    return dict(
        name=f"net_{'pos' if side > 0 else 'neg'}",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[NET_THICKNESS / 2, half_len, half_h],
        pos=[0.0, side * cy, cz],
        quat=[math.cos(angle / 2), math.sin(angle / 2), 0.0, 0.0],
        rgba=[0.1, 0.1, 0.1, 0.6],
        group=PHYSICAL_GROUP,
    )


def _line(name: str, x0: float, x1: float, y0: float, y1: float) -> dict:
    return dict(
        name=name,
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[(x1 - x0) / 2, (y1 - y0) / 2, 0.0005],
        pos=[(x0 + x1) / 2, (y0 + y1) / 2, 0.0005],
        rgba=[1.0, 1.0, 1.0, 1.0],
        contype=0,
        conaffinity=0,
        group=MARKING_GROUP,
    )


def line_geoms() -> list[dict]:
    """Visual court markings. Line positions follow their outer edges, so lines
    lie inside the area they bound."""
    w, hl, hw = LINE_WIDTH, HALF_LENGTH, HALF_WIDTH
    lines = [
        _line("baseline_near", -hl, -hl + w, -hw, hw),
        _line("baseline_far", hl - w, hl, -hw, hw),
        _line("sideline_pos", -hl, hl, hw - w, hw),
        _line("sideline_neg", -hl, hl, -hw, -hw + w),
        _line("kitchen_near", -KITCHEN_DEPTH, -KITCHEN_DEPTH + w, -hw, hw),
        _line("kitchen_far", KITCHEN_DEPTH - w, KITCHEN_DEPTH, -hw, hw),
        _line("centerline_near", -hl, -KITCHEN_DEPTH, -w / 2, w / 2),
        _line("centerline_far", KITCHEN_DEPTH, hl, -w / 2, w / 2),
    ]
    return lines


def build_court_spec() -> mujoco.MjSpec:
    """Floor, court surface markings, net and posts in a standalone spec."""
    spec = mujoco.MjSpec()
    spec.modelname = "pickleball_court"
    wb = spec.worldbody
    wb.add_geom(
        name="floor",
        type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[HALF_LENGTH + RUNOFF, HALF_WIDTH + RUNOFF, 0.1],
        rgba=[0.25, 0.45, 0.35, 1.0],
        group=PHYSICAL_GROUP,
    )
    for g in line_geoms():
        wb.add_geom(**g)
    for side in (1, -1):
        wb.add_geom(**_net_half(side))
        wb.add_geom(
            name=f"net_post_{'pos' if side > 0 else 'neg'}",
            type=mujoco.mjtGeom.mjGEOM_CYLINDER,
            size=[NET_POST_RADIUS, NET_SIDELINE_HEIGHT / 2, 0.0],
            pos=[0.0, side * (HALF_NET_POST_SPAN + NET_POST_RADIUS), NET_SIDELINE_HEIGHT / 2],
            rgba=[0.3, 0.3, 0.3, 1.0],
            group=PHYSICAL_GROUP,
        )
    return spec
