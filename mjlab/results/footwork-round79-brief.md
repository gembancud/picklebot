# Panel round 79 brief: D-214 IdleRec on C reads KILL-NO-CLIMB at +360, 2026-11-05

Read first:
- D-214 and its result in docs/DECISIONS.md;
- round 78 in mjlab/results/footwork-review.md;
- mjlab/results/rec78-summary.txt, rec78-train-idlerec.jsonl and rec78-train.jsonl;
- the frozen target, mjlab/results/rally-target.md.

## Result

R = rally-d1s3idle: C model_32598 on Picklebot-Rally22b-FastMove-IdleRec-G1, LR 3e-5, training seed 211.
- **Smoke (seed 212) passed:** falls 1.992 against the line 4.157 (half-split 2.606 / 1.446).
- **Killed at +368 by KILL-NO-CLIMB.** The newly paid recovery value went from 0.5254 (iterations 0-60) to 0.5155 (300-360); the line needed +0.05.
- **Other kill lines passed:** falls 1.17; legal_return 0.907; mean rally length 4.07 vs C2's 4.22.
- No endpoint read was taken. C stays the parent.

## The record since C was promoted (D-211)

| run | change | verdict | what moved |
|---|---|---|---|
| C2 | recipe continued | COMPOUND fail | -1.22 points; recovery worse |
| K | pair_rally_cap 5 | LEVER fail | h0 / h1 down about 1.2 points vs C; ready 0.211; long-rally endings up |
| d1b | Fast4 teacher | TEACHER-NOT-READY | court-scale speed the same as fw1b-S |
| R | IdleRec | KILL-NO-CLIMB | recovery-while-parked value flat |

- P(5+) is 0.41 against 0.80; feeder legal 0.64 against M1's 85 %.
- Hazards on C: h0 0.37, h1 0.27, later about 0.02 and below.
- R3 is not yet read on C with the target's instrument (the h5f court read). On the pairs read with falls / (falls + envs) it is about 5 %.

**Round 78's findings:**
- The court-scale movement limit is acceleration (about 1.0-1.5 m/s^2 effective) and an earlier start, not top speed.
- The feeder ball is a scramble ball: 52 % launch with the robot more than 1.2 m off its spot, legal 0.60.
- The first return is the STATE ball.

**Queued:**
- pre-bounce approach_far (motion; about 4 lines, with a smoke assert);
- restart-state starts (coach; new code);
- the cap on a share of courts (about 20 lines).

The GPU is idle. Training seeds next 213; dev next free 4220366 (4220365 reserved for the R3 court read; 4220349-4220356 reserved unread for a CONFIRM).

## Questions

1. **Correction check.**
   - Is KILL-NO-CLIMB valid as pre-registered?
   - Was the climb line the right kill for a parent whose recovery value already starts at 0.53?
   - Anything misstated?
2. **What we learned.** Four levers on C have failed or not moved. Is there a common cause (for example, C sits on a plateau the LR 3e-5 recipe cannot leave)? Is the opening exchange limited by state, by reach, or by something the task does not train?
3. **Next step.** Vote with coded lines, kill checks and seeds:
   - **(i)** pre-bounce approach_far on C (motion's lines from round 78);
   - **(ii)** restart-state starts;
   - **(iii)** read R3 properly on C (h5f) and fix measurement before more levers;
   - **(iv)** STOP. Under D-169 a STOP moves to the next phase (name it: for example 2v2 / self-play, or a different target route) rather than ending the climb;
   - **(v)** other.
