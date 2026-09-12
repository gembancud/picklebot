# Contact-quality telemetry

Added a continuous first-accepted-contact normal alignment, measured against the paddle broad-face normal. Front and back faces are equivalent. Missing/invalid measurements use -1; conditional TensorBoard alignment excludes those values. Existing face-contact counts retain their original collider-contact meaning. No new mastery threshold or physical classification is imposed.

TensorBoard now records `Picklebot/ContactQuality/Measured`, `Picklebot/ContactQuality/NormalAlignment`, and per-drill `ContactNormalAlignment`. No training is active, so these appear on a future run using a rebuilt worker.

Validation: three focused Unity tests passed. A full512-case replay preserved every old episode field (including reward) exactly, plus byte-identical first observations/actions and execution goals/landings. All333 accepted contacts have valid alignment;9 measure below0.5, a descriptive cutoff only. The known rightward graze measures0.0093; successful references measure0.9783 and1.0000. This does not make edge contacts illegal or change their physics.

The new runtime identity is d73e387e7f96b0238d823bec4cdf64cc15bba86ef76fbface3f437971f7ed34c. The evaluated model retains its original training source and checkpoint identity, explicitly recorded in the source manifest. The prior worker executable has not been rebuilt with this telemetry. Historical evidence stays unchanged.

Next: use pre-contact face-relative geometry to identify why the lateral feeds are missed; distinguish reaching a useful striking surface from merely touching the closed paddle collider. Any subsequent reward intervention requires a separate bounded experiment and all existing retention/target evaluations.

Evidence: `research/hierarchy-v1/contact-quality-telemetry-01` includes tests, scripts, complete replay and parity verification. Final acceptance seeds remain unused.
