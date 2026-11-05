# Panel round 90 brief: the footwork phase is STOPPED (D-226); name the next phase inside the loop's authority, 2026-11-05

Read first:
- D-226 in docs/DECISIONS.md;
- round 89 in mjlab/results/footwork-review.md;
- D-169, D-179 and docs/PANEL.md;
- the frozen target (results/rally-target.md).

## Where we are

**Footwork phase STOPPED (D-226, 4 of 5).** The panel's recorded view:
- Best reachable P(5+) on this body, stack and read is about 0.45-0.55.
- 0.80 is not shown reachable. It needs h0 and h1 near 0.06 each, which means about 1.1 s to close 1.5 m. Every policy shown reads 1.26-1.41 s.
- It also needs near first-hand-off legal of about 0.97 (shown: 0.87-0.88).

**D-169 (the user):** loop to the target with the agent directing; a STOP moves the loop to the next phase. The user is briefed now with the asks below, without stopping the loop.

**Asks recorded for the user (their decision, not the loop's):**
- **A set start:** both robots on their spots when a rally starts. This changes the frozen read's premise.
- **A body or controller change:**
  - agile reference motion (a download);
  - an actuation review or a different body;
  - a from-scratch controller.

**Inside the loop's authority (no download, no change to the read, no new body):**
- **(a) A reported-only read of C under a set start** (architecture).
  - About 15 lines in pairs.step: hold the feeder ball until both robots are within 0.3 m of their spot and below 0.3 m/s, with a timeout.
  - A test, and about 0.4 GPU h of reads on dev 4220380-4220381.
  - It is not a score. It gives the user a measured number for their ask.
- **(b) A from-scratch low-level controller** (experiment design).
  - No model_15900 warm start and not through latent-07. Trained for acceleration and for reaching and hitting on the run, on data already on disk (LAFAN, the D-178 AMASS subset).
  - Several GPU days. Then a new rally stack is built on it.
- **(c) The joint fine-tune of base and residual** (motion's fallback). About 80 lines and about 8 GPU h.
- **(d) Partner credit on the first hand-off** (RL, experiment design). About 15 lines and about 4-6 GPU h. At best about +4 points.
- **(e) Random-practice hand-offs** (coach): off-groove balls in training.

**Resources:**
- The GPU is idle.
- Training seeds: next free 224.
- Dev seeds: next free 4220380 (4220340 held; 4220349-4220356 CONFIRM only).

## Questions

1. **Correction check on D-226.** Is anything misstated?
2. **The next phase.** Vote for one of (a)-(e), or (f) other, with its first run: the one change, parent, smoke and kill lines readable on windows that exist, a gate, seeds and GPU hours. Name the simpler option you rejected. Say which candidate has the largest expected gain toward 0.80 under the current read, and whether (a) should run first regardless, since it is cheap and informs the user.
3. **The user brief.** In two or three sentences, what should the user be told, and which ask should come first?
