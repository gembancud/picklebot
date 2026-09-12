# Pre-contact diagnosis: a recipe-specific stall

Across seven consecutive windows of512 completed episodes per worker, the25cm training return rate stayed at37.5%,36.9%,38.7%,41.1%,38.0%,39.9%,37.6%. Right25cm success remained roughly1-8% with no sustained upward trend. The focus-wide average rose only from69.4% to71.0%. These are sampled-action training windows with a changing policy, approximate mixture balance and excluded final tails, not fixed-checkpoint evaluations or proof of capacity exhaustion. An unchanged longer run is not supported by an obvious continuing improvement trend.

Matched wide development feeds identify different failure mechanisms. All9 lost deep legal returns under target A and all11 under B still contacted the paddle but failed to cross the net. Some were edge-like contacts, some broad-face contacts, and A includes two DoubleHit faults. Rightward cases remained61/64 no-contact under A and64/64 under B. The two new rightward successes under A are seeds1109964 and1110284; this is not sufficient success or replicated evidence.

To investigate an apparent training/evaluation discrepancy, the final checkpoint ran512 already-used training feeds twice through maintained ML-Agents `--inference`: deterministic versus sampled actions, same goals/observations, no updates. Actor, critic, normalization and optimizer state remained unchanged. The bounded training-mode worker intentionally exhausts its512 allocation; the framework reports a restart-limit shutdown. The original postcheck expected a different log message; that failed postcheck and the correction are preserved. This was not resumed learning, acceptance testing, or a new candidate.

| Frozen probe | Focus legal /256 |25cm legal /64 |Right25cm |Deep25cm |
|---|---:|---:|---:|---:|
| Deterministic |195|32|1/16|12/17|
| Sampled |187|30|0/16|13/17|

Sampling does not reveal a reliable hidden rightward skill in this small check. The higher training-style aggregate is not evidence of an export failure:1670 matched full-observation/goal pairs across these recorded training feeds and the prior wide A/B tests had matching outcomes; maximum first-action difference was6.99e-7. These pairs include repeated observations and are not1670 independent trials. Feed distance and task/player frequencies differ between the broad wide battery and the training mix; compare stratified or matched cases, not their aggregate percentages.

Decision: keep the final checkpoint unpromoted, retain the common parent, and do not automatically extend this reward recipe. The next learning intervention must address sideways contact acquisition while preserving useful deep shots. More generic body-position shaping alone does not cover both failures. No conclusion about network capacity is established by this evidence. Final acceptance seeds remain unused; full drill mastery and final-model demonstrations remain incomplete.

Evidence and reproducible scripts: `research/hierarchy-v1/precontact-diagnosis-01`. Full raw decision streams are losslessly compressed; original artifacts remain on disk.
