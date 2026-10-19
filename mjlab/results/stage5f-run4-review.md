# Stage 5F run 4 review (reviewer round 7, 2026-10-20)

**Trigger.**
- Run 3 (clean drill v2 PPO, warm-up fixed) raised drill v2 p to 0.830, but was killed by the stage rules: court main 67.7 % (< 76.8 %) and falls 7.5 % (> 7.4 %).
- With run 2's early kill that makes 2 kills in a row, so the loop stopped.
- The user picked "mix court feeds in" and asked whether that was a group consensus. It was not (it was the agent's proposal), so the user asked for this review.

**Brief.**
- Options A-E:
  - A: per-robot task mixture with the Court-Rally task's own settings;
  - B: court feeds on drill v2 terms;
  - C: KL or behaviour cloning toward the parent;
  - D: wider drill v2 starts;
  - E: other.
- The brief also gave the config diff between the two tasks: the court task trains with a stance hint, a curriculum, a 0.5 s refeed and no ball noise.

Five reviewers answered independently: RL fine-tuning, motion prior, coach, experiment design, architecture.

## Verdicts

| Reviewer | Option | Court share | Parent |
|---|---|---|---|
| 1. RL fine-tuning | B (rehearsal) | 50 % of feeds | start point |
| 2. Motion prior | B | 40 % of feeds | start point |
| 3. Coach | B, interleaved per episode | 40 % court / 60 % v2 | start point |
| 4. Experiment design | A, per robot, the court task's own settings | 50 % of robots | start point |
| 5. Architecture | B, per feed | 40 % of feeds | start point |

**Majority (4 of 5): B.**
- **What it is:** court-wide feeds mixed in on drill v2 terms. Court families with zone validity, the court anchor (75 % court-anchored, 25 % pelvis), the fixed rally recovery spot, no hint, no planner on court feeds, ball noise on, 0.2 s refeed.
- **Why:**
  - it trains what the court evaluation measures (no hint);
  - it reuses existing code (about 40 lines);
  - A's hint is a privileged input the evaluation never shows.

## Unanimous points

- **Parent:** the start point (`s5d-01-rally/model_1800`). Run 3 was killed, and a killed run is never extended or promoted. Run 3 becomes the paired comparator.
- **The ready-position reward comes after retention is fixed.** Adding it to a forgetting policy would confound both effects.
- **The stage kill rules are unchanged.** The early check gains a court-main item (256 envs, dev seed), which only tightens the rules: kill if more than 5 points below the parent on the same protocol (reviewer 1: 3 points).
- **Fallback if court is still forgotten: C**, a KL or behaviour-cloning pull toward the parent at a fixed weight. With court feeds now in the batch, the pull finally acts on court states.
- **Nothing else runs on the GPU** during training. Report the gains honestly against run 3 and the start point.

## Other findings

- **The pre-registered exit has fired** (reviewer 4). D-113 lists "2 kills in a row" as an exit trigger, the switch to the goal-conditioned controller, as well as a stop-and-ask. Continuing needs a decision entry that records the trigger, the user's choice and why. Run 2 stays counted as a kill even though a tooling bug caused it. The counters are not reset, and a third kill stops the loop again.
- **Implementation risks for B** (reviewer 5):
  - `_refeed` recomputes the feed for every env and restores the ones that did not fire. The new court-feed flag must be restored too; this bug class has happened twice before (D-066, D-092).
  - The drill v2 no-two-extremes state must advance only on v2 feeds.
  - A separate generator, so share 0 reproduces run 3 exactly.
  - Court feeds keep the planner off.
  - Tests: share-0 equivalence, mix ratios, refeed restoration, evaluation-config hashes unchanged, a 20-iteration smoke run at 12,288 envs.
- **No ratio sweeps** (reviewer 4). The share is fixed before launch, and any change is its own pre-registered run.
- **Report court-drill results by family and start sector**, and the residual norm and prior NLL on court states, to test the motion reviewer's reading that the residual drifts off the prior on court states (reviewer 2).
- **Next runs:**
  - if court and drill v2 both pass: the ready-position reward on the same mix;
  - if court holds but p < 0.80: a smaller court share;
  - if court still fails: B plus the KL pull-back.

  After that comes a run aimed at falls.
