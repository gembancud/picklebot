"""Ball-index tally (picklebot_mj/tasks/ball_index.py), its summary / coded rule (picklebot_mj/ballidx_rule.py) and the
diagnostic task (tasks/agility.py TASK_AGILITY_BALLIDX). CPU only: the tally runs against a small fake term."""

from types import SimpleNamespace

import torch

from picklebot_mj import ballidx_rule as br


# ------------------------------------------------------------------------------------------
class _Pairs:
    """What the tally reads from PairCourts; step / on_reset return or record scripted events."""

    def __init__(self, n):
        self.n, self.h = n, n // 2
        self.handed = torch.zeros(n, dtype=torch.bool)
        self.court_dead = torch.zeros(n // 2, dtype=torch.bool)
        self.waiting = torch.zeros(n, dtype=torch.bool)
        self.partner = (torch.arange(n) + n // 2) % n
        self.group = torch.zeros(n // 2, dtype=torch.long)
        self.next = None  # (fire, recv) for the next step call
        self.resets = []

    def court(self, m):
        return m[: self.h] | m[self.h:]

    def step(self, over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        z = torch.zeros_like(over)
        fire, recv = self.next if self.next is not None else (z, z)
        self.next = None
        return fire, recv

    def on_reset(self, env_ids, fell_open=None):
        self.resets.append(env_ids)


class _Term:
    def __init__(self, n=8):
        self.num_envs, self.device = n, "cpu"
        pose = torch.zeros(n, 7)
        pose[:, 3] = 1.0  # facing +x (the net)
        self._entity = SimpleNamespace(data=SimpleNamespace(root_link_pose_w=pose))
        self.ball = SimpleNamespace(pos=torch.zeros(n, 3), vel=torch.zeros(n, 3), spin=torch.zeros(n, 3))
        self.hit_done = torch.zeros(n, dtype=torch.bool)
        self.tallied = torch.zeros(n, dtype=torch.bool)
        self.pairs = _Pairs(n)
        self._env = SimpleNamespace(cfg=SimpleNamespace(decimation=4))

    def pelvis_xy(self, env_ids=None):
        return self._entity.data.root_link_pose_w[:, :2].clone()


def _mask(n, ids):
    m = torch.zeros(n, dtype=torch.bool)
    m[list(ids)] = True
    return m


def _tally(n=8):
    from picklebot_mj.tasks.ball_index import BallIndexTally
    t = _Term(n)
    calls = []

    def predictor(pos, vel, spin):  # the interception is the hand-off position itself; not found when z < 0
        calls.append(pos.shape[0])
        return pos.clone(), pos[:, 2] >= 0

    tally = BallIndexTally(t, t._env, predictor=predictor, batch=4)
    return t, tally, calls


def _step(t, over=(), legal=(), contact=(), fire=(), recv=()):
    n = t.num_envs
    o = _mask(n, over)
    t.tallied |= o
    t.pairs.next = (_mask(n, fire), _mask(n, recv))
    return t.pairs.step(o, _mask(n, legal), torch.zeros(n, dtype=torch.bool), torch.zeros(n, dtype=torch.bool), 0.005,
                        0.5, contact=_mask(n, contact))


def test_tally_hooks_and_counts_handed_balls_by_index_direction_speed_distance():
    n = 8
    t, tally, calls = _tally(n)
    assert t.pairs.step == tally.step and t.pairs.on_reset == tally.on_reset
    t.pairs.group[3] = 1  # court 3 is a drill court
    _step(t, fire=(0, 1, 2, 3))  # feeder balls on side A
    # the partners' returns, mirrored at the hand-off: receivers 4-7 see forward / left / back / right at 1 m, 1-7 m/s
    t.ball.pos[:4] = torch.tensor([[-1.0, 0, 1], [0, -1.0, 1], [1.0, 0, 1], [0, 1.0, 1]])
    t.ball.vel[:4] = torch.tensor([[-1.0, 0, 0], [0, -3.0, 0], [5.0, 0, 0], [0, 4.2, -5.6]])  # |v| 1, 3, 5, 7
    _step(t, recv=(4, 5, 6, 7))
    assert tally.kb[4:].tolist() == [0, 0, 0, 0] and tally.open[4:].all() and tally.pend[4:].all()
    assert torch.allclose(tally.spd[4:], torch.tensor([1.0, 3.0, 5.0, 7.0]))
    assert torch.allclose(tally.hspd[4:], torch.tensor([1.0, 3.0, 5.0, 4.2]))
    for _ in range(2):
        _step(t)
    assert calls == [4]  # call 0 only so far (decimation 4): nothing pending then
    _step(t)  # call 4: the pending hand-offs are predicted
    assert tally.dirc[4:].tolist() == [0, 1, 2, 3] and torch.allclose(tally.dist[4:], torch.ones(4))
    assert not tally.pend.any()
    # outcomes: 4 legal (contact), 5 contact then not legal, 6 the hitter's shot faulted (void), 7 volleyed back (early)
    t.hit_done[4:6] = True
    t.pairs.waiting[6] = True
    t.ball.pos[3] = torch.tensor([0.0, 1.0, -1.0])  # env 7's next ball gets no interception
    _step(t, over=(4, 5, 6, 2), legal=(4,), recv=(7,))
    c = tally.counters()
    cell = lambda g, k, d: br._cell(g, k, d)  # noqa: E731
    assert c["balls"][cell(0, 0, 0)] == 1 and c["legal"][cell(0, 0, 0)] == 1 and c["contact"][cell(0, 0, 0)] == 1
    assert c["balls"][cell(0, 0, 1)] == 1 and c["legal"][cell(0, 0, 1)] == 0 and c["contact"][cell(0, 0, 1)] == 1
    assert c["balls"][cell(0, 0, 2)] == 0 and c["void"][0] == 1  # group 0, k = 1
    assert c["balls"][cell(1, 0, 3)] == 1 and c["legal"][cell(1, 0, 3)] == 1 and c["early"][cell(1, 0, 3)] == 1
    assert c["received"][0] == 3 and c["received"][3] == 1  # group 1 (drill court 3), k = 1
    assert c["speed"][cell(0, 0, 0)][2] == 1 and c["speed"][cell(0, 0, 1)][6] == 1 and c["hspeed"][cell(1, 0, 3)][8] == 1
    assert c["dist"][cell(0, 0, 0)][4] == 1 and c["dist_legal"][cell(0, 0, 0)][4] == 1
    assert c["speed_legal"][cell(0, 0, 1)][6] == 0
    # env 7 now holds the court's 2nd hand-off (k = 2); its prediction finds nothing; a fall ends it
    assert int(tally.kb[7]) == 1 and tally.open[7]
    for _ in range(4):
        _step(t)
    assert int(tally.dirc[7]) == 4
    tally.on_reset(torch.tensor([7, 4]), fell_open=_mask(n, (7,)))
    c = tally.counters()
    assert c["balls"][cell(1, 1, 4)] == 1 and c["fell"][cell(1, 1, 4)] == 1 and c["legal"][cell(1, 1, 4)] == 0
    assert c["dist"][cell(1, 1, 4)][-1] == 1  # no interception: distance in the overflow bin
    assert len(t.pairs.resets) == 1 and not tally.open.any()
    # a new feeder ball restarts the court's count; a censored (time-out) reset is not a ball
    _step(t, fire=(1,))
    _step(t, recv=(5,))
    assert int(tally.kb[5]) == 0
    tally.on_reset(torch.tensor([5]), fell_open=_mask(n, ()))
    assert tally.counters()["censored"][0] == 1


def test_rally_index_bins_count_hand_offs_since_the_feeder_ball():
    n = 4
    t, tally, _ = _tally(n)
    _step(t, fire=(0,))
    seen = []
    for i in range(5):  # hand-offs alternate sides: 2, 0, 2, 0, 2
        r = 2 if i % 2 == 0 else 0
        _step(t, over=(), recv=(r,))
        seen.append(int(tally.kb[r]))
    assert seen == [0, 1, 2, 2, 2]  # k = 1, 2, 3+, 3+, 3+
    assert int(tally.nh[0]) == 5 and int(tally.nh[1]) == 0


# ------------------------------------------------------------------------------------------
def _counters(balls):
    """Counters from synthetic balls (k_bin, direction, speed, dist, legal), all on pair courts."""
    from picklebot_mj.tasks import ball_index as bi
    cells = bi.N_GROUPS * bi.N_KBINS * bi.N_DIRS
    c = {k: [0] * cells for k in ("balls", "contact", "legal", "fell", "early")}
    c["hspd_sum"] = [0.0] * cells
    for k in ("speed", "speed_legal", "hspeed", "hspeed_legal"):
        c[k] = [[0] * bi.SPEED_BINS for _ in range(cells)]
    for k in ("dist", "dist_legal"):
        c[k] = [[0] * bi.DIST_BINS for _ in range(cells)]
    for k in ("received", "void", "censored"):
        c[k] = [0] * (bi.N_GROUPS * bi.N_KBINS)
    for kb, d, sp, di, lg in balls:
        i = br._cell(0, kb, d)
        sb, db = min(int(sp / bi.SPEED_BIN), bi.SPEED_BINS - 1), min(int(di / bi.DIST_BIN), bi.DIST_BINS - 1)
        c["balls"][i] += 1
        c["contact"][i] += 1
        c["legal"][i] += int(lg)
        c["speed"][i][sb] += 1
        c["hspeed"][i][sb] += 1
        c["dist"][i][db] += 1
        c["received"][kb] += 1
        if lg:
            c["speed_legal"][i][sb] += 1
            c["dist_legal"][i][db] += 1
    return c


def _base(k1_speed=(6.2, 6.7, 7.2), k1_fail=(0.1, 0.1, 0.1), k1_dist=(1.1, 1.1, 1.1), k1_dirs=(0, 3, 0, 3),
          k1_dir_fail=None):
    balls = []
    for j in range(300):  # k >= 3: forward / right, 6.2 m/s, 1.1 m, 2 % failures
        balls.append((2, (0, 3, 0, 3, 0, 3, 0, 3, 0, 1)[j % 10], 6.2, 1.1, j % 50 != 0))
    for j in range(300):  # k = 1 in three equal speed / distance terciles
        t = j % 3
        d = k1_dirs[j % len(k1_dirs)]
        f = k1_fail[t] if k1_dir_fail is None else k1_dir_fail[d]
        balls.append((0, d, k1_speed[t], k1_dist[t], (j // 3) % 100 >= round(100 * f)))
    return br.summarize(_counters(balls))


def test_rule_routes_pace_reach_direction_other():
    assert br.route(_base())["verdict"] == "OTHER"
    pace = _base(k1_speed=(6.2, 7.7, 9.2), k1_fail=(0.1, 0.2, 0.4))  # p50 7.7+ >= 6.2+ + 1.0; 0.4 >= 2 x 0.1
    r = br.route(pace)
    assert r["fired"] == ["PACE"] and r["verdict"] == "PACE"
    assert br.route(_base(k1_speed=(6.2, 7.7, 9.2), k1_fail=(0.2, 0.2, 0.3)))["verdict"] == "OTHER"  # ratio < 2
    assert br.route(_base(k1_speed=(6.2, 6.7, 9.2), k1_fail=(0.1, 0.2, 0.4)))["verdict"] == "OTHER"  # p50 + 0.5 only
    reach = _base(k1_dist=(1.1, 1.8, 2.6), k1_fail=(0.05, 0.2, 0.3))
    assert br.route(reach)["fired"] == ["REACH"]
    both = _base(k1_speed=(6.2, 7.7, 9.2), k1_dist=(1.1, 1.8, 2.6), k1_fail=(0.05, 0.2, 0.3))
    assert br.route(both)["fired"] == ["PACE", "REACH"] and br.route(both)["verdict"] == "PACE + REACH"
    dirn = _base(k1_dirs=(1, 2, 0, 3), k1_dir_fail={0: 0.1, 1: 0.4, 2: 0.4, 3: 0.1})  # LB share 0.5 vs 0.1
    r = br.route(dirn)
    assert r["fired"] == ["DIRECTION"]
    assert len(r["lines"]) == 6 and all(("PASS" in x or "FAIL" in x) and ">=" in x for x in r["lines"])


def test_summary_rates_quantiles_and_terciles():
    s = _base(k1_speed=(6.2, 7.7, 9.2), k1_fail=(0.1, 0.2, 0.4))
    k1, k3 = s["k"][0], s["k"][2]
    assert k1["balls"] == 300 and abs(k1["legal"] - (1 - (0.1 + 0.2 + 0.4) / 3)) < 1e-3 and k1["contact"] == 1.0
    assert 7.5 <= k1["speed_p50"] <= 8.0 and 6.0 <= k3["speed_p50"] <= 6.5
    st = k1["speed_terciles"]
    assert st["bottom"]["balls"] == 100 and abs(st["bottom"]["failure"] - 0.1) < 1e-9 and abs(st["top"]["failure"] - 0.4) < 1e-9
    assert abs(k3["lb_share"] - 0.1) < 1e-9 and k1["directions"]["none"]["balls"] == 0
    assert br.quantile([0, 10, 0], 0.5, 0.5) == 0.75 and br.quantile([], 0.5, 1.0) is None
    assert [x["lo"] for x in s["fail_by_speed"]["1"]] == [6.0, 7.5, 9.0]


# ------------------------------------------------------------------------------------------
def test_ballidx_task_differs_from_its_source_only_in_the_tally_flag():
    import dataclasses

    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    assert ag.SRC_22B == "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1"
    for play in (False, True):
        src, a = load_env_cfg(ag.SRC_22B, play=play), load_env_cfg(ag.TASK_AGILITY_BALLIDX, play=play)
        sb, ab = src.actions["ball"], a.actions["ball"]
        assert isinstance(ab, ag.AgilityBallActionCfg) and ab.ball_index_tally
        assert [f.name for f in dataclasses.fields(sb) if getattr(sb, f.name) != getattr(ab, f.name)] == []
        extra = {f.name for f in dataclasses.fields(ab)} - {f.name for f in dataclasses.fields(sb)}
        assert [k for k in sorted(extra) if getattr(ab, k) != getattr(ag.AgilityBallActionCfg, k, None)
                and k != "ball_index_tally"] == []  # every other agility flag at its default (off)
        assert not ab.deadline_drill and not ab.direction_tally
        assert [k for k in src.actions if k != "ball" and src.actions[k] != a.actions[k]] == []
        for g in src.observations:
            assert list(src.observations[g].terms) == list(a.observations[g].terms)
        assert list(src.rewards) == list(a.rewards)
        assert [k for k in src.rewards if src.rewards[k].func is not a.rewards[k].func
                or src.rewards[k].weight != a.rewards[k].weight or src.rewards[k].params != a.rewards[k].params] == []
        assert list(src.terminations) == list(a.terminations)
        assert src.episode_length_s == a.episode_length_s and src.decimation == a.decimation
        assert src.scene.num_envs == a.scene.num_envs
    assert load_env_cfg(ag.TASK_AGILITY_BALLIDX).episode_length_s == 120.0
    assert load_env_cfg(ag.TASK_AGILITY_BALLIDX).actions["ball"].pair_drill_court_frac == 0.5
    assert load_runner_cls(ag.TASK_AGILITY_BALLIDX) is load_runner_cls(ag.SRC_22B)
    assert load_rl_cfg(ag.TASK_AGILITY_BALLIDX) == load_rl_cfg(ag.SRC_22B)
