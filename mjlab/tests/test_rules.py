"""Rally rules, mirroring the rally-level cases of Unity DoublesRulesTests (same names in comments)."""

import torch

from picklebot_mj import court
from picklebot_mj.rules import Fault, Phase, RallyRules, in_bounds, in_kitchen_zone

T, F = torch.tensor([True]), torch.tensor([False])
HL, HW, K = court.HALF_LENGTH, court.HALF_WIDTH, court.KITCHEN_DEPTH


def p(x, y):
    return torch.tensor([[x, y]])


def pl(i):
    return torch.tensor([i])


def served(server=0, right=True):
    r = RallyRules(1)
    r.begin_rally(torch.tensor([0]), pl(server), torch.tensor([right]))
    r.fixed_ball_serve(T, pl(server), T)
    return r


def outside(r, player):
    r.feet(T, pl(player), F, T, T)


def legal_serve_landing(server_right=True):
    # Near server on its right (-y) serves diagonally to the far right box (+y), beyond the kitchen.
    return p(4.0, 1.5 if server_right else -1.5)


def test_serve_foot_fault():  # ServeFootFault
    r = RallyRules(1)
    r.begin_rally(torch.tensor([0]), pl(0), T)
    r.fixed_ball_serve(T, pl(0), F)
    assert r.fault.item() == Fault.SERVE_FOOT and r.winner.item() == 1


def test_serve_cannot_land_on_kitchen_line():  # ServeCannotLandOnKitchenLine
    r = served()
    r.bounce(T, p(K, 1.5))
    assert r.fault.item() == Fault.SERVE_LANDING and r.winner.item() == 1


def test_serve_must_be_diagonal():  # ServeMustBeDiagonal
    r = served()
    r.bounce(T, p(4.0, -1.5))
    assert r.fault.item() == Fault.SERVE_LANDING
    r = served(right=False)
    r.bounce(T, legal_serve_landing(server_right=False))
    assert not r.dead.item()


def test_serve_may_touch_centre_line():  # ServeMayTouchCentreLine
    r = served()
    r.bounce(T, p(4.0, 0.0))
    assert not r.dead.item() and r.bounced.item()


def test_wrong_partner_cannot_return_serve():  # WrongPartnerCannotReturnServe
    r = served()
    r.bounce(T, legal_serve_landing())
    receiver = r.designated_receiver.item()
    r.hit(T, pl(receiver ^ 1))
    assert r.fault.item() == Fault.WRONG_RECEIVER and r.winner.item() == 0


def test_serve_cannot_be_volleyed():  # ServeCannotBeVolleyed
    r = served()
    outside(r, r.designated_receiver.item())
    r.hit(T, r.designated_receiver)
    assert r.fault.item() == Fault.EARLY_VOLLEY and r.winner.item() == 0


def test_serving_team_must_let_return_bounce():  # ServingTeamMustLetReturnBounce
    r = served()
    r.bounce(T, legal_serve_landing())
    r.hit(T, r.designated_receiver)
    assert r.phase.item() == Phase.RETURN_FLIGHT
    outside(r, 1)
    r.hit(T, pl(1))  # serving team volleys the return
    assert r.fault.item() == Fault.EARLY_VOLLEY and r.winner.item() == 1


def rally_ready():
    """Serve, return and third shot all bounced: now in RALLY with the far team to play."""
    r = served()
    r.bounce(T, legal_serve_landing())
    r.hit(T, r.designated_receiver)
    r.bounce(T, p(-4.0, 0.5))
    r.hit(T, pl(1))
    assert r.phase.item() == Phase.RALLY and r.expected_team.item() == 1
    return r


def test_either_partner_may_hit_after_serve_return():  # EitherPartnerMayHitAfterServeReturn
    r = rally_ready()
    outside(r, 3)
    r.hit(T, pl(3))  # legal volley in the rally
    assert not r.dead.item() and r.expected_team.item() == 0


def test_teammate_cannot_make_second_hit():  # TeammateCannotMakeSecondHit
    r = rally_ready()
    r.bounce(T, p(4.0, 0.0))
    r.hit(T, pl(2))
    r.hit(T, pl(3))
    assert r.fault.item() == Fault.DOUBLE_HIT and r.winner.item() == 0


def test_kitchen_volley_is_fault():  # KitchenVolleyIsFault
    r = rally_ready()
    r.feet(T, pl(2), T, F, F)
    r.hit(T, pl(2))
    assert r.fault.item() == Fault.KITCHEN_VOLLEY and r.winner.item() == 0


def test_kitchen_groundstroke_is_legal():  # KitchenGroundstrokeIsLegal
    r = rally_ready()
    r.feet(T, pl(2), T, F, F)
    r.bounce(T, p(1.0, 0.0))
    r.hit(T, pl(2))
    assert not r.dead.item()


def test_both_feet_must_reestablish_before_volley():  # BothFeetMustReestablishBeforeVolley
    r = rally_ready()
    r.feet(T, pl(2), T, F, F)
    r.feet(T, pl(2), F, F, F)  # left the kitchen, but both feet not yet outside
    r.hit(T, pl(2))
    assert r.fault.item() == Fault.KITCHEN_VOLLEY


def test_volley_momentum_into_kitchen_is_fault():  # LateMomentumOverridesUnresolvedRally (live part)
    r = rally_ready()
    outside(r, 2)
    r.feet(T, pl(2), F, T, F)  # outside but not yet balanced
    r.hit(T, pl(2))  # legal volley
    r.feet(T, pl(2), T, F, F)  # momentum carries into the kitchen
    assert r.fault.item() == Fault.KITCHEN_MOMENTUM and r.winner.item() == 0


def test_second_bounce_loses_for_receiver():  # SecondBounceLosesForReceiver
    r = rally_ready()
    r.bounce(T, p(4.0, 0.0))
    r.bounce(T, p(5.0, 0.0))
    assert r.fault.item() == Fault.SECOND_BOUNCE and r.winner.item() == 0


def test_out_after_legal_bounce_still_loses_for_receiver():  # OutAfterLegalBounceStillLosesForReceiver
    r = rally_ready()
    r.bounce(T, p(4.0, 0.0))
    r.bounce(T, p(HL + 1.0, 0.0))
    assert r.fault.item() == Fault.OUT and r.winner.item() == 0


def test_out_before_bounce_loses_for_hitter():
    r = rally_ready()  # team 0 hit last
    r.bounce(T, p(HL + 0.5, 0.0))
    assert r.fault.item() == Fault.OUT and r.winner.item() == 1


def test_wrong_side_loses_for_hitter():
    r = rally_ready()
    r.bounce(T, p(-3.0, 0.0))  # team 0's shot lands on its own side (did not cross)
    assert r.fault.item() == Fault.WRONG_SIDE and r.winner.item() == 1


def test_net_touch_ball_is_not_automatically_fault():  # NetTouchBallIsNotAutomaticallyFault
    r = rally_ready()
    # The ball touching the net has no rules call; a legal landing keeps the rally alive.
    r.bounce(T, p(0.5, 0.0))
    assert not r.dead.item()


def test_body_contact_loses_even_for_outward_ball():  # BodyContactLosesEvenForAnOutwardBall
    r = rally_ready()
    r.body_contact(T, pl(3))
    assert r.fault.item() == Fault.BODY_CONTACT and r.winner.item() == 0


def test_boundary_lines_are_in():  # BoundaryLinesAreIn
    assert in_bounds(p(HL, HW)).item() and in_bounds(p(-HL, -HW)).item()
    assert not in_bounds(p(HL + 1e-4, 0)).item()
    assert in_kitchen_zone(p(K, 0)).item() and not in_kitchen_zone(p(K + 1e-4, 0)).item()


def test_post_before_bounce_loses_for_hitter():  # PostBeforeBounceLosesForHitter
    r = rally_ready()
    r.permanent_object(T)
    assert r.fault.item() == Fault.PERMANENT_OBJECT and r.winner.item() == 1


def test_post_after_legal_bounce_loses_for_receiver():  # PostAfterLegalBounceLosesForReceiver
    r = rally_ready()
    r.bounce(T, p(4.0, 0.0))
    r.permanent_object(T)
    assert r.fault.item() == Fault.PERMANENT_OBJECT and r.winner.item() == 0


def test_first_fault_sticks():  # DuplicateResolutionDoesNotScoreTwice (rally level)
    r = rally_ready()
    r.bounce(T, p(HL + 1, 0))
    r.body_contact(T, pl(0))
    assert r.fault.item() == Fault.OUT and r.winner.item() == 1


def test_drill_feed_context_and_batching():
    # 3 envs fed by far player 2 in RALLY context; near player 0 responds differently.
    r = RallyRules(3)
    ids = torch.arange(3)
    r.begin_from_feed(ids, torch.tensor([2, 2, 2]))
    r.feet(torch.ones(3, dtype=torch.bool), torch.zeros(3, dtype=torch.long),
           torch.tensor([False, True, False]), torch.tensor([True, False, True]), torch.ones(3, dtype=torch.bool))
    r.bounce(torch.tensor([True, False, False]), torch.tensor([[-4.0, 0.0]] * 3))
    r.hit(torch.ones(3, dtype=torch.bool), torch.zeros(3, dtype=torch.long))  # env0 groundstroke, env1 kitchen volley, env2 volley
    assert r.dead.tolist() == [False, True, False]
    assert r.fault[1].item() == Fault.KITCHEN_VOLLEY
    r.bounce(torch.tensor([True, False, True]), torch.tensor([[4.0, 1.0], [0, 0], [HL + 0.2, 0.0]]))
    assert r.dead.tolist() == [False, True, True] and r.fault[2].item() == Fault.OUT and r.winner[2].item() == 1
    # Must-bounce feed (serve-receive context): a volley is an early-volley fault.
    r2 = RallyRules(1)
    r2.begin_from_feed(torch.tensor([0]), pl(2), must_bounce=True)
    r2.hit(T, pl(0))
    assert r2.fault.item() == Fault.EARLY_VOLLEY
