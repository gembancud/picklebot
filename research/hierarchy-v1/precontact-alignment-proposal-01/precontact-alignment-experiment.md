# Proposed bounded experiment: pre-contact face alignment

Status: design frozen before implementation; no new training launched. The current worker binary has not been rebuilt. Preserve all previous control/forward-progress results.

## Evidence and hypothesis

The forward-progress intervention starts only after accepted contact. Rightward 50–100cm probes have no accepted contacts. At25cm, the latest endpoint has3/15 and1/15 contacts for targets A/B; a traced failed contact is an edge graze despite5.5m/s forward paddle speed. The body moves left during two rightward misses. The input path is connected. The old position reward only measures root translation, ignoring actual paddle orientation and joint correction.

Hypothesis: a small, reversible pre-contact signal based on actual ball-to-broad-face alignment can help the executor discover useful joint/body correction before contact. It does not prescribe a stroke, intercept point, movement direction or trajectory. It is not a new success criterion.

## Fixed intervention

Use the existing current-state ball centre, actual paddle pose and physical dimensions. Transform the ball into paddle-face coordinates. Use a conservative inner rectangle with half-width/half-height reduced by the actual rounded-corner radius. Its two approach planes are offset from each physical broad face by the ball radius. Let d be Euclidean distance to the closest such approach patch. This is a shaping heuristic, not collision clearance or a claim that other contacts are illegal.

Before accepted contact, potential Phi = -0.25*(1-exp(-d/0.5m)); after contact or at terminal, Phi=0. Shape each policy transition with F = 0.99*Phi(next)-Phi(previous). Account at actual20Hz decision boundaries, not240Hz physics ticks. Initialize from the first state without paying an initial reward; settle exactly once on terminal, including partial decision intervals. After contact, all subsequent Phi remain0. Preserve terminal flags and failure handling. Do not turn software failures into reward transitions.

The discounted sum of F must telescope to -Phi(initial) for every complete terminal path. This property, including early contact, failure, varying episode length and a partial final decision interval, is a mandatory mathematical test. Match the trainer gamma0.99 explicitly. A mismatch must reject configuration rather than silently claiming invariant shaping. For paired/multi-agent modes keep this option unsupported until a separate credit/clock contract is designed.

This follows potential-based shaping (Ng, Harada, Russell1999, https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf). The theorem concerns correctly specified discounted MDPs; it does not guarantee PPO optimization, finite-capacity retention or rapid learning. Our reward clock and terminal implementation require verification.

## Comparison and scope

Start from the preserved common parent at1,048,609 experiences, not the regressed forward-progress endpoint. Keep the6.25/12.5/18.75/25cm four-axis focus,25% familiar/25% prior/50% focus mixture, body/action/observation contract, placement reward and PPO settings. Enable shaping only on focus drills. Disable forward-progress and old position shaping; the sole reward change is pre-contact potential shaping. Fixed endpoint near2,097,152 experiences; no performance-picked checkpoint or automatic extension.

Retain all five development evaluations: narrow A/B/random and wide A/B, with shaping disabled. Compare contact quality, legal returns, aiming and retention against common parent and no-progress control. Original success measures and harder25–100cm probes remain unchanged. One seeded training comparison is not independent replication. Final acceptance seeds remain unused.

## Required implementation checks

- Pure geometry: both broad faces, rotation/translation invariance, invalid inputs, plane and tangential error.
- Decision-clock telescoping and terminal settlement, including the case of an episode ending between decisions.
- Default-off exact physical/action/reward replay parity; enabled rewards do not alter physics or observations.
- Focus-only scope; explicit rejection for incompatible paired runs or gamma settings.
- Export distinct base reward, shaping reward and potential telemetry; preserve historic counters and contact-normal quality.
- Rebuild workers, verify exact checkpoint restoration, run the bounded trial, evaluate before promotion.

The five recorded trajectories give descriptive minimum approach-patch distances of2.6/4.0cm for successful reference hits,6.9cm for the graze, and12.4/16.0cm for misses. These selected samples only check that the heuristic distinguishes this failure mechanism; they are not thresholds, feasibility proofs or optimization results.
