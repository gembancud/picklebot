"""D-235 diagnostic: stage2_eval on the launcher-court rally task (registered in footwork_specialist)."""
import sys

sys.path.insert(0, "scripts")
import picklebot_mj.tasks.footwork_specialist  # noqa: E402,F401
import stage2_eval  # noqa: E402

if __name__ == "__main__":
    stage2_eval.main()
