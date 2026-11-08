# Panel round 110 brief: the user's footwork target (D-251) - freeze the call-and-set test, 2026-11-09

Read first: D-251 at the end of docs/DECISIONS.md (the user's words and the target); D-191, D-197, D-221, D-222, D-226, D-228, D-229 (earlier footwork work: first step stuck near 1.34 s under deadlines, a first-step bonus and effort x2); results/agility249-summary.txt (Q, D-249 and D-248 identical on the Measure60 drill); docs/PANEL.md. Code: mjlab/picklebot_mj/tasks/move_drill.py (MoveDrill, ready_mask, READY_*), deadline_drill.py, footwork_specialist.py (FootworkDrill, first-step instrument, with_strong_legs / with_loose_legs), body_speed.py, return_stand.py (shadow-swing / ghost feeds: swing_prob, swing_families), scripts/diag/footwork_eval.py, picklebot_mj/bodyspeed_rule.py.

## The user's direction (D-251)

Focus moves from the rally target to footwork: "the best footwork that it can achieve with the best athleticism we can unlock in its body", digital only (no hardware limits), proven by a hill-climbable metric like the 80 % rally target. In the user's words: "agility and explosiveness mixed with footwork thats also able to do ready positions in certain directions [...] sprint then split step to prepare for a stroke". D-250 was stopped by the user.

**The target as recorded:** one rep = one coach call: a ghost ball at a spot on the robot's half, forehand or backhand side, arriving at a set time. Pass = (1) starts at once, (2) covers the ground in time, (3) SET before arrival (decelerated, both feet down, balanced: the split step), (4) READY on the called side (paddle up, prepared on that side, the ghost ball within paddle reach at its arrival time), (5) no fall. Calls chain (wide forehand, wide backhand, deep, short), about a third before recovery completes. Deadline = reaction allowance + distance / pace (pace from athletic human court movement scaled to size: about 1.3 s for 2 m, 1.7 s for 3 m). Headline: share of reps passed on frozen dev seeds; target 80 %. Swing not required (recorded only). Subject: the robot that plays (Q, rally-d1s3cap8hr2 model_36793), unless you argue otherwise.

## Facts

- Q on the Measure60 drill (3-5 m spots, untimed): first step to 1.5 m 1.36 s (left / back 1.34 s), sustained 1.69 m/s, peak about 2.0 m/s, arrival 0.986, falls 3.55 per 1,000 env-s.
- Human court-foot speed from the PPA video: p90 about 2.9 m/s, p99 about 4.4 m/s; the pros' mean move speed 1.0-1.2 m/s; G1 hip height 0.69 m vs about 0.95 m (Froude time x1.17, speed x0.85).
- A damping premise read is running (Q with leg / waist / ankle damping halved, zero-shot; scripts/diag/damp249.sh) - its result is a lever input, not part of the test.

## Questions

1. **Correction check** on the D-250 stop and the D-251 record.
2. **Freeze the test (numbers, before any baseline):** call distribution (distance range, directions, deep / short, side), chaining and the early-call share, reaction allowance and pace (or a ladder), SET definition (speed, contacts, hold, timing window), READY definition (paddle pose on the called side), REACH definition, falls, rep count, seeds (a dev block for development reads and a separate unread block for target reads), the pass bar and its interval rule.
3. **Implementation form:** smallest build on the existing drills; what gets unit-tested; how the baseline on Q is read.
4. **Lever order** after the baseline (damping, facing freedom, action range, effort, base retrain on the drill, agile reference, length / size): the first one and why.

Under 300 words.
