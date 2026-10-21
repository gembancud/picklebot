"""Two-robot rally video frames (D-132 interim video): one court with both robots of a pair.

In pair mode each robot lives in its own env and sees itself on the near side (picklebot_mj/pairs.py). This draws the
court of env a with robot a, and adds robot b from env b turned 180 degrees about the court centre, so it appears on
the far side of the same court. A ball is drawn only while it is on its owner's half: a's ball while x < 0 in a's
court frame, b's ball (turned) while x < 0 in b's frame. After a return crosses the net, a's own copy of it is not
drawn; b's received copy is. b's copy of the court is not drawn (the court is symmetric). Rendering only: nothing here
touches the simulation.
"""

from __future__ import annotations

import mujoco
import numpy as np


def _quat_turn_z(q: np.ndarray) -> np.ndarray:
    """(w, x, y, z) rotated by 180 degrees about the world z axis: q_z(pi) * q."""
    w, x, y, z = q
    return np.array([-z, -y, x, w])


class PairFrames:
    def __init__(self, env, ball_term, width: int = 960, height: int = 540, distance: float = 8.5,
                 elevation: float = -20.0, azimuth: float = 270.0):
        r = env._offline_renderer
        if r is None:
            raise ValueError("the environment needs render_mode='rgb_array'")
        self.env, self.r = env, r
        self.model = r._model
        self.origins = env.scene.env_origins.cpu().numpy()
        names = [mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, i) or "" for i in range(self.model.nbody)]
        mocap = {names[b].split("/")[0]: int(self.model.body_mocapid[b]) for b in range(self.model.nbody)
                 if self.model.body_mocapid[b] >= 0}
        self.ball_mocap, self.court_mocap = mocap["ball"], mocap["court"]
        self.free = ball_term._entity.data.indexing.free_joint_q_adr.cpu().numpy()
        self.cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(self.model, self.cam)
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE.value
        self.cam.distance, self.cam.elevation, self.cam.azimuth = distance, elevation, azimuth
        self.hidden = np.array([0.0, 0.0, -50.0])

    def frame(self, a: int, b: int) -> np.ndarray:
        r, data, d = self.r, self.env.sim.data, self.r._data
        oa, ob = self.origins[a], self.origins[b]
        # env a: its robot, its court, its ball while on its own half
        r._sync_model_fields(a)
        r._sync_data_fields(data, a)
        if d.mocap_pos[self.ball_mocap][0] - oa[0] > 0.0:
            d.mocap_pos[self.ball_mocap] = self.hidden
            mujoco.mj_forward(self.model, d)
        self.cam.lookat[:] = oa + np.array([0.0, 0.0, 0.6])
        r._renderer.update_scene(d, camera=self.cam, scene_option=r._opt)
        # env b, turned onto the far side of a's court
        r._sync_model_fields(b)
        r._sync_data_fields(data, b)
        p = d.qpos[self.free[:3]] - ob
        d.qpos[self.free[:3]] = np.array([-p[0], -p[1], p[2]]) + oa
        d.qpos[self.free[3:7]] = _quat_turn_z(d.qpos[self.free[3:7]].copy())
        bp = d.mocap_pos[self.ball_mocap] - ob
        d.mocap_pos[self.ball_mocap] = (np.array([-bp[0], -bp[1], bp[2]]) + oa) if bp[0] < 0.0 else self.hidden
        d.mocap_pos[self.court_mocap] = self.hidden
        mujoco.mj_forward(self.model, d)
        mujoco.mjv_addGeoms(self.model, d, r._opt, r._pert, r._catmask.value, r._renderer.scene)
        return r._renderer.render()


def caption(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    """Text lines over a dark band at the top of the frame (PIL)."""
    from PIL import Image, ImageDraw
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    h = 8 + 18 * len(lines)
    draw.rectangle([0, 0, img.width, h], fill=(0, 0, 0))
    for i, t in enumerate(lines):
        draw.text((10, 6 + 18 * i), t, fill=(255, 255, 255))
    return np.asarray(img)
