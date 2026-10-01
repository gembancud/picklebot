"""Update current status after the verified reward-experiment launch."""
from pathlib import Path
import json

root = Path("F:/dev/picklebot")
base = root / "artifacts/hierarchy-v1/movement-progress-01"
archive = root / "docs/research/execution-v1-evidence/movement-progress-01"
manifest = json.loads((archive / "setup-launch/archive-manifest.json").read_text())
plan = json.loads((base / "plan.json").read_text())
assert not (base / "training/verification.json").exists()
assert not (base / "training/failure.json").exists()
assert plan["rewardChange"]["focusOnly"] and plan["initialStep"] == 1048609
marker = "<!-- movement-progress-running -->"
current = root / "docs/CURRENT_STATE.md"
goal = root / "docs/DRILL_MASTERY_GOAL.md"
summary = (
    "The matched **execution-movement-progress-01** experiment is running on **128 courts**, "
    "from the preserved 1,048,609-experience parent toward a fixed endpoint near 2.1 million. "
    "It keeps the same 6.25–25 cm axes mixture and PPO settings, adding at most 0.25 for measured "
    "forward ball travel after an accepted contact in focus drills. Familiar and prior-court rewards remain unchanged. "
    "All 50 Unity checks passed, the new worker build passed, and all eight workers started with exact registered trainer-state restoration."
)
next_work = (
    "Current work: " + summary + " The completed no-progress control remains preserved and unpromoted; "
    "its rightward returns and target following were insufficient. At the fixed endpoint, compare legal returns, "
    "contact, aiming and retention on the same narrow and wide development tests before extending. "
    "This is one matched training comparison, with no performance improvement established yet. "
    "Final acceptance seeds remain unused. [Running experiment](research/execution-v1-movement-progress.md) · "
    "[Completed control](research/execution-v1-axes-recovery-final.md)."
)
before = {path: path.read_bytes() for path in (current, goal)}
assert all(marker.encode() not in raw for raw in before.values())
prefix = (
    "# Active drill-mastery goal — movement reward experiment running\n\n" + marker + "\n\n" + summary + "\n\n"
    "The preceding run did not resolve lateral returns and reduced aiming accuracy. This branch starts from the common earlier checkpoint "
    "so that its fixed endpoint can be compared with the completed no-progress control. No new performance result or mastery acceptance is claimed.\n\n"
    "TensorBoard: `execution-movement-progress-01` on the existing port 6009. Steps before 1,048,609 are inherited history.\n\n"
    "[Running experiment](research/execution-v1-movement-progress.md) · [Control results](research/execution-v1-axes-recovery-final.md)\n\n---\n"
)
newline = "\r\n" if b"\r\n" in before[current] else "\n"
current.write_bytes(prefix.replace("\n", newline).encode() + before[current])
text = before[goal].decode("utf-8")
lines = text.splitlines(keepends=True)
indices = [i for i, line in enumerate(lines) if line.startswith("Current work:")]
assert len(indices) == 1
index = indices[0]
ending = "\r\n" if lines[index].endswith("\r\n") else "\n"
lines[index] = next_work + ending
goal.write_bytes("".join(lines).encode())
link_target = archive / "tensorboard-link.json"
assert not link_target.exists()
link_target.write_bytes((base / "tensorboard-link.json").read_bytes())
print("Updated current state, active goal, and TensorBoard reference")
