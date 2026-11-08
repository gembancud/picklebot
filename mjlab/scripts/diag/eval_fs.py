"""scripts/stage2_eval.py with the footwork_specialist tasks registered (for tasks defined there, e.g. the loose-damping
reads). Usage: python scripts/diag/eval_fs.py <stage2_eval.py flags>"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mjlab.tasks  # noqa: F401,E402

import picklebot_mj.tasks.footwork_specialist  # noqa: F401,E402  (registers the tasks)
import stage2_eval  # noqa: E402

if __name__ == "__main__":
    stage2_eval.main()
