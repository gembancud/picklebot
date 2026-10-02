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
import math
from dataclasses import dataclass

import mujoco
import numpy as np

from mjlab.asset_zoo.robots.unitree_g1 import g1_constants as g1
from mjlab.entity import EntityCfg

from picklebot_mj.ball_sim import PADDLE_HALF

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


# v1: Stage 2 mount (handle centred on the palm site, in line with the hand). Close-ups showed
# the face starting ~4 cm inside the fingers and the paddle in line with the forearm.
GRIP_V1 = GripCfg("v1-inline", 0.0, (PALM_X, 0.0, 0.0))
FACE_CENTRE_X = PALM_X + HANDLE_LENGTH / 2 + PADDLE_HALF[1]  # v1 face centre along the hand axis
# v2: handshake grip. The handle crosses the palm 35 deg toward the thumb, held in the finger curl
# (+y) and slid out so the face clears every hand-mesh vertex by >= 3 mm
# (scripts/fit_grip.py, 2026-10-02).
GRIP_V2 = GripCfg("v2-handshake", 35.0, (0.1084, 0.025, 0.0129))
DEFAULT_GRIP = GRIP_V1


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
    paddle.add_geom(name="paddle_face", type=mujoco.mjtGeom.mjGEOM_BOX, size=list(PADDLE_HALF),
                    rgba=[0.1, 0.3, 0.8, 1.0], contype=0, conaffinity=0, group=2, mass=0)
    paddle.add_geom(name="paddle_handle", type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                    size=[HANDLE_RADIUS, HANDLE_LENGTH / 2, 0.0], pos=[0.0, handle_y, 0.0],
                    quat=[0.7071068, 0.7071068, 0.0, 0.0], rgba=[0.15, 0.15, 0.15, 1.0],
                    contype=0, conaffinity=0, group=2, mass=0)
    paddle.add_site(name="paddle_face_centre", pos=[0, 0, 0], size=[0.01, 0, 0])
    return paddle


def get_spec(grip: GripCfg | None = None) -> mujoco.MjSpec:
    spec = g1.get_spec()
    attach_paddle(spec, grip)
    return spec


def get_g1_paddle_cfg() -> EntityCfg:
    cfg = g1.get_g1_robot_cfg()
    cfg = copy.copy(cfg)
    cfg.spec_fn = get_spec
    return cfg
