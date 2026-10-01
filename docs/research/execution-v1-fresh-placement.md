# Fresh placement development screen

Both frozen models were evaluated anew on **256 paired base resets**, each repeated under target A, target B and random targets. The candidate is fixed at 1,048,609 training experiences; this campaign adds evaluation only.

The predeclared diagnostic screen **did not pass**. No model promotion or drill-mastery acceptance follows from this result.

| Model | A legal / target hits (of 256) | B legal / target hits (of 256) | Random legal / target hits (of 256) |
|---|---:|---:|---:|
| Initializer | 235 / 115 | 235 / 3 | 235 / 65 |
| Candidate (1,048,609 experiences) | 234 / 96 | 235 / 33 | 235 / 77 |

Target hits require a legal landing within 1 m for A/B or 1.5 m for random targets. Nonzero training reward is not a target hit. A/B/random are repeated conditions of the same base resets, not three independent sets of situations.

| Candidate assignment-gain estimate | Mean | Pointwise 95% interval | Weighting |
|---|---:|---:|---|
| Paired reset estimate | 0.06055 | [0.02734, 0.09180] | Every base reset equally |
| Unique-observation cluster estimate | 0.05333 | [0.01667, 0.09333] | Average within identical observations, then each cluster equally |

Assignment gain measures requested-versus-opposite-region success on paired feeds. Target-blind shots cancel; attempts without legal landings contribute zero. The two estimates use different weights and need not agree. Their intervals do not establish independent training replication or broad generalization.

| Predeclared check | Result |
|---|---|
| Reset-weighted gain interval lower bound above zero | Pass |
| Unique-cluster gain interval lower bound above zero | Pass |
| A and B target-hit rates both exceed the initializer | Fail |
| No drill loses more than 5 percentage points of legality in any condition | Fail |

The retention limit uses per-drill point estimates; it is not a statistical noninferiority guarantee.

| Retention guard triggered | Candidate minus initializer | Paired 95% interval |
|---|---:|---:|
| receive-feed / A | -6.25 percentage points | [-25.00, +12.50] percentage points |

These point estimates trigger the predeclared guard. Wide intervals that include zero do not establish a reliable regression; all per-drill checks remain available in the analysis.

## Requested targets and actual landings

Each cell lists **in A / in B / legal outside both / no legal landing**. A/B means shallower/deeper for serves and canonical left/right for rally and receiving shots. Every attempt remains included.

| Drill | Model | Requested A | Requested B |
|---|---|---:|---:|
| stationary-serve | Initializer | 16 / 0 / 0 / 0 | 16 / 0 / 0 / 0 |
| stationary-serve | Candidate | 0 / 0 / 16 / 0 | 0 / 8 / 8 / 0 |
| receive-feed | Initializer | 1 / 0 / 13 / 2 | 1 / 0 / 13 / 2 |
| receive-feed | Candidate | 4 / 0 / 9 / 3 | 5 / 0 / 9 / 2 |
| rally-air-feed | Initializer | 41 / 3 / 57 / 11 | 41 / 3 / 57 / 11 |
| rally-air-feed | Candidate | 46 / 0 / 55 / 11 | 34 / 0 / 68 / 10 |
| rally-bounce-feed | Initializer | 57 / 0 / 47 / 8 | 57 / 0 / 47 / 8 |
| rally-bounce-feed | Candidate | 46 / 23 / 35 / 8 | 36 / 25 / 42 / 9 |

## What was physically new

The 256 reset IDs produced **150 distinct first-observation vectors**. Compared with the pinned prior set of 150 vectors, **62 resets were exactly novel** and **194 repeated a prior vector**. This is observed-state novelty, not proof of new hidden simulator states or harder shots.

| Drill | Base resets | Exactly novel observations (resets) | Repeated observations (resets) |
|---|---:|---:|---:|
| stationary-serve | 16 | 0 | 16 |
| receive-feed | 16 | 8 | 8 |
| rally-air-feed | 112 | 27 | 85 |
| rally-bounce-feed | 112 | 27 | 85 |

194/256 resets are within a maximum normalized-feature difference of 0.00001 from a prior observation; 194/256 are within 0.0001. These thresholds are descriptive, are not measured in metres, and exclude no cases.

| Descriptive subset | Base resets | Candidate A legal / targets | Candidate B legal / targets | Reset-weighted gain [95% interval] |
|---|---:|---:|---:|---:|
| Exactly novel | 62 | 43 / 10 | 44 / 4 | 0.00806 [-0.04052, 0.06452] |
| Exactly repeated | 194 | 191 / 86 | 191 / 29 | 0.07732 [0.04124, 0.11598] |

Exact-novel/repeated subsets and their per-drill results are descriptive. The predeclared screen uses all cases. A repeated first observation can conceal other state differences, while an exactly novel vector can differ only slightly.

## Coverage still needed for mastery

This remains the existing small-shift recovery recipe. It does not deliberately cover broad left/right/shallow/deep footwork, independent start positions and flight times, varied mandatory-bounce receiver contexts, or kitchen-line/momentum decisions. An accepted shifted-ball return does not prove that substantial body movement was required.

Actual `incomingServeLanded` and `contactWasVolley` indicators are included in the analysis. Rally-bounce feeds already permit volleys and are not substitutes for mandatory-bounce receiving. A false volley flag without contact is not counted as a groundstroke.

The goal still requires per-skill and per-variation acceptance thresholds, repeat evidence with uncertainty, preservation in the same checkpoint, and representative movement recordings for human review. Passing this screen alone cannot satisfy those requirements. Final acceptance seeds remain untouched; freshness here is limited to the recorded V3 ledger.

[Complete analysis](execution-v1-evidence/fresh-placement-01/analysis.json) · [Frozen plan](execution-v1-evidence/fresh-placement-01/plan.json) · [Input archive and coverage](execution-v1-evidence/fresh-placement-01/archive-manifest.json) · [Coverage audit](drill-mastery-coverage.md)
