"""Named feed families for the standing-return drills (Stage 4).

Each family is a FeedCfg: ranges for the ballistic aim (no drag; aerodynamics then
shortens it slightly), the lateral offset from the robot's pelvis (its right is -y)
and spin. `spin_y` is signed for travel toward -x: positive = topspin, negative = backspin.
A FeedMix samples a family per episode by weight; tasks record the family index so
evaluations can be reported per family. Every Stage 4 family is checked offline
(scripts/tune_feed.py --families): it bounces exactly once before the contact plane,
arrives at a reachable height, and stays within reach (tests/test_feeds.py).

Reach families (Stage 5, footwork) need the robot to move: their hittable window (after the
bounce, before a second bounce, at paddle height) lies 1-2.5 m to the side, or in front of or
behind the start spot. They are checked for the travel they require (tune_feed.py --reach).
With a feed anchor (footwork tasks) bounce_x and lateral_y are relative to the robot's current
pelvis position (bounce_x shifted by the anchor's offset from ROBOT_START), so each family keeps
its meaning wherever the robot stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class FeedCfg:
    start_x: tuple[float, float] = (0.8, 1.2)
    start_z: tuple[float, float] = (1.2, 1.6)
    bounce_x: tuple[float, float] = (-4.6, -4.2)
    lateral_y: tuple[float, float] = (-0.65, -0.30)
    flight_time: tuple[float, float] = (0.8, 0.95)
    spin_y: tuple[float, float] = (0.0, 30.0)  # rad/s, + = topspin for travel toward -x


EASY_FOREHAND = FeedCfg()  # the Stage 2 drill

FAMILIES: dict[str, FeedCfg] = {
    "easy_forehand": EASY_FOREHAND,
    "wide_forehand": replace(EASY_FOREHAND, lateral_y=(-0.90, -0.65)),
    "backhand": replace(EASY_FOREHAND, lateral_y=(0.30, 0.65)),
    "deep": replace(EASY_FOREHAND, bounce_x=(-5.0, -4.7), flight_time=(0.9, 1.05), start_z=(1.3, 1.7)),
    "short": replace(EASY_FOREHAND, bounce_x=(-4.1, -3.8), flight_time=(0.95, 1.05), start_z=(2.1, 2.5)),
    "high": replace(EASY_FOREHAND, start_z=(2.7, 3.1), flight_time=(1.1, 1.2), bounce_x=(-4.3, -4.0)),
    "low": replace(EASY_FOREHAND, start_z=(0.95, 1.15), flight_time=(0.7, 0.8), bounce_x=(-4.8, -4.5)),
    "fast": replace(EASY_FOREHAND, flight_time=(0.6, 0.7), start_z=(1.0, 1.3), bounce_x=(-4.7, -4.4)),
    "topspin": replace(EASY_FOREHAND, spin_y=(60.0, 120.0)),
    "backspin": replace(EASY_FOREHAND, spin_y=(-120.0, -60.0)),
}
STAGE4_FAMILIES: tuple[str, ...] = tuple(FAMILIES)
BOUNCE_AIM_MIN = -7.5  # drag-corrected: aims beyond this land past the baseline  # the ten standing families (Stage 4 tasks)

# Stage 5 reach families: longer, higher feeds so there is time to move (about 1.1-1.3 s flight).
REACH_FAMILIES_CFG: dict[str, FeedCfg] = {
    "reach_forehand": replace(EASY_FOREHAND, lateral_y=(-2.5, -1.0), start_z=(1.9, 2.3), flight_time=(1.15, 1.3)),
    "reach_backhand": replace(EASY_FOREHAND, lateral_y=(1.0, 2.5), start_z=(1.9, 2.3), flight_time=(1.15, 1.3)),
    "reach_short": replace(EASY_FOREHAND, bounce_x=(-3.0, -2.5), start_z=(1.3, 1.6), flight_time=(0.85, 1.0)),
    # Aimed past the baseline: drag shortens these lobs by ~0.9 m, so they bounce behind the robot.
    # Feeds clamp the aim at BOUNCE_AIM_MIN so that from deep start spots they still land in.
    "reach_deep": replace(EASY_FOREHAND, bounce_x=(-8.0, -7.6), start_z=(2.2, 2.6), flight_time=(1.15, 1.3)),
}
FAMILIES.update(REACH_FAMILIES_CFG)
# Drill 3 reach curriculum (stage5-sd2c-videos.md): the "near" end of each reach family, just past arm reach.
# A curriculum scale s in [0, 1] interpolates every range between this near version and the full family.
REACH_NEAR: dict[str, FeedCfg] = {
    "reach_forehand": replace(REACH_FAMILIES_CFG["reach_forehand"], lateral_y=(-1.1, -0.85)),
    "reach_backhand": replace(REACH_FAMILIES_CFG["reach_backhand"], lateral_y=(0.75, 1.0)),
    "reach_short": replace(REACH_FAMILIES_CFG["reach_short"], bounce_x=(-3.9, -3.6), start_z=(1.6, 2.0),
                           flight_time=(0.95, 1.05)),
    "reach_deep": replace(REACH_FAMILIES_CFG["reach_deep"], bounce_x=(-6.2, -5.9)),
}
REACH_FAMILIES: tuple[str, ...] = tuple(REACH_FAMILIES_CFG)
FAMILY_NAMES: tuple[str, ...] = tuple(FAMILIES)


@dataclass
class FeedMix:
    """Weights over FAMILY_NAMES (missing names have weight 0)."""

    weights: dict[str, float] = field(default_factory=lambda: {"easy_forehand": 1.0})

    def vector(self) -> list[float]:
        unknown = set(self.weights) - set(FAMILIES)
        if unknown:
            raise ValueError(f"unknown feed families: {sorted(unknown)}")
        w = [float(self.weights.get(n, 0.0)) for n in FAMILY_NAMES]
        if sum(w) <= 0:
            raise ValueError("feed mix has no positive weight")
        return w


def only(name: str) -> FeedMix:
    return FeedMix({name: 1.0})

# Drill 3 follow-up S-D3b (stage5-run-sd3.md): gentler near versions that start where the robot already succeeds.
REACH_NEAR_V2: dict[str, FeedCfg] = {
    "reach_forehand": REACH_NEAR["reach_forehand"],
    "reach_backhand": replace(REACH_FAMILIES_CFG["reach_backhand"], lateral_y=(0.55, 0.8)),
    "reach_short": replace(REACH_FAMILIES_CFG["reach_short"], bounce_x=(-4.2, -3.9), start_z=(1.8, 2.2),
                           flight_time=(0.95, 1.05)),
    "reach_deep": replace(REACH_FAMILIES_CFG["reach_deep"], bounce_x=(-5.4, -5.1)),
}
