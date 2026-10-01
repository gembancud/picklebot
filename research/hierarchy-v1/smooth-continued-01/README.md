# Bounded smooth-placement continuation

The completed 262,179-experience smooth policy retained legal returns but failed useful target following. First-decision diagnostics found correct target encodings, normalization and learned goal sensitivity. This run tests more experience with the same physical curriculum and reward recipe.

The maintained ML-Agents trainer resumes actor, critic, normalizers, Adam and global step from an isolated copy. `init_path` is removed so it cannot override resume. Checkpoint-manager paths are remapped to protect the completed parent. The actual trainer confirmed step 262,179; a separate installed-loader preflight matched all registered state exactly. Live simulation, unfinished rollouts and process RNG progression restart.

Target: 1,048,576 total experiences, eight workers × sixteen courts. The nearest retained checkpoint to 524,288 (within 8,192, lower step on a tie) and the final checkpoint are selected by step before observing their performance. All are evaluated on the same A/B/random development anchor. The midpoint describes learning progress; it does not replace the fixed final candidate. No automatic promotion or mastery acceptance.

The plan, launcher and resume proof are saved here. Runtime results remain under `artifacts/hierarchy-v1/smooth-continued-01`. Source/build identity is unchanged from the smooth-distance experiment. No final seeds are consumed. Wider positioning and varied rule-context coverage remain open requirements.
