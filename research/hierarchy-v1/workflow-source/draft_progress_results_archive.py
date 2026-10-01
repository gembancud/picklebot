"""Derive the next result archiver from the preserved axes archive implementation."""
from pathlib import Path
import ast
import hashlib

here = Path(__file__).resolve().parent
source = here / "archive_axes_results.py"
assert hashlib.sha256(source.read_bytes()).hexdigest() == "3933f72f962ba7062d529a7a210aab415b8b306b0fc67ac418b87cc26582b67e"
text = source.read_text()
text = text.replace("axes-recovery-01", "movement-progress-01")
text = text.replace("execution-v1-axes-recovery-final.md", "execution-v1-movement-progress-final.md")
text = text.replace('FINAL = "ExecutionV1AxesRecoveryFinal01"', 'CONTROL = "ExecutionV1AxesRecoveryFinal01"\nFINAL = "ExecutionV1MovementProgressFinal01"')
text = text.replace("MODELS = (INITIAL, PARENT, FINAL)", "MODELS = (INITIAL, PARENT, CONTROL, FINAL)")
text = text.replace('labels = {INITIAL: "Initializer", PARENT: "Previous endpoint", FINAL: "Axes endpoint"}',
    'labels = {INITIAL: "Initializer", PARENT: "Common parent", CONTROL: "No-progress control", FINAL: "Progress reward endpoint"}')
text = text.replace("for baseline in (INITIAL, PARENT):", "for baseline in (INITIAL, PARENT, CONTROL):")
text = text.replace("complete_axes_recovery_final_assessment", "complete_movement_progress_final_assessment")
text = text.replace("complete_axes_results_archive", "complete_movement_progress_results_archive")
for before, after in (("prepare_axes_evaluation.py", "prepare_movement_progress_evaluation.py"),
    ("analyze_axes_recovery.py", "analyze_movement_progress.py"), ("run_axes_recovery.py", "run_movement_progress.py"),
    ("prepare_axes_recovery.py", "prepare_movement_progress.py")):
    text = text.replace(before, after)
start = text.index('    require((archive / "setup/archive-manifest.json")')
end = text.index('    analysis, plan, selected, training =', start)
text = text[:start] + '''    prior = archive / "setup-launch/archive-manifest.json"
    require(prior.is_file(), "Verified setup/launch archive is missing")
    for item in read(prior)["files"]:
        require(sha(inside(root, item["path"])) == item["sha256"], "Existing setup/launch archive changed")
''' + text[end:]
text = text.replace('(archive / "setup", archive / "launch", workflow)', '(archive / "setup-launch", workflow)')
text = text.replace("# Graded movement continuation", "# Forward-flight reward comparison")
text = text.replace("# Axes final assessment workflow", "# Forward-flight reward assessment workflow")
text = text.replace("Archive completed axes results", "Archive completed forward-flight reward results")
text = text.replace(
    "Actor, critic, normalization, Adam and global step resumed through ML-Agents. Body controls, observations, PPO settings and smooth-distance reward were unchanged.",
    "Actor, critic, normalization, Adam and global step resumed through ML-Agents from the common parent. The sole training change added up to 0.25 for measured post-contact forward progress in focus episodes. Familiar and prior-court rewards, body controls, observations, PPO and smooth placement reward were unchanged.")
text = text.replace("Both baselines retain their original source identities.", "All three comparison models retain their original source identities. The completed axes run supplies the no-progress control; this is one training lineage per condition, not replicated causal evidence. The added reward is disabled for all new frozen evaluations.")
text = text.replace("Passed default-reset tests and exact paired", "Fifty passed reward/default-reset checks and exact paired")
text = text.replace("Existing setup/launch archives remain unchanged.", "The existing setup-launch archive remains unchanged.")
ast.parse(text)
output = here / "archive_movement_progress_results.py"
assert not output.exists()
with output.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(text)
print(hashlib.sha256(output.read_bytes()).hexdigest())
