"""Unitree G1 (mjlab asset) with a rigid pickleball paddle fixed in the right hand (D-038).

The paddle body is a child of `right_wrist_yaw_link`, in a handshake grip. The
handle is centred on the `right_palm` site (x = 0.08 m along the hand) and the
face extends further along the hand's +x axis. The face is parallel to the palm,
so its normal is the wrist frame's +y axis.

The paddle body origin is the face centre. Its local axes follow
`ball_sim.PaddleState`: x = face width, y = length (toward the tip), z = face normal.
So `xpos`/`xmat` of the `paddle` body are exactly the PaddleState pose.

Geoms are visual only: ball contact is analytic (D-039), and paddle-vs-body or
paddle-vs-floor collisions are not modelled yet.
"""

from __future__ import annotations

import copy
import functools
import math
from dataclasses import dataclass

import mujoco
import numpy as np

from mjlab.asset_zoo.robots.unitree_g1 import g1_constants as g1
from mjlab.entity import EntityCfg

from picklebot_mj.ball_sim import PADDLE_CORNER_RADIUS, PADDLE_HALF

PADDLE_MASS = 0.22  # kg; typical composite paddle (USA Pickleball has no mass limit)
HANDLE_LENGTH = 0.127  # Unity CourtGeometryV1.PaddleHandleLength
HANDLE_RADIUS = 0.016
PALM_X = 0.08  # right_palm site in right_wrist_yaw_link
WRIST_BODY = "right_wrist_yaw_link"
PADDLE_BODY = "paddle"


@dataclass(frozen=True)
class GripCfg:
    """Where the paddle sits in the hand (right_wrist_yaw_link frame).

    The hand axis is wrist +x, the palm faces wrist +y and the thumb side is wrist +z.
    The handle axis is tilted by `tilt_deg` from the hand axis toward the thumb, within
    the palm plane. `handle_centre` is the handle midpoint; the face starts at the
    handle's outer end. The face normal is the palm normal (wrist +y).
    """

    name: str
    tilt_deg: float
    handle_centre: tuple[float, float, float]
    closed_hand: bool = False  # visual only: hide the open-hand mesh, draw fingers wrapped on the handle


# v1: Stage 2 mount (handle centred on the palm site, in line with the hand). Close-ups showed
# the face starting ~4 cm inside the fingers and the paddle in line with the forearm.
GRIP_V1 = GripCfg("v1-inline", 0.0, (PALM_X, 0.0, 0.0))
FACE_CENTRE_X = PALM_X + HANDLE_LENGTH / 2 + PADDLE_HALF[1]  # v1 face centre along the hand axis
# v2: handshake grip. The handle crosses the palm 35 deg toward the thumb, held in the finger curl
# (+y) and slid out so the face clears every hand-mesh vertex by >= 3 mm
# (scripts/fit_grip.py, 2026-10-02).
GRIP_V2 = GripCfg("v2-handshake", 35.0, (0.1084, 0.025, 0.0129), closed_hand=True)
DEFAULT_GRIP = GRIP_V2  # switched at the Stage 4 grip step (2026-10-02)


def _axes(grip: GripCfg):
    t = math.radians(grip.tilt_deg)
    length = np.array([math.cos(t), 0.0, math.sin(t)])  # handle/paddle long axis
    normal = np.array([0.0, 1.0, 0.0])  # palm normal
    width = np.cross(length, normal)
    return width, length, normal


def paddle_pose_in_wrist(grip: GripCfg):
    """(face-centre position, quaternion) of the paddle body in the wrist frame."""
    width, length, normal = _axes(grip)
    centre = np.array(grip.handle_centre) + length * (HANDLE_LENGTH / 2 + PADDLE_HALF[1])
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, np.stack([width, length, normal], axis=1).flatten())
    return centre, quat


HAND_RGBA = [0.13, 0.13, 0.13, 1.0]
HIDDEN_GROUP = 5  # not drawn by the default viewers/renderers (groups 0-3)
EDGE_GUARD = 0.008  # visible edge-guard band width
FACE_RGBA = [0.08, 0.28, 0.75, 1.0]
GUARD_RGBA = [0.06, 0.06, 0.07, 1.0]
GRIP_RGBA = [0.9, 0.9, 0.88, 1.0]
CAP_RGBA = [0.08, 0.08, 0.09, 1.0]


def _rounded_rect(body, prefix, half_w, half_l, half_t, r, rgba, y0=0.0):
    """Visual rounded rectangle in the body x-y plane (thickness along z) from boxes and cylinders."""
    kw = dict(contype=0, conaffinity=0, group=2, mass=0, rgba=rgba)
    body.add_geom(name=f"{prefix}_mid", type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0, y0, 0],
                  size=[half_w - r, half_l, half_t], **kw)
    for sx in (-1, 1):
        body.add_geom(name=f"{prefix}_side{'p' if sx > 0 else 'n'}", type=mujoco.mjtGeom.mjGEOM_BOX,
                      pos=[sx * (half_w - r / 2), y0, 0], size=[r / 2, half_l - r, half_t], **kw)
        for sy in (-1, 1):
            body.add_geom(name=f"{prefix}_corner{'p' if sx > 0 else 'n'}{'p' if sy > 0 else 'n'}",
                          type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r, half_t, 0],
                          pos=[sx * (half_w - r), y0 + sy * (half_l - r), 0], **kw)


def add_paddle_visual(paddle) -> None:
    """Standard-shape paddle look (16 x 8 in overall, 5 in handle): rounded face, edge guard,
    throat, wrapped grip with overgrip bands and a butt cap. Visual only.

    Tasks set BallParams.paddle_corner_radius = PADDLE_CORNER_RADIUS so the analytic
    ball contact uses this same rounded face.
    """
    hw, hl, ht = PADDLE_HALF
    r = PADDLE_CORNER_RADIUS
    _rounded_rect(paddle, "guard", hw, hl, ht, r, GUARD_RGBA)  # edge guard = outer rim
    _rounded_rect(paddle, "skin", hw - EDGE_GUARD, hl - EDGE_GUARD, ht + 0.0004, r - EDGE_GUARD, FACE_RGBA)
    kw = dict(contype=0, conaffinity=0, group=2, mass=0)
    # Throat: the face narrows into the handle.
    paddle.add_geom(name="throat", type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0, -hl - 0.006, 0],
                    size=[0.026, 0.008, ht * 0.9], rgba=GUARD_RGBA, **kw)
    # Grip: wrapped handle, raised overgrip bands, flared butt cap.
    hy = -(hl + HANDLE_LENGTH / 2)
    rot_y = [0.7071068, 0.7071068, 0.0, 0.0]  # cylinder/capsule axis along paddle y
    paddle.add_geom(name="grip_wrap", type=mujoco.mjtGeom.mjGEOM_CYLINDER, pos=[0, hy, 0], quat=rot_y,
                    size=[HANDLE_RADIUS, HANDLE_LENGTH / 2 - 0.004, 0], rgba=GRIP_RGBA, **kw)
    for i, dy in enumerate((-0.045, -0.027, -0.009, 0.009, 0.027, 0.045)):
        paddle.add_geom(name=f"grip_band{i}", type=mujoco.mjtGeom.mjGEOM_CYLINDER, pos=[0, hy + dy, 0],
                        quat=rot_y, size=[HANDLE_RADIUS + 0.0012, 0.0025, 0], rgba=[0.78, 0.78, 0.76, 1], **kw)
    paddle.add_geom(name="butt_cap", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                    pos=[0, hy - HANDLE_LENGTH / 2 + 0.003, 0], quat=rot_y,
                    size=[HANDLE_RADIUS + 0.004, 0.005, 0], rgba=CAP_RGBA, **kw)


def attach_paddle(spec: mujoco.MjSpec, grip: GripCfg | None = None) -> mujoco.MjsBody:
    grip = grip or DEFAULT_GRIP
    pos, quat = paddle_pose_in_wrist(grip)
    wrist = spec.body(WRIST_BODY)
    paddle = wrist.add_body(name=PADDLE_BODY, pos=pos.tolist(), quat=quat.tolist())
    # Inertia: face plate plus handle, lumped. The CoM sits slightly toward the handle.
    face_mass, handle_mass = 0.8 * PADDLE_MASS, 0.2 * PADDLE_MASS
    w, l, t = (2 * h for h in PADDLE_HALF)
    handle_y = -(PADDLE_HALF[1] + HANDLE_LENGTH / 2)
    com_y = handle_mass * handle_y / PADDLE_MASS
    ixx = face_mass * (l**2 + t**2) / 12 + face_mass * com_y**2 + handle_mass * (handle_y - com_y) ** 2
    iyy = face_mass * (w**2 + t**2) / 12
    izz = face_mass * (w**2 + l**2) / 12 + face_mass * com_y**2 + handle_mass * (handle_y - com_y) ** 2
    paddle.explicitinertial = True
    paddle.mass = PADDLE_MASS
    paddle.ipos = [0.0, com_y, 0.0]
    paddle.iquat = [1.0, 0.0, 0.0, 0.0]
    paddle.inertia = [ixx, iyy, izz]
    # Reference shapes used by the analytic ball contact (box face) and the handle axis; hidden,
    # because the drawn paddle below is a styled version of the same dimensions.
    paddle.add_geom(name="paddle_face", type=mujoco.mjtGeom.mjGEOM_BOX, size=list(PADDLE_HALF),
                    rgba=[0.1, 0.3, 0.8, 1.0], contype=0, conaffinity=0, group=HIDDEN_GROUP, mass=0)
    paddle.add_geom(name="paddle_handle", type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                    size=[HANDLE_RADIUS, HANDLE_LENGTH / 2, 0.0], pos=[0.0, handle_y, 0.0],
                    quat=[0.7071068, 0.7071068, 0.0, 0.0], rgba=[0.15, 0.15, 0.15, 1.0],
                    contype=0, conaffinity=0, group=HIDDEN_GROUP, mass=0)
    add_paddle_visual(paddle)
    paddle.add_site(name="paddle_face_centre", pos=[0, 0, 0], size=[0.01, 0, 0])
    if grip.closed_hand:
        add_closed_hand(spec, grip)
    return paddle




def _capsule(body, name, a, b, r):
    body.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=list(a) + list(b), size=[r, 0, 0],
                  rgba=HAND_RGBA, contype=0, conaffinity=0, group=2, mass=0)


def add_closed_hand(spec: mujoco.MjSpec, grip: GripCfg) -> None:
    """Visual-only closed hand around the handle (no mass, no contacts; physics unchanged).

    The G1 rubber hand is a single rigid open-hand mesh. It is moved to a hidden geom
    group and replaced by a palm, four curled fingers and a thumb wrapped around the handle.
    Built in the wrist frame from the paddle pose: handle axis = paddle +y; the palm sits
    on the paddle -z side of the handle (the palm normal is the paddle normal).
    """
    wrist = spec.body(WRIST_BODY)
    for g in wrist.geoms:
        if g.type == mujoco.mjtGeom.mjGEOM_MESH and "rubber_hand" in (g.meshname or ""):
            g.group = HIDDEN_GROUP
    c, q = paddle_pose_in_wrist(grip)
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q)
    R = R.reshape(3, 3)
    hy = -(PADDLE_HALF[1] + HANDLE_LENGTH / 2)  # handle centre along the paddle y axis
    to_wrist = lambda x, y, z: c + R @ np.array([x, y, z])
    rf, ring = 0.0095, HANDLE_RADIUS + 0.0095
    pt = lambda deg, y: to_wrist(ring * math.cos(math.radians(deg)), y, ring * math.sin(math.radians(deg)))
    # Palm pad behind the handle, and the back of the hand joining it to the wrist link.
    palm = to_wrist(0.0, hy, -(HANDLE_RADIUS + 0.013))
    wrist.add_geom(name="hand_palm", type=mujoco.mjtGeom.mjGEOM_BOX, pos=palm.tolist(), quat=q.tolist(),
                   size=[0.034, 0.047, 0.012], rgba=HAND_RGBA, contype=0, conaffinity=0, group=2, mass=0)
    _capsule(wrist, "hand_back", (0.035, 0.0, 0.0), palm, 0.028)
    # Four fingers stacked along the handle (index nearest the face), curled from the palm edge
    # around the far side of the handle.
    for i, dy in enumerate((0.030, 0.010, -0.010, -0.029)):
        y = hy + dy
        arc = [-125, -180, 130, 75] if i < 3 else [-125, -180, 135, 90]
        for k in range(len(arc) - 1):
            _capsule(wrist, f"hand_finger{i}_{k}", pt(arc[k], y), pt(arc[k + 1], y), rf - 0.0005 * i)
    # Thumb across the top of the handle, toward the index finger.
    ty = hy + 0.048
    _capsule(wrist, "hand_thumb_0", to_wrist(0.026, hy + 0.020, -(HANDLE_RADIUS + 0.008)), pt(-35, ty), 0.0105)
    _capsule(wrist, "hand_thumb_1", pt(-35, ty), pt(25, ty + 0.006), 0.0100)
    _capsule(wrist, "hand_thumb_2", pt(25, ty + 0.006), pt(70, ty + 0.010), 0.0095)


def get_spec(grip: GripCfg | None = None) -> mujoco.MjSpec:
    spec = g1.get_spec()
    attach_paddle(spec, grip)
    return spec


def get_g1_paddle_cfg(grip: GripCfg | None = None) -> EntityCfg:
    cfg = g1.get_g1_robot_cfg()
    cfg = copy.copy(cfg)
    cfg.spec_fn = get_spec if grip is None else functools.partial(get_spec, grip)
    return cfg
