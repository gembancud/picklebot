# Stage 1 — court bounce with native MuJoCo contacts: not viable

Date: 2026-10-02. Branch `feat/mjlab-pivot`.
Scripts: `mjlab/scripts/bounce_sweep.py`, `calibrate_court_bounce.py`. Tests: `mjlab/tests/test_bounce.py`.

## Target
Official drop test (PHASE1B spec §5): release from 1.981 m (ball-bottom datum), first rebound apex (ball top) 0.762–0.864 m. That implies a normal COR of about 0.62–0.66 including drag. No acrylic-court reference exists yet, so the official band is a provisional bound only.

## What was tried
1. **Sweep** of 552 configurations: dt ∈ {5, 2, 1, 0.5} ms; solref time constant 2/4/8 × dt; two solimp settings; damping ratio 0.05–0.60. Implicitfast integrator, pyramidal cone, aerodynamics on, ball contacts via explicit pairs.
   - Time constants of 4× and 8× dt were non-monotonic and chaotic.
   - Low damping at 2× dt gained energy (rebounds of 20–70 m from a 2 m drop).
   - The only well-behaved-looking regime was 2× dt with moderate damping.
2. **Calibration**: bisection of the damping ratio per dt hit the band centre exactly: 0.813 m, COR 0.637 at dt 5/2/1 ms. Penetration was 12.4 / 4.3 / 1.4 mm.
3. **Validation against other drop heights failed.** This exposed the real behaviour below.

## Finding: restitution depends on impact phase, not on material parameters
The contact resolves in about one solver step, and MuJoCo's soft-contact reference acceleration includes a position (spring) term. The rebound speed therefore scales with how deep the ball happens to be when contact is first detected. That depth depends on where the impact falls between timesteps.

Shifting the drop height over 1.95–2.05 m (same parameters):

| dt | COR range | Depth at first detection |
|---|---|---|
| 2 ms | 0.10 – 1.64 | 0.3 – 11.8 mm, COR linear in depth |
| 1 ms | 0.11 – 2.88 | 0.1 – 5.8 mm, COR linear in depth |

The single calibrated drop only matched one phase. COR > 1 means energy gain.

Finer timesteps with multi-step contacts (drop height shifted 0–2 cm):

| dt | Time constant | Damping ratio | COR spread |
|---|---|---|---|
| 0.5 ms | 2 ms | 0.25 | 0.32 – 0.68 |
| 0.25 ms | 2 ms | 0.15 | 0.54 – 0.73 |
| 0.1 ms | 1 ms | 0.15 | 0.57 – 0.68 |

Even at 0.1 ms (50× finer than mjlab's 5 ms G1 setting), COR still varies by about ±0.05 with impact phase. Simulating the whole scene at 0.1–0.25 ms would cost roughly 20–50× throughput, giving up the Stage 0 gain.

Other results in the same suite still pass at dt ≤ 2 ms:
- impact timing;
- angled bounces losing energy and gaining topspin;
- backspin checking up;
- the net stopping a 12 m/s ball;
- clearing the net.

At 5 ms a 12 m/s ball **tunnels through the net** (strict xfail).

## Conclusion
MuJoCo has no velocity-level restitution coefficient. For a 24 g ball with millisecond contacts, native soft contacts cannot give a consistent, physical bounce at any affordable timestep. The ball's bounce physics needs a different design. Options for the user decision are in `docs/MJLAB_PIVOT.md` → Open questions.
