"""Feed families: reachable, single-bounce, and actually different from the easy drill."""

import sys
from pathlib import Path

import pytest
import torch

from picklebot_mj.feeds import FAMILIES, FAMILY_NAMES, FeedMix, only

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tune_feed import _FakeTerm, evaluate  # noqa: E402


@pytest.fixture(scope="module")
def stats():
    return {name: evaluate(only(name), n=512) for name in FAMILY_NAMES}


@pytest.mark.parametrize("name", FAMILY_NAMES)
def test_family_is_single_bounce_and_reachable(stats, name):
    r = stats[name]
    assert r["one_bounce"] >= 0.99
    assert r["height_p05"] >= 0.28 and r["height_p95"] <= 1.2  # measured face-centre reach 0.29-1.73 m
    assert -0.92 <= r["lateral_min"] and r["lateral_max"] <= 0.92  # measured reach 0.90 m


def test_families_differ_from_easy(stats):
    e = stats["easy_forehand"]
    assert stats["wide_forehand"]["lateral_max"] <= -0.64
    assert stats["backhand"]["lateral_min"] >= 0.29
    assert stats["high"]["height_p50"] >= e["height_p50"] + 0.2
    assert stats["low"]["height_p50"] <= e["height_p50"] - 0.08
    assert stats["fast"]["speed_p50"] >= 1.4 * e["speed_p50"]
    assert FAMILIES["deep"].bounce_x[1] < FAMILIES["easy_forehand"].bounce_x[0]
    assert FAMILIES["short"].bounce_x[0] > FAMILIES["easy_forehand"].bounce_x[1]


def test_spin_signs():
    t = _FakeTerm(only("topspin"), 64)
    t._feed(torch.arange(64))
    assert (t.ball.spin[:, 1] < 0).all()  # topspin for travel toward -x is about -y
    t = _FakeTerm(only("backspin"), 64)
    t._feed(torch.arange(64))
    assert (t.ball.spin[:, 1] > 0).all()


def test_mix_sampling_and_validation():
    t = _FakeTerm(FeedMix({"easy_forehand": 1.0, "backhand": 3.0}), 4000, seed=1)
    t._feed(torch.arange(4000))
    frac_backhand = (t.family == FAMILY_NAMES.index("backhand")).float().mean()
    assert 0.72 < float(frac_backhand) < 0.78
    assert set(t.family.unique().tolist()) == {FAMILY_NAMES.index("easy_forehand"), FAMILY_NAMES.index("backhand")}
    with pytest.raises(ValueError):
        FeedMix({"nonsense": 1.0}).vector()
    with pytest.raises(ValueError):
        FeedMix({"easy_forehand": 0.0}).vector()
