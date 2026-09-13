# Randomized execution scaling experiment

Run: `execution-randomized-scale-01`. Started 13 September 2026.

- Maintained ML-Agents PPO; one execution policy, two hidden layers of256.
- Parent: right-retention endpoint2097180. Actor and critic widened by duplicate hidden units with complementary outgoing weights. Preserved normalizers and action distribution parameters; fresh Adam, new phase counter0. On2816 recorded observations plus4096 numerical probes, maximum action-mean/value error was below0.000009. Installed initialization loader verified. Earlier128 checkpoint remains intact.
- Budget:8million additional experiences; checkpoints every1million, keep10. Eight executable workers,16 courts each.12-hour failure timeout, no automatic extension or promotion.
- Same reward definitions and motor constraints.50% episode starts: random axes movement, nominal reset displacement2.5cm–1m, varied feed difficulty up to.5, flight-timing fraction0–.25, start-position fraction0–.15.25%: prior court movement, continuous range.005–.1 plus feed variation.25%: familiar serves/required-bounce receives/rally feeds; serves preserved, half non-serve familiar cycles retain anchor settings. Episode shares differ from decision/gradient shares.
- Fixed-ball serving stays fixed. No scripted actions, added shaping, changed collider or physics timestep. Air-feed labels are not proof of volley contact; assess actual contact mode.
- Training seeds2000000–2983039; development4000000–4099999 reserved separately. First512 training seeds used by the frozen probe and then training. Existing final-test seeds remain forbidden and unconsumed.
-17/17 Unity tests passed, including768 distinct non-familiar physical reset observations across separate training/development samples, reproducibility and old curriculum checks. This validates reset construction, not universal biomechanical reachability.
- Frozen executable probe completed512 episodes, including256 distinct focus distances, with no shaping. Its bounded seed exhaustion is expected; it is not a training failure.
- Automatic frozen evaluations: initial model and approximately each1m checkpoint, original narrowA/B/random and wideA/B plus randomized512-seedA/B. Actual snapshot steps/hashes and all raw failures retained. Repeated development evaluation is not final acceptance. Evaluation process failure must be inspected separately from training.

This pilot changes capacity, reset distribution, duration and optimizer initialization together. Improvement would support this combined recipe; it would not isolate network size as the cause. The prior mixed run learned rightward returns but regressed narrow legality from234/235 to164/167 out of256; it was not promoted.

Live artifacts: `artifacts/hierarchy-v1/randomized-scale-01/`. TensorBoard: http://127.0.0.1:6009/ (select the training run, not its `-probe` companion).
