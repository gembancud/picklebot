# The review panel (from D-115, 2026-10-20)

The user has handed run-level and plan-level decisions to a standing panel of five independent reviewers. The panel decides by consensus. The agent carries out the decision and reports it. The aim is the hill-climb to a robot that can learn from self-play.

## Members (each reviews independently and does not see the others' answers)

1. **RL:** fine-tuning, forgetting, multi-agent and self-play methods.
2. **Motion:** the motion prior, balance, falls, style.
3. **Coach:** pickleball and practice design.
4. **Experiment design:** pre-registration, honest reporting, the gates.
5. **Architecture:** code, compute, implementation risk.

## When the panel is asked

- Before each run: what the one change is, its parent, and its kill checks.
- After any kill, plateau or surprise.
- Before any change to a milestone, gate or roadmap.

A routine continuation that the panel already agreed on does not need a new round.

## How it decides

- **Majority (3 of 5) decides.** If there is no majority, the option with the least new code and fewest moving parts wins. If that is still unclear, the experiment-design reviewer's position wins.
- **Every round starts with a correction check.** Each reviewer says whether the last decision or its implementation was wrong, and how to fix it.
- **Write-up.** Each round is summarised in `mjlab/results/` (verdicts, agreements, disagreements). Decisions that change direction get a D-entry. Decisions are append-only.

## Against over-engineering (every reviewer applies this)

- Prefer the smallest change that could work, and reuse existing code.
- No new infrastructure, framework or abstraction until two runs show it is needed.
- A reviewer who proposes something bigger must name the simpler option and say why it fails.
- Cut whatever is not needed to reach the next milestone.

## Standing rules (unchanged)

- One change per run.
- Each run is at most 6 h (the user's approval on 2026-10-21, D-137; it was 2 h), with a fixed endpoint and an early kill check at about 30 %.
- Development seeds only, recorded in the seed ledger.
- Never loosen a threshold. A gate changes only through a decision that names the premise that changed.
- Report failures as plainly as successes.

## Still the user's to decide (the agent stops and asks)

- sudo or system changes;
- Unity or the `feat/hierarchical-control` checkout;
- deleting anything;
- any download;
- any run over 6 h;
- using final seeds.
