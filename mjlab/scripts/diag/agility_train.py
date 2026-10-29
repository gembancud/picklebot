"""`train` with the agility screen tasks registered. mjlab's `train` only sees tasks from the `mjlab.tasks` entry point
(picklebot_mj/tasks/__init__.py), which does not import picklebot_mj/tasks/agility.py; this wrapper imports it and then
runs mjlab's own train entry point unchanged (same arguments: TASK then the tyro flags).

Usage: python scripts/diag/agility_train.py Picklebot-Agility-Deadline-LamR2-G1 --env.scene.num-envs 4096 ...
"""

import sys

import mjlab.tasks  # noqa: F401  (the entry-point tasks)

import picklebot_mj.tasks.agility  # noqa: F401  (registers the agility tasks)
from mjlab.scripts.train import main

if __name__ == "__main__":
    sys.exit(main())
