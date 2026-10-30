"""D-185: the H0 fine-tune task differs from Picklebot-Tracking-TennisLafan3-Huge-G1 only in the motion file, the source
shares and motion_global_root_pos std (O1); the parent task and every other tracking task keep std 0.3."""

import mjlab.tasks  # noqa: F401
from mjlab.tasks.registry import list_tasks, load_env_cfg, load_rl_cfg

import picklebot_mj.tasks as t


def test_one_objective_change_and_no_leak():
    a, b = load_env_cfg(t.TASK_TRACKING_TENNIS_LAFAN3_HUGE), load_env_cfg(t.TASK_TRACKING_TL3FF_ROOT1_HUGE)
    assert a.rewards["motion_global_root_pos"].params["std"] == 0.3
    assert b.rewards["motion_global_root_pos"].params["std"] == 1.0
    assert b.rewards["motion_global_root_pos"].weight == a.rewards["motion_global_root_pos"].weight == 0.5
    diff = sorted(k for k in a.rewards if a.rewards[k].params != b.rewards[k].params or a.rewards[k].weight != b.rewards[k].weight
                  or a.rewards[k].func is not b.rewards[k].func)
    assert diff == ["motion_global_root_pos"], diff
    assert set(a.rewards) == set(b.rewards) and list(a.terminations) == list(b.terminations)
    for k in a.terminations:
        assert a.terminations[k].params == b.terminations[k].params
    ca, cb = a.commands["motion"], b.commands["motion"]
    assert cb.source_shares == (0.5, 0.125, 0.125, 0.25) and ca.source_shares == (0.5, 0.25, 0.25)
    assert cb.motion_file.endswith("tennis-lafan3-ff.npz") and ca.motion_file.endswith("tennis-lafan3.npz")
    assert load_rl_cfg(t.TASK_TRACKING_TL3FF_ROOT1_HUGE) == load_rl_cfg(t.TASK_TRACKING_TENNIS_LAFAN3_HUGE)
    for task in list_tasks():
        if task.startswith("Picklebot-Tracking-") and task != t.TASK_TRACKING_TL3FF_ROOT1_HUGE:
            c = load_env_cfg(task)
            if "motion_global_root_pos" in c.rewards:
                assert c.rewards["motion_global_root_pos"].params["std"] == 0.3, task
