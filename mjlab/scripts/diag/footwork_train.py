"""`train` with the footwork specialist tasks registered (tasks/footwork_specialist.py, which also registers the agility
tasks), then mjlab's own train entry point unchanged. Launched by agility_train_run.sh with
PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py.
"""

import sys

import mjlab.tasks  # noqa: F401  (the entry-point tasks)

import picklebot_mj.tasks.footwork_specialist  # noqa: F401  (registers the footwork tasks)
from mjlab.scripts.train import main

if __name__ == "__main__":
    sys.exit(main())
