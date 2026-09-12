# Graded movement continuation

The fixed final executor reached **2,097,159 experiences**, adding **1,048,550** from the 1,048,609-experience checkpoint. The focus drills used 6.25/12.5/18.75/25 cm shifts in four directions, within the existing 25% familiar / 25% prior / 50% focus mixture.

Actor, critic, normalization, Adam and global step resumed through ML-Agents. Body controls, observations, PPO settings and smooth-distance reward were unchanged. Process RNG and live rollouts restarted; training reset IDs were reused. These results assess the fixed final export, without choosing a checkpoint by performance.

Five new evaluations reused the narrow 256-reset A/B/random battery and the wide 512-reset A/B battery. Both baselines retain their original source identities. Passed default-reset tests and exact paired first 124 physical / full 136 observation values support comparison across the opt-in scheduler change. No promotion, automatic extension or mastery acceptance follows from this report.

## Narrow retained-skill battery

**256 base resets; 150 distinct initial physical-observation clusters.** Conditions repeat the same resets; they are not independent extra situations.

Every count below is **legal / target hits / attempts**. Target success requires a legal landing inside the requested region; nonzero distance reward does not count as target success.

| Cases | Model | A | B | random |
|---|---|---:|---:|---:|
| All | Initializer | 235 / 115 / 256 | 235 / 3 / 256 | 235 / 65 / 256 |
| All | Previous endpoint | 234 / 96 / 256 | 235 / 33 / 256 | 235 / 77 / 256 |
| All | Axes endpoint | 234 / 68 / 256 | 233 / 28 / 256 | 233 / 72 / 256 |
| stationary-serve | Initializer | 16 / 16 / 16 | 16 / 0 / 16 | 16 / 10 / 16 |
| stationary-serve | Previous endpoint | 16 / 0 / 16 | 16 / 8 / 16 | 16 / 9 / 16 |
| stationary-serve | Axes endpoint | 16 / 8 / 16 | 16 / 8 / 16 | 16 / 13 / 16 |
| receive-feed | Initializer | 14 / 1 / 16 | 14 / 0 / 16 | 14 / 2 / 16 |
| receive-feed | Previous endpoint | 13 / 4 / 16 | 14 / 0 / 16 | 14 / 5 / 16 |
| receive-feed | Axes endpoint | 13 / 5 / 16 | 14 / 0 / 16 | 13 / 1 / 16 |
| rally-air-feed | Initializer | 101 / 41 / 112 | 101 / 3 / 112 | 101 / 26 / 112 |
| rally-air-feed | Previous endpoint | 101 / 46 / 112 | 102 / 0 / 112 | 101 / 35 / 112 |
| rally-air-feed | Axes endpoint | 102 / 46 / 112 | 100 / 1 / 112 | 101 / 29 / 112 |
| rally-bounce-feed | Initializer | 104 / 57 / 112 | 104 / 0 / 112 | 104 / 27 / 112 |
| rally-bounce-feed | Previous endpoint | 104 / 46 / 112 | 103 / 25 / 112 | 104 / 28 / 112 |
| rally-bounce-feed | Axes endpoint | 103 / 9 / 112 | 103 / 19 / 112 | 103 / 29 / 112 |

| Final A/B assignment gain | Reset-weighted estimate [95% interval] | Equal-observation-cluster estimate [95% interval] |
|---|---:|---:|
| Absolute final gain | +0.0020 [-0.0312, +0.0352] | +0.0200 [-0.0233, +0.0633] |
| Final minus initializer | +0.0020 [-0.0312, +0.0352] | +0.0200 [-0.0233, +0.0633] |
| Final minus previous endpoint | -0.0586 [-0.1055, -0.0098] | -0.0333 [-0.0933, +0.0233] |

Assignment gain compares requested versus opposite A/B regions on matched feeds. Illegal/no-landing attempts contribute zero. The initializer's target-blind actions and physical outcomes cancel exactly. Reset and cluster estimates use different weights; both intervals are pointwise and do not establish independent training replication.

| Drill | Model | Requested A: in A / in B / legal elsewhere / no legal landing | Requested B: same categories |
|---|---|---:|---:|
| stationary-serve | Initializer | 16 / 0 / 0 / 0 | 16 / 0 / 0 / 0 |
| stationary-serve | Previous endpoint | 0 / 0 / 16 / 0 | 0 / 8 / 8 / 0 |
| stationary-serve | Axes endpoint | 8 / 8 / 0 / 0 | 8 / 8 / 0 / 0 |
| receive-feed | Initializer | 1 / 0 / 13 / 2 | 1 / 0 / 13 / 2 |
| receive-feed | Previous endpoint | 4 / 0 / 9 / 3 | 5 / 0 / 9 / 2 |
| receive-feed | Axes endpoint | 5 / 0 / 8 / 3 | 2 / 0 / 12 / 2 |
| rally-air-feed | Initializer | 41 / 3 / 57 / 11 | 41 / 3 / 57 / 11 |
| rally-air-feed | Previous endpoint | 46 / 0 / 55 / 11 | 34 / 0 / 68 / 10 |
| rally-air-feed | Axes endpoint | 46 / 0 / 56 / 10 | 39 / 1 / 60 / 12 |
| rally-bounce-feed | Initializer | 57 / 0 / 47 / 8 | 57 / 0 / 47 / 8 |
| rally-bounce-feed | Previous endpoint | 46 / 23 / 35 / 8 | 36 / 25 / 42 / 9 |
| rally-bounce-feed | Axes endpoint | 9 / 24 / 70 / 9 | 14 / 19 / 70 / 9 |

A/B are shallow/deep target regions for serves and canonical left/right for receives and rallies. The complete analysis also retains player, serve-side, movement-category and paired outcome/telemetry differences.

## Wide movement battery

**512 base resets; 174 distinct initial physical-observation clusters.** Conditions repeat the same resets; they are not independent extra situations.

Every count below is **legal / target hits / attempts**. Target success requires a legal landing inside the requested region; nonzero distance reward does not count as target success.

| Cases | Model | A | B |
|---|---|---:|---:|
| All | Initializer | 275 / 104 / 512 | 275 / 2 / 512 |
| All | Previous endpoint | 285 / 78 / 512 | 288 / 56 / 512 |
| All | Axes endpoint | 288 / 69 / 512 | 284 / 37 / 512 |
| stationary-serve | Initializer | 64 / 64 / 64 | 64 / 0 / 64 |
| stationary-serve | Previous endpoint | 64 / 0 / 64 | 64 / 32 / 64 |
| stationary-serve | Axes endpoint | 64 / 32 / 64 | 64 / 32 / 64 |
| receive-feed | Initializer | 59 / 6 / 64 | 59 / 0 / 64 |
| receive-feed | Previous endpoint | 55 / 21 / 64 | 56 / 3 / 64 |
| receive-feed | Axes endpoint | 55 / 25 / 64 | 56 / 2 / 64 |
| rally-air-feed | Initializer | 69 / 16 / 192 | 69 / 2 / 192 |
| rally-air-feed | Previous endpoint | 76 / 38 / 192 | 78 / 1 / 192 |
| rally-air-feed | Axes endpoint | 74 / 9 / 192 | 69 / 0 / 192 |
| rally-bounce-feed | Initializer | 83 / 18 / 192 | 83 / 0 / 192 |
| rally-bounce-feed | Previous endpoint | 90 / 19 / 192 | 90 / 20 / 192 |
| rally-bounce-feed | Axes endpoint | 95 / 3 / 192 | 95 / 3 / 192 |
| Familiar/retained | Initializer | 251 / 102 / 256 | 251 / 0 / 256 |
| Familiar/retained | Previous endpoint | 247 / 69 / 256 | 248 / 51 / 256 |
| Familiar/retained | Axes endpoint | 247 / 57 / 256 | 248 / 34 / 256 |
| Axes challenges | Initializer | 24 / 2 / 256 | 24 / 2 / 256 |
| Axes challenges | Previous endpoint | 38 / 9 / 256 | 40 / 5 / 256 |
| Axes challenges | Axes endpoint | 41 / 12 / 256 | 36 / 3 / 256 |
| Left | Initializer | 5 / 0 / 66 | 5 / 0 / 66 |
| Left | Previous endpoint | 3 / 0 / 66 | 5 / 0 / 66 |
| Left | Axes endpoint | 3 / 0 / 66 | 3 / 0 / 66 |
| Right | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Right | Previous endpoint | 0 / 0 / 64 | 0 / 0 / 64 |
| Right | Axes endpoint | 0 / 0 / 64 | 0 / 0 / 64 |
| Shallow | Initializer | 5 / 2 / 62 | 5 / 0 / 62 |
| Shallow | Previous endpoint | 19 / 9 / 62 | 17 / 3 / 62 |
| Shallow | Axes endpoint | 19 / 10 / 62 | 12 / 0 / 62 |
| Deep | Initializer | 14 / 0 / 64 | 14 / 2 / 64 |
| Deep | Previous endpoint | 16 / 0 / 64 | 18 / 2 / 64 |
| Deep | Axes endpoint | 19 / 2 / 64 | 21 / 3 / 64 |
| Nominal 25 cm | Initializer | 21 / 2 / 64 | 21 / 2 / 64 |
| Nominal 25 cm | Previous endpoint | 31 / 9 / 64 | 33 / 5 / 64 |
| Nominal 25 cm | Axes endpoint | 29 / 12 / 64 | 22 / 3 / 64 |
| Nominal 50 cm | Initializer | 3 / 0 / 64 | 3 / 0 / 64 |
| Nominal 50 cm | Previous endpoint | 7 / 0 / 64 | 7 / 0 / 64 |
| Nominal 50 cm | Axes endpoint | 10 / 0 / 64 | 9 / 0 / 64 |
| Nominal 75 cm | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 75 cm | Previous endpoint | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 75 cm | Axes endpoint | 2 / 0 / 64 | 5 / 0 / 64 |
| Nominal 100 cm | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 100 cm | Previous endpoint | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 100 cm | Axes endpoint | 0 / 0 / 64 | 0 / 0 / 64 |

| Final A/B assignment gain | Reset-weighted estimate [95% interval] | Equal-observation-cluster estimate [95% interval] |
|---|---:|---:|
| Absolute final gain | -0.0186 [-0.0361, -0.0010] | +0.0259 [+0.0000, +0.0517] |
| Final minus initializer | -0.0186 [-0.0361, -0.0010] | +0.0259 [+0.0000, +0.0517] |
| Final minus previous endpoint | -0.0449 [-0.0693, -0.0205] | +0.0287 [-0.0057, +0.0632] |

Assignment gain compares requested versus opposite A/B regions on matched feeds. Illegal/no-landing attempts contribute zero. The initializer's target-blind actions and physical outcomes cancel exactly. Reset and cluster estimates use different weights; both intervals are pointwise and do not establish independent training replication.

| Drill | Model | Requested A: in A / in B / legal elsewhere / no legal landing | Requested B: same categories |
|---|---|---:|---:|
| stationary-serve | Initializer | 64 / 0 / 0 / 0 | 64 / 0 / 0 / 0 |
| stationary-serve | Previous endpoint | 0 / 0 / 64 / 0 | 0 / 32 / 32 / 0 |
| stationary-serve | Axes endpoint | 32 / 32 / 0 / 0 | 32 / 32 / 0 / 0 |
| receive-feed | Initializer | 6 / 0 / 53 / 5 | 6 / 0 / 53 / 5 |
| receive-feed | Previous endpoint | 21 / 1 / 33 / 9 | 25 / 3 / 28 / 8 |
| receive-feed | Axes endpoint | 25 / 0 / 30 / 9 | 4 / 2 / 50 / 8 |
| rally-air-feed | Initializer | 16 / 2 / 51 / 123 | 16 / 2 / 51 / 123 |
| rally-air-feed | Previous endpoint | 38 / 2 / 36 / 116 | 38 / 1 / 39 / 114 |
| rally-air-feed | Axes endpoint | 9 / 0 / 65 / 118 | 18 / 0 / 51 / 123 |
| rally-bounce-feed | Initializer | 18 / 0 / 65 / 109 | 18 / 0 / 65 / 109 |
| rally-bounce-feed | Previous endpoint | 19 / 20 / 51 / 102 | 21 / 20 / 49 / 102 |
| rally-bounce-feed | Axes endpoint | 3 / 19 / 73 / 97 | 20 / 3 / 72 / 97 |

A/B are shallow/deep target regions for serves and canonical left/right for receives and rallies. The complete analysis also retains player, serve-side, movement-category and paired outcome/telemetry differences.

Nominal shift is the feed offset from the initial paddle face, not required or actual root travel. Training focus stopped at 25 cm; the 50–100 cm cases are transfer probes. Direction and distance tables are marginal summaries; sparse joint cells remain included.

| Final axes movement | A | B |
|---|---:|---:|
| Accepted face contacts / attempts | 77 / 256 | 77 / 256 |
| Root path through first contact or termination | 0.835 m (n=256) | 0.855 m (n=256) |
| Root path conditional on accepted contact | 0.453 m (n=77) | 0.458 m (n=77) |
| Net root displacement conditional on accepted contact | 0.331 m (n=77) | 0.333 m (n=77) |
| Root path through no-contact termination | 0.998 m (n=179) | 1.026 m (n=179) |

The 128 drill/direction/distance/player cells include 2 empty cells and 126 cells with fewer than five attempts. These remain descriptive. Longer miss trajectories can accumulate more travel; distance alone does not prove better positioning.

## Existing narrow retention screen

| Check | Against initializer | Against previous endpoint |
|---|---|---|
| Final reset-weighted gain interval lower bound > 0 | Fail | Fail |
| Final cluster-weighted gain interval lower bound > 0 | Fail | Fail |
| Final A and B target rates exceed comparison model | Fail | Fail |
| No drill/condition loses >5 percentage points of legality | Fail | Fail |
| Combined descriptive screen | Fail | Fail |

The original retention rule uses point estimates; it is not a statistical noninferiority guarantee. Absolute final assignment gain and changes versus each baseline are reported separately. No new pass threshold is imposed on wide movement.

| Drill / condition | Legal-rate change vs initializer, pp [95% interval] | Vs previous endpoint, pp [95% interval] |
|---|---:|---:|
| stationary-serve / A | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| stationary-serve / B | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| stationary-serve / random | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| receive-feed / A | -6.2500 [-25.0000, +12.5000] | +0.0000 [+0.0000, +0.0000] |
| receive-feed / B | +0.0000 [-25.0000, +25.0000] | +0.0000 [+0.0000, +0.0000] |
| receive-feed / random | -6.2500 [-25.0000, +12.5000] | -6.2500 [-18.7500, +0.0000] |
| rally-air-feed / A | +0.8929 [-4.4643, +6.2500] | +0.8929 [-3.5714, +5.3571] |
| rally-air-feed / B | -0.8929 [-5.3571, +3.5714] | -1.7857 [-6.2500, +2.6786] |
| rally-air-feed / random | +0.0000 [-5.3571, +4.4643] | +0.0000 [-4.4643, +4.4643] |
| rally-bounce-feed / A | -0.8929 [-4.4643, +1.7857] | -0.8929 [-4.4643, +2.6786] |
| rally-bounce-feed / B | -0.8929 [-4.4643, +1.7857] | +0.0000 [-2.6786, +2.6786] |
| rally-bounce-feed / random | -0.8929 [-4.4643, +1.7857] | -0.8929 [-4.4643, +1.7857] |

## Actual receiving and volley contacts

| Final battery / condition | Required-bounce legal / attempts | Volley legal / accepted volley contacts | Bounced-rally legal / accepted bounced contacts | Rally attempts |
|---|---:|---:|---:|---:|
| narrow / A | 13 / 16 | 102 / 106 | 103 / 108 | 224 |
| narrow / B | 14 / 16 | 100 / 106 | 103 / 109 | 224 |
| narrow / random | 13 / 16 | 101 / 106 | 103 / 110 | 224 |
| wide / A | 55 / 64 | 74 / 98 | 95 / 107 | 384 |
| wide / B | 56 / 64 | 69 / 99 | 95 / 106 | 384 |

Volley/bounced-contact columns are explicitly conditional contact outcomes; the earlier legal/all tables include misses. A rally-bounce feed permits a volley after the opening rule has cleared. A false volley flag without contact is not counted as a groundstroke.

## Evidence limits

This is one continuing training lineage on reused development situations. Repeated observations and exact reset parity do not establish broad generalization or prove each difficult feed is physically reachable. Varied starts and timing, broader required-bounce receiving, kitchen-line/momentum decisions, paired ownership and full 2v2 play remain outside this battery's mastery claim.

The source, tests, seeds, selection, all five raw evaluations and complete analysis are preserved. Worker rollout JSONL is stored as lossless gzip with compressed and uncompressed hashes. Existing canonical model/checkpoint files and previously archived helper dependencies are referenced by hash, without duplicating large binaries. Final acceptance seeds remain unused.

[Analysis](execution-v1-evidence/axes-recovery-01/results/audit/analysis.json) · [Frozen plan](execution-v1-evidence/axes-recovery-01/results/plan.json) · [Training verification](execution-v1-evidence/axes-recovery-01/results/training/verification.json) · [Archive coverage](execution-v1-evidence/axes-recovery-01/results/archive-manifest.json) · [Coverage gaps](drill-mastery-coverage.md)
