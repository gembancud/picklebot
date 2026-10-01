"""Batched pickleball rally rules, ported from Unity `Doubles/DoublesRules.cs`.

One rally state per environment, as torch tensors. Coordinates are court-local
(court.py): Unity z (length) maps to x here and Unity x (width) maps to -y. Unity
is left-handed, so this keeps "right" meaning a player's right in our right-handed
frame. Team 0 plays the near side (x < 0) and team 1 the far side. Players 0..3;
team = player // 2.

Ported: phases, the two-bounce rule (serve and return must bounce), kitchen volleys
with the volley-momentum obligation, double hits, wrong receiver, out (lines are in),
wrong side, second bounce, serve landing (diagonal box beyond the kitchen line;
the kitchen line is a fault, the centre line is in), body contact, net touch by a
player, posts, lost ball and truncation. A ball touching the net is not a fault by
itself.
Not ported (not needed for Stage 2 drills): game scoring, server rotation and
side-out, serve motion rules (drop or volley serve) and continuous-stroke contacts.
Each call takes a boolean `mask` selecting the envs where that event happened.
"""

from __future__ import annotations

from enum import IntEnum

import torch

from picklebot_mj import court

HALF_WIDTH, HALF_LENGTH, KITCHEN = court.HALF_WIDTH, court.HALF_LENGTH, court.KITCHEN_DEPTH


class Phase(IntEnum):
    AWAIT_SERVE = 0
    SERVE_FLIGHT = 1
    RETURN_FLIGHT = 2
    RALLY = 3
    DEAD = 4


class Fault(IntEnum):  # same order as Unity DoublesRules.Fault
    NONE = 0
    SERVE_FOOT = 1
    SERVE_MOTION = 2
    SERVE_LANDING = 3
    WRONG_RECEIVER = 4
    EARLY_VOLLEY = 5
    KITCHEN_VOLLEY = 6
    KITCHEN_MOMENTUM = 7
    DOUBLE_HIT = 8
    SECOND_BOUNCE = 9
    OUT = 10
    WRONG_SIDE = 11
    BODY_CONTACT = 12
    NET_TOUCH = 13
    LOST = 14
    CARRY = 15
    SERVE_TIMEOUT = 16
    PERMANENT_OBJECT = 17


# Geometry helpers (court-local tensors, (..., >=2)) -----------------------------------

def in_bounds(p: torch.Tensor) -> torch.Tensor:
    """Landing point inside the court; boundary lines are in."""
    return (p[..., 0].abs() <= HALF_LENGTH) & (p[..., 1].abs() <= HALF_WIDTH)


def landing_team(p: torch.Tensor) -> torch.Tensor:
    """Team whose half the point is on (0 near, 1 far)."""
    return (p[..., 0] >= 0).long()


def in_kitchen_zone(p: torch.Tensor) -> torch.Tensor:
    """Point inside the non-volley zone; the kitchen line counts as kitchen."""
    return p[..., 0].abs() <= KITCHEN


def team_of(player: torch.Tensor) -> torch.Tensor:
    return player // 2


def court_sign(team: torch.Tensor) -> torch.Tensor:
    """-1 for the near team, +1 for the far team (Unity Side)."""
    return team * 2 - 1


class RallyRules:
    def __init__(self, num_envs: int, device: str | torch.device = "cpu"):
        n, dev = num_envs, device
        z = lambda dtype=torch.long: torch.zeros(n, dtype=dtype, device=dev)
        self.phase = z()
        self.fault = z()
        self.winner = z() - 1
        self.serving_team = z()
        self.server = z()
        self.designated_receiver = z()
        self.expected_team = z()
        self.last_hitter = z() - 1
        self.bounced = z(torch.bool)
        self.hits = z()
        # Per-player kitchen state: (N, 4).
        self.kitchen_occupied = torch.zeros(n, 4, dtype=torch.bool, device=dev)
        self.established_outside = torch.ones(n, 4, dtype=torch.bool, device=dev)
        self.volley_pending = torch.zeros(n, 4, dtype=torch.bool, device=dev)
        # Right player per team: (N, 2). Default: players 0 and 2 on the right.
        self.right_player = torch.tensor([0, 2], device=dev).repeat(n, 1)

    @property
    def dead(self) -> torch.Tensor:
        return self.phase == Phase.DEAD

    # Setup ---------------------------------------------------------------------------
    def begin_rally(self, env_ids: torch.Tensor, server: torch.Tensor, server_on_right: torch.Tensor):
        """Start a rally awaiting the serve (Unity constructor + BeginRally, without scoring)."""
        team = team_of(server)
        self.server[env_ids] = server
        self.serving_team[env_ids] = team
        rp = self.right_player[env_ids].clone()
        rows = torch.arange(len(env_ids), device=rp.device)
        rp[rows, team] = torch.where(server_on_right, server, server ^ 1)
        self.right_player[env_ids] = rp
        recv_team = 1 - team
        recv_right = rp[rows, recv_team]
        self.designated_receiver[env_ids] = torch.where(server_on_right, recv_right, recv_right ^ 1)
        self.expected_team[env_ids] = recv_team
        self._reset_common(env_ids, Phase.AWAIT_SERVE)
        self.last_hitter[env_ids] = -1

    def begin_from_feed(self, env_ids: torch.Tensor, feeder: torch.Tensor, phase: Phase = Phase.RALLY,
                        must_bounce: bool = False):
        """Drill start: the ball is in flight after a feed by `feeder` (the opponent).

        phase RALLY allows volleys; RETURN_FLIGHT models a served-ball receive (must bounce)
        when must_bounce is set (equivalent to Unity SERVE_FLIGHT receive context).
        """
        self._reset_common(env_ids, Phase.SERVE_FLIGHT if must_bounce else phase)
        self.last_hitter[env_ids] = feeder
        self.serving_team[env_ids] = team_of(feeder)
        self.server[env_ids] = feeder
        self.expected_team[env_ids] = 1 - team_of(feeder)
        self.hits[env_ids] = 1
        self.designated_receiver[env_ids] = -1  # any player of the receiving team (drill)

    def _reset_common(self, env_ids, phase):
        self.phase[env_ids] = int(phase)
        self.fault[env_ids] = int(Fault.NONE)
        self.winner[env_ids] = -1
        self.bounced[env_ids] = False
        self.hits[env_ids] = 0
        self.kitchen_occupied[env_ids] = False
        self.volley_pending[env_ids] = False
        self.established_outside[env_ids] = True

    # Events --------------------------------------------------------------------------
    def fail(self, mask: torch.Tensor, losing_team: torch.Tensor, fault: Fault):
        m = mask & ~self.dead
        self.winner = torch.where(m, 1 - losing_team, self.winner)
        self.fault = torch.where(m, torch.full_like(self.fault, int(fault)), self.fault)
        self.phase = torch.where(m, torch.full_like(self.phase, int(Phase.DEAD)), self.phase)

    def feet(self, mask: torch.Tensor, player: torch.Tensor, touches_kitchen: torch.Tensor,
             both_feet_outside: torch.Tensor, balance_recovered: torch.Tensor):
        rows = torch.arange(self.phase.shape[0], device=self.phase.device)
        p = player.clamp(0, 3)
        occ = self.kitchen_occupied[rows, p]
        est = self.established_outside[rows, p]
        self.kitchen_occupied[rows, p] = torch.where(mask, touches_kitchen, occ)
        new_est = torch.where(touches_kitchen, torch.zeros_like(est), torch.where(both_feet_outside, torch.ones_like(est), est))
        self.established_outside[rows, p] = torch.where(mask, new_est, est)
        pending = self.volley_pending[rows, p]
        momentum = mask & pending & touches_kitchen
        self.fail(momentum, team_of(p), Fault.KITCHEN_MOMENTUM)
        # (Unity also re-assigns late momentum on an unresolved dead rally; there is no
        # separate resolution step here, so a dead rally keeps its first fault.)
        clear = mask & both_feet_outside & balance_recovered
        self.volley_pending[rows, p] = torch.where(clear, torch.zeros_like(pending), self.volley_pending[rows, p])

    def fixed_ball_serve(self, mask: torch.Tensor, player: torch.Tensor, legal_feet: torch.Tensor):
        m = mask & (self.phase == Phase.AWAIT_SERVE)
        wrong = m & (player != self.server)
        self.fail(wrong, self.serving_team, Fault.WRONG_RECEIVER)
        foot = m & ~wrong & ~legal_feet
        self.fail(foot, self.serving_team, Fault.SERVE_FOOT)
        ok = m & ~wrong & ~foot
        self.phase = torch.where(ok, torch.full_like(self.phase, int(Phase.SERVE_FLIGHT)), self.phase)
        self.last_hitter = torch.where(ok, player, self.last_hitter)
        self.hits = torch.where(ok, torch.ones_like(self.hits), self.hits)

    def hit(self, mask: torch.Tensor, player: torch.Tensor):
        """A paddle contact by `player` (kitchen state comes from earlier `feet` calls)."""
        m = mask & ~self.dead & (self.phase != Phase.AWAIT_SERVE)
        rows = torch.arange(self.phase.shape[0], device=self.phase.device)
        p = player.clamp(0, 3)
        team = team_of(p)
        double = m & (team != self.expected_team)
        self.fail(double, team, Fault.DOUBLE_HIT)
        wrong_recv = (m & ~double & (self.phase == Phase.SERVE_FLIGHT) & (self.designated_receiver >= 0)
                      & (p != self.designated_receiver))
        self.fail(wrong_recv, team, Fault.WRONG_RECEIVER)
        ok = m & ~double & ~wrong_recv
        can_volley = self.phase == Phase.RALLY
        early = ok & ~self.bounced & ~can_volley
        self.fail(early, team, Fault.EARLY_VOLLEY)
        kitchen = ok & ~early & ~self.bounced & (self.kitchen_occupied[rows, p] | ~self.established_outside[rows, p])
        self.fail(kitchen, team, Fault.KITCHEN_VOLLEY)
        legal = ok & ~early & ~kitchen
        volley = legal & ~self.bounced
        self.volley_pending[rows, p] = self.volley_pending[rows, p] | volley
        nxt = torch.where(self.phase == Phase.SERVE_FLIGHT, torch.full_like(self.phase, int(Phase.RETURN_FLIGHT)),
                          torch.where(self.phase == Phase.RETURN_FLIGHT, torch.full_like(self.phase, int(Phase.RALLY)), self.phase))
        self.phase = torch.where(legal, nxt, self.phase)
        self.bounced = torch.where(legal, torch.zeros_like(self.bounced), self.bounced)
        self.last_hitter = torch.where(legal, p, self.last_hitter)
        self.expected_team = torch.where(legal, 1 - team, self.expected_team)
        self.hits = torch.where(legal, self.hits + 1, self.hits)

    def bounce(self, mask: torch.Tensor, point: torch.Tensor):
        """Ball touches the court (or ground outside it) at court-local `point`."""
        m = mask & ~self.dead & (self.phase != Phase.AWAIT_SERVE)
        hitter_team = team_of(self.last_hitter.clamp(min=0))
        blame = torch.where(self.bounced, self.expected_team, hitter_team)
        out = m & ~in_bounds(point)
        self.fail(out, blame, Fault.OUT)
        land = landing_team(point)
        wrong_side = m & ~out & (land != self.expected_team)
        self.fail(wrong_side, blame, Fault.WRONG_SIDE)
        second = m & ~out & ~wrong_side & self.bounced
        self.fail(second, self.expected_team, Fault.SECOND_BOUNCE)
        rest = m & ~out & ~wrong_side & ~second
        serve_bad = rest & (self.phase == Phase.SERVE_FLIGHT) & (self.designated_receiver >= 0) & (
            in_kitchen_zone(point) | (point[..., 1] * self._service_y(self.designated_receiver.clamp(min=0)) < 0))
        self.fail(serve_bad, self.serving_team, Fault.SERVE_LANDING)
        ok = rest & ~serve_bad
        self.bounced = self.bounced | ok

    def _service_y(self, player: torch.Tensor) -> torch.Tensor:
        """Sign of the y centre of `player`'s service box (Unity ServiceX in our frame)."""
        team = team_of(player)
        rows = torch.arange(player.shape[0], device=player.device)
        is_right = self.right_player[rows, team] == player
        # Facing the net: the near team (facing +x) has its right at -y; the far team at +y.
        right_y = torch.where(team == 0, -1.0, 1.0)
        return torch.where(is_right, right_y, -right_y) * HALF_WIDTH * 0.5

    def body_contact(self, mask, player):
        self.fail(mask, team_of(player), Fault.BODY_CONTACT)

    def net_touch(self, mask, player):
        self.fail(mask, team_of(player), Fault.NET_TOUCH)

    def _blame_now(self):
        return torch.where(self.bounced, self.expected_team, team_of(torch.where(self.last_hitter < 0, self.server, self.last_hitter)))

    def lost(self, mask):
        self.fail(mask, self._blame_now(), Fault.LOST)

    def permanent_object(self, mask):
        """E.g. the ball hits a net post before landing (Unity PermanentObject)."""
        self.fail(mask, self._blame_now(), Fault.PERMANENT_OBJECT)

    def truncate(self, mask):
        m = mask & ~self.dead
        self.winner = torch.where(m, torch.full_like(self.winner, -1), self.winner)
        self.fault = torch.where(m, torch.full_like(self.fault, int(Fault.NONE)), self.fault)
        self.phase = torch.where(m, torch.full_like(self.phase, int(Phase.DEAD)), self.phase)
