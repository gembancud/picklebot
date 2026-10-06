"""Stage 5 specialist teacher tasks (D-042): one skill each, same inputs as the drill and footwork tasks."""


def test_teacher_tasks():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.feeds import FAMILY_NAMES, STAGE4_FAMILIES
    from picklebot_mj.tasks import TASK_DRILL_MOVE, TASK_FOOTWORK_WIDE, TASK_TEACHER_HIT, TASK_TEACHER_MOVE

    mv, hit, d1, f2 = (load_env_cfg(t) for t in (TASK_TEACHER_MOVE, TASK_TEACHER_HIT, TASK_DRILL_MOVE,
                                                  TASK_FOOTWORK_WIDE))
    assert mv.actions["ball"].move_prob == 1.0 and mv.actions["ball"].move_sector_weights is None
    assert set(mv.rewards) == set(d1.rewards)
    assert hit.actions["ball"].move_prob == 0.0 and set(hit.rewards) == set(f2.rewards)
    w = dict(zip(FAMILY_NAMES, hit.actions["ball"].feed_mix.vector()))
    assert {f for f, x in w.items() if x > 0} == set(STAGE4_FAMILIES) | {"reach_forehand"}
    for g in ("actor", "critic"):  # warm-start compatible with both parents
        names = list(f2.observations[g].terms)
        assert list(mv.observations[g].terms) == names and list(hit.observations[g].terms) == names


def test_backspin_follow_up_only_changes_the_mix():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.feeds import FAMILY_NAMES
    from picklebot_mj.tasks import TASK_TEACHER_HIT, TASK_TEACHER_HIT_BACKSPIN

    a, b = load_env_cfg(TASK_TEACHER_HIT), load_env_cfg(TASK_TEACHER_HIT_BACKSPIN)
    wa = dict(zip(FAMILY_NAMES, a.actions["ball"].feed_mix.vector()))
    wb = dict(zip(FAMILY_NAMES, b.actions["ball"].feed_mix.vector()))
    assert wb["backspin"] == 3.0 and all(wb[f] == wa[f] for f in FAMILY_NAMES if f != "backspin")
    assert set(a.rewards) == set(b.rewards) and all(a.rewards[k].weight == b.rewards[k].weight for k in a.rewards)
