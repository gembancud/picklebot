# Graded four-direction recovery

The wide diagnostic found little transfer beyond 25 cm. The next experiment changes focus feeds from 2.5–10 cm lateral offsets to **6.25 / 12.5 / 18.75 / 25 cm** offsets left, right, shallow and deep. Existing **25% familiar / 25% prior-court / 50% focus** practice and interleaving remain intact.

`execution-axes-recovery-01` resumed the full actor, critic, normalization, Adam and step state at **1,048,609 experiences**, on **8 workers × 16 courts**. Its fixed endpoint is approximately **2,097,152 total experiences**. PPO settings, body controls, goal inputs and smooth landing reward are unchanged. Process RNG and live episodes restart; this is not bitwise trajectory continuation.

All **14 Unity checks passed**, including the complete recorded default curriculum and new four-direction reset construction. Two test compilation issues were corrected before execution: an unnecessary JSON-library dependency and the installed Unity SceneHandle type. The test runner's sole analytics-define edit was restored to the prior exact bytes before building. A new standalone worker was built and source/build identities verified.

Training is running in this snapshot; improvement has not been evaluated. The mandatory frozen endpoint will replay the narrow 256-reset A/B/random battery and wide 512-reset A/B battery. Compare actual legal returns, target outcomes, root movement and contact by skill, direction and distance against the initializer and immediate parent. The 50–100 cm feeds remain transfer probes. No automatic extension, model promotion or mastery acceptance.

[Frozen plan](execution-v1-evidence/axes-recovery-01/setup/plan.json) · [Tests](execution-v1-evidence/axes-recovery-01/setup/integration-tests.xml) · [Setup evidence](execution-v1-evidence/axes-recovery-01/setup/archive-manifest.json) · [Previous movement results](execution-v1-wide-movement.md) · [Recordings](execution-v1-wide-movement-review.md)
