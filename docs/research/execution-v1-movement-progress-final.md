# Forward-flight reward comparison

The fixed final executor reached **2,097,183 experiences**, adding **1,048,574** from the 1,048,609-experience checkpoint. The focus drills used 6.25/12.5/18.75/25 cm shifts in four directions, within the existing 25% familiar / 25% prior / 50% focus mixture.

Actor, critic, normalization, Adam and global step resumed through ML-Agents from the common parent. The sole training change added up to 0.25 for measured post-contact forward progress in focus episodes. Familiar and prior-court rewards, body controls, observations, PPO and smooth placement reward were unchanged. Process RNG and live rollouts restarted; training reset IDs were reused. These results assess the fixed final export, without choosing a checkpoint by performance.

Five new evaluations reused the narrow 256-reset A/B/random battery and the wide 512-reset A/B battery. All three comparison models retain their original source identities. The completed axes run supplies the no-progress control; this is one training lineage per condition, not replicated causal evidence. The added reward is disabled for all new frozen evaluations. Fifty passed reward/default-reset checks and exact paired first 124 physical / full 136 observation values support comparison across the opt-in scheduler change. No promotion, automatic extension or mastery acceptance follows from this report.

## Narrow retained-skill battery

**256 base resets; 150 distinct initial physical-observation clusters.** Conditions repeat the same resets; they are not independent extra situations.

Every count below is **legal / target hits / attempts**. Target success requires a legal landing inside the requested region; nonzero distance reward does not count as target success.

| Cases | Model | A | B | random |
|---|---|---:|---:|---:|
| All | Initializer | 235 / 115 / 256 | 235 / 3 / 256 | 235 / 65 / 256 |
| All | Common parent | 234 / 96 / 256 | 235 / 33 / 256 | 235 / 77 / 256 |
| All | No-progress control | 234 / 68 / 256 | 233 / 28 / 256 | 233 / 72 / 256 |
| All | Progress reward endpoint | 224 / 84 / 256 | 230 / 36 / 256 | 225 / 74 / 256 |
| stationary-serve | Initializer | 16 / 16 / 16 | 16 / 0 / 16 | 16 / 10 / 16 |
| stationary-serve | Common parent | 16 / 0 / 16 | 16 / 8 / 16 | 16 / 9 / 16 |
| stationary-serve | No-progress control | 16 / 8 / 16 | 16 / 8 / 16 | 16 / 13 / 16 |
| stationary-serve | Progress reward endpoint | 16 / 0 / 16 | 16 / 8 / 16 | 16 / 11 / 16 |
| receive-feed | Initializer | 14 / 1 / 16 | 14 / 0 / 16 | 14 / 2 / 16 |
| receive-feed | Common parent | 13 / 4 / 16 | 14 / 0 / 16 | 14 / 5 / 16 |
| receive-feed | No-progress control | 13 / 5 / 16 | 14 / 0 / 16 | 13 / 1 / 16 |
| receive-feed | Progress reward endpoint | 12 / 3 / 16 | 13 / 5 / 16 | 12 / 3 / 16 |
| rally-air-feed | Initializer | 101 / 41 / 112 | 101 / 3 / 112 | 101 / 26 / 112 |
| rally-air-feed | Common parent | 101 / 46 / 112 | 102 / 0 / 112 | 101 / 35 / 112 |
| rally-air-feed | No-progress control | 102 / 46 / 112 | 100 / 1 / 112 | 101 / 29 / 112 |
| rally-air-feed | Progress reward endpoint | 89 / 25 / 112 | 94 / 12 / 112 | 91 / 31 / 112 |
| rally-bounce-feed | Initializer | 104 / 57 / 112 | 104 / 0 / 112 | 104 / 27 / 112 |
| rally-bounce-feed | Common parent | 104 / 46 / 112 | 103 / 25 / 112 | 104 / 28 / 112 |
| rally-bounce-feed | No-progress control | 103 / 9 / 112 | 103 / 19 / 112 | 103 / 29 / 112 |
| rally-bounce-feed | Progress reward endpoint | 107 / 56 / 112 | 107 / 11 / 112 | 106 / 29 / 112 |

| Final A/B assignment gain | Reset-weighted estimate [95% interval] | Equal-observation-cluster estimate [95% interval] |
|---|---:|---:|
| Absolute final gain | +0.0156 [-0.0117, +0.0430] | +0.0267 [-0.0100, +0.0633] |
| Final minus initializer | +0.0156 [-0.0117, +0.0430] | +0.0267 [-0.0100, +0.0633] |
| Final minus common parent | -0.0449 [-0.0859, -0.0039] | -0.0267 [-0.0800, +0.0267] |
| Final minus no-progress control | +0.0137 [-0.0293, +0.0547] | +0.0067 [-0.0500, +0.0600] |

Assignment gain compares requested versus opposite A/B regions on matched feeds. Illegal/no-landing attempts contribute zero. The initializer's target-blind actions and physical outcomes cancel exactly. Reset and cluster estimates use different weights; both intervals are pointwise and do not establish independent training replication.

| Drill | Model | Requested A: in A / in B / legal elsewhere / no legal landing | Requested B: same categories |
|---|---|---:|---:|
| stationary-serve | Initializer | 16 / 0 / 0 / 0 | 16 / 0 / 0 / 0 |
| stationary-serve | Common parent | 0 / 0 / 16 / 0 | 0 / 8 / 8 / 0 |
| stationary-serve | No-progress control | 8 / 8 / 0 / 0 | 8 / 8 / 0 / 0 |
| stationary-serve | Progress reward endpoint | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 |
| receive-feed | Initializer | 1 / 0 / 13 / 2 | 1 / 0 / 13 / 2 |
| receive-feed | Common parent | 4 / 0 / 9 / 3 | 5 / 0 / 9 / 2 |
| receive-feed | No-progress control | 5 / 0 / 8 / 3 | 2 / 0 / 12 / 2 |
| receive-feed | Progress reward endpoint | 3 / 1 / 8 / 4 | 1 / 5 / 7 / 3 |
| rally-air-feed | Initializer | 41 / 3 / 57 / 11 | 41 / 3 / 57 / 11 |
| rally-air-feed | Common parent | 46 / 0 / 55 / 11 | 34 / 0 / 68 / 10 |
| rally-air-feed | No-progress control | 46 / 0 / 56 / 10 | 39 / 1 / 60 / 12 |
| rally-air-feed | Progress reward endpoint | 25 / 7 / 57 / 23 | 33 / 12 / 49 / 18 |
| rally-bounce-feed | Initializer | 57 / 0 / 47 / 8 | 57 / 0 / 47 / 8 |
| rally-bounce-feed | Common parent | 46 / 23 / 35 / 8 | 36 / 25 / 42 / 9 |
| rally-bounce-feed | No-progress control | 9 / 24 / 70 / 9 | 14 / 19 / 70 / 9 |
| rally-bounce-feed | Progress reward endpoint | 56 / 15 / 36 / 5 | 47 / 11 / 49 / 5 |

A/B are shallow/deep target regions for serves and canonical left/right for receives and rallies. The complete analysis also retains player, serve-side, movement-category and paired outcome/telemetry differences.

## Wide movement battery

**512 base resets; 174 distinct initial physical-observation clusters.** Conditions repeat the same resets; they are not independent extra situations.

Every count below is **legal / target hits / attempts**. Target success requires a legal landing inside the requested region; nonzero distance reward does not count as target success.

| Cases | Model | A | B |
|---|---|---:|---:|
| All | Initializer | 275 / 104 / 512 | 275 / 2 / 512 |
| All | Common parent | 285 / 78 / 512 | 288 / 56 / 512 |
| All | No-progress control | 288 / 69 / 512 | 284 / 37 / 512 |
| All | Progress reward endpoint | 283 / 44 / 512 | 292 / 67 / 512 |
| stationary-serve | Initializer | 64 / 64 / 64 | 64 / 0 / 64 |
| stationary-serve | Common parent | 64 / 0 / 64 | 64 / 32 / 64 |
| stationary-serve | No-progress control | 64 / 32 / 64 | 64 / 32 / 64 |
| stationary-serve | Progress reward endpoint | 64 / 0 / 64 | 64 / 32 / 64 |
| receive-feed | Initializer | 59 / 6 / 64 | 59 / 0 / 64 |
| receive-feed | Common parent | 55 / 21 / 64 | 56 / 3 / 64 |
| receive-feed | No-progress control | 55 / 25 / 64 | 56 / 2 / 64 |
| receive-feed | Progress reward endpoint | 58 / 9 / 64 | 57 / 19 / 64 |
| rally-air-feed | Initializer | 69 / 16 / 192 | 69 / 2 / 192 |
| rally-air-feed | Common parent | 76 / 38 / 192 | 78 / 1 / 192 |
| rally-air-feed | No-progress control | 74 / 9 / 192 | 69 / 0 / 192 |
| rally-air-feed | Progress reward endpoint | 71 / 3 / 192 | 73 / 0 / 192 |
| rally-bounce-feed | Initializer | 83 / 18 / 192 | 83 / 0 / 192 |
| rally-bounce-feed | Common parent | 90 / 19 / 192 | 90 / 20 / 192 |
| rally-bounce-feed | No-progress control | 95 / 3 / 192 | 95 / 3 / 192 |
| rally-bounce-feed | Progress reward endpoint | 90 / 32 / 192 | 98 / 16 / 192 |
| Familiar/retained | Initializer | 251 / 102 / 256 | 251 / 0 / 256 |
| Familiar/retained | Common parent | 247 / 69 / 256 | 248 / 51 / 256 |
| Familiar/retained | No-progress control | 247 / 57 / 256 | 248 / 34 / 256 |
| Familiar/retained | Progress reward endpoint | 250 / 41 / 256 | 249 / 67 / 256 |
| Axes challenges | Initializer | 24 / 2 / 256 | 24 / 2 / 256 |
| Axes challenges | Common parent | 38 / 9 / 256 | 40 / 5 / 256 |
| Axes challenges | No-progress control | 41 / 12 / 256 | 36 / 3 / 256 |
| Axes challenges | Progress reward endpoint | 33 / 3 / 256 | 43 / 0 / 256 |
| Left | Initializer | 5 / 0 / 66 | 5 / 0 / 66 |
| Left | Common parent | 3 / 0 / 66 | 5 / 0 / 66 |
| Left | No-progress control | 3 / 0 / 66 | 3 / 0 / 66 |
| Left | Progress reward endpoint | 2 / 0 / 66 | 5 / 0 / 66 |
| Right | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Right | Common parent | 0 / 0 / 64 | 0 / 0 / 64 |
| Right | No-progress control | 0 / 0 / 64 | 0 / 0 / 64 |
| Right | Progress reward endpoint | 0 / 0 / 64 | 0 / 0 / 64 |
| Shallow | Initializer | 5 / 2 / 62 | 5 / 0 / 62 |
| Shallow | Common parent | 19 / 9 / 62 | 17 / 3 / 62 |
| Shallow | No-progress control | 19 / 10 / 62 | 12 / 0 / 62 |
| Shallow | Progress reward endpoint | 15 / 3 / 62 | 17 / 0 / 62 |
| Deep | Initializer | 14 / 0 / 64 | 14 / 2 / 64 |
| Deep | Common parent | 16 / 0 / 64 | 18 / 2 / 64 |
| Deep | No-progress control | 19 / 2 / 64 | 21 / 3 / 64 |
| Deep | Progress reward endpoint | 16 / 0 / 64 | 21 / 0 / 64 |
| Nominal 25 cm | Initializer | 21 / 2 / 64 | 21 / 2 / 64 |
| Nominal 25 cm | Common parent | 31 / 9 / 64 | 33 / 5 / 64 |
| Nominal 25 cm | No-progress control | 29 / 12 / 64 | 22 / 3 / 64 |
| Nominal 25 cm | Progress reward endpoint | 23 / 3 / 64 | 28 / 0 / 64 |
| Nominal 50 cm | Initializer | 3 / 0 / 64 | 3 / 0 / 64 |
| Nominal 50 cm | Common parent | 7 / 0 / 64 | 7 / 0 / 64 |
| Nominal 50 cm | No-progress control | 10 / 0 / 64 | 9 / 0 / 64 |
| Nominal 50 cm | Progress reward endpoint | 5 / 0 / 64 | 8 / 0 / 64 |
| Nominal 75 cm | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 75 cm | Common parent | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 75 cm | No-progress control | 2 / 0 / 64 | 5 / 0 / 64 |
| Nominal 75 cm | Progress reward endpoint | 5 / 0 / 64 | 7 / 0 / 64 |
| Nominal 100 cm | Initializer | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 100 cm | Common parent | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 100 cm | No-progress control | 0 / 0 / 64 | 0 / 0 / 64 |
| Nominal 100 cm | Progress reward endpoint | 0 / 0 / 64 | 0 / 0 / 64 |

| Final A/B assignment gain | Reset-weighted estimate [95% interval] | Equal-observation-cluster estimate [95% interval] |
|---|---:|---:|
| Absolute final gain | -0.0068 [-0.0195, +0.0059] | +0.0000 [-0.0201, +0.0201] |
| Final minus initializer | -0.0068 [-0.0195, +0.0059] | +0.0000 [-0.0201, +0.0201] |
| Final minus common parent | -0.0332 [-0.0537, -0.0127] | +0.0029 [-0.0259, +0.0316] |
| Final minus no-progress control | +0.0117 [-0.0078, +0.0312] | -0.0259 [-0.0546, +0.0029] |

Assignment gain compares requested versus opposite A/B regions on matched feeds. Illegal/no-landing attempts contribute zero. The initializer's target-blind actions and physical outcomes cancel exactly. Reset and cluster estimates use different weights; both intervals are pointwise and do not establish independent training replication.

| Drill | Model | Requested A: in A / in B / legal elsewhere / no legal landing | Requested B: same categories |
|---|---|---:|---:|
| stationary-serve | Initializer | 64 / 0 / 0 / 0 | 64 / 0 / 0 / 0 |
| stationary-serve | Common parent | 0 / 0 / 64 / 0 | 0 / 32 / 32 / 0 |
| stationary-serve | No-progress control | 32 / 32 / 0 / 0 | 32 / 32 / 0 / 0 |
| stationary-serve | Progress reward endpoint | 0 / 32 / 32 / 0 | 0 / 32 / 32 / 0 |
| receive-feed | Initializer | 6 / 0 / 53 / 5 | 6 / 0 / 53 / 5 |
| receive-feed | Common parent | 21 / 1 / 33 / 9 | 25 / 3 / 28 / 8 |
| receive-feed | No-progress control | 25 / 0 / 30 / 9 | 4 / 2 / 50 / 8 |
| receive-feed | Progress reward endpoint | 9 / 3 / 46 / 6 | 7 / 19 / 31 / 7 |
| rally-air-feed | Initializer | 16 / 2 / 51 / 123 | 16 / 2 / 51 / 123 |
| rally-air-feed | Common parent | 38 / 2 / 36 / 116 | 38 / 1 / 39 / 114 |
| rally-air-feed | No-progress control | 9 / 0 / 65 / 118 | 18 / 0 / 51 / 123 |
| rally-air-feed | Progress reward endpoint | 3 / 0 / 68 / 121 | 23 / 0 / 50 / 119 |
| rally-bounce-feed | Initializer | 18 / 0 / 65 / 109 | 18 / 0 / 65 / 109 |
| rally-bounce-feed | Common parent | 19 / 20 / 51 / 102 | 21 / 20 / 49 / 102 |
| rally-bounce-feed | No-progress control | 3 / 19 / 73 / 97 | 20 / 3 / 72 / 97 |
| rally-bounce-feed | Progress reward endpoint | 32 / 19 / 39 / 102 | 34 / 16 / 48 / 94 |

A/B are shallow/deep target regions for serves and canonical left/right for receives and rallies. The complete analysis also retains player, serve-side, movement-category and paired outcome/telemetry differences.

Nominal shift is the feed offset from the initial paddle face, not required or actual root travel. Training focus stopped at 25 cm; the 50â€“100 cm cases are transfer probes. Direction and distance tables are marginal summaries; sparse joint cells remain included.

| Final axes movement | A | B |
|---|---:|---:|
| Accepted face contacts / attempts | 78 / 256 | 79 / 256 |
| Root path through first contact or termination | 0.879 m (n=256) | 0.868 m (n=256) |
| Root path conditional on accepted contact | 0.495 m (n=78) | 0.492 m (n=79) |
| Net root displacement conditional on accepted contact | 0.353 m (n=78) | 0.352 m (n=79) |
| Root path through no-contact termination | 1.047 m (n=178) | 1.036 m (n=177) |

The 128 drill/direction/distance/player cells include 2 empty cells and 126 cells with fewer than five attempts. These remain descriptive. Longer miss trajectories can accumulate more travel; distance alone does not prove better positioning.

## Existing narrow retention screen

| Check | Against initializer | Against common parent | Against no-progress control |
|---|---|---|---|
| Final reset-weighted gain interval lower bound > 0 | Fail | Fail | Fail |
| Final cluster-weighted gain interval lower bound > 0 | Fail | Fail | Fail |
| Final A and B target rates exceed comparison model | Fail | Fail | Pass |
| No drill/condition loses >5 percentage points of legality | Fail | Fail | Fail |
| Combined descriptive screen | Fail | Fail | Fail |

The original retention rule uses point estimates; it is not a statistical noninferiority guarantee. Absolute final assignment gain and changes versus each baseline are reported separately. No new pass threshold is imposed on wide movement.

| Drill / condition | Legal-rate change vs initializer, pp [95% interval] | Vs common parent, pp [95% interval] | Vs no-progress control, pp [95% interval] |
|---|---:|---:|---:|
| stationary-serve / A | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| stationary-serve / B | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| stationary-serve / random | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| receive-feed / A | -12.5000 [-31.2500, +0.0000] | -6.2500 [-18.7500, +0.0000] | -6.2500 [-18.7500, +0.0000] |
| receive-feed / B | -6.2500 [-25.0000, +12.5000] | -6.2500 [-18.7500, +0.0000] | -6.2500 [-18.7500, +0.0000] |
| receive-feed / random | -12.5000 [-31.2500, +0.0000] | -12.5000 [-31.2500, +0.0000] | -6.2500 [-18.7500, +0.0000] |
| rally-air-feed / A | -10.7143 [-16.9643, -5.3571] | -10.7143 [-17.8571, -3.5714] | -11.6071 [-17.8571, -6.2500] |
| rally-air-feed / B | -6.2500 [-10.7143, -1.7857] | -7.1429 [-13.3929, -0.8929] | -5.3571 [-10.7143, -0.8929] |
| rally-air-feed / random | -8.9286 [-14.2857, -4.4643] | -8.9286 [-15.1786, -2.6786] | -8.9286 [-14.2857, -4.4643] |
| rally-bounce-feed / A | +2.6786 [+0.0000, +6.2500] | +2.6786 [+0.0000, +6.2500] | +3.5714 [+0.0000, +8.0357] |
| rally-bounce-feed / B | +2.6786 [+0.0000, +6.2500] | +3.5714 [+0.8929, +7.1429] | +3.5714 [+0.0000, +8.0357] |
| rally-bounce-feed / random | +1.7857 [-1.7857, +5.3571] | +1.7857 [-1.7857, +5.3571] | +2.6786 [-1.7857, +7.1429] |

## Actual receiving and volley contacts

| Final battery / condition | Required-bounce legal / attempts | Volley legal / accepted volley contacts | Bounced-rally legal / accepted bounced contacts | Rally attempts |
|---|---:|---:|---:|---:|
| narrow / A | 12 / 16 | 89 / 105 | 107 / 110 | 224 |
| narrow / B | 13 / 16 | 94 / 105 | 107 / 109 | 224 |
| narrow / random | 12 / 16 | 91 / 105 | 106 / 110 | 224 |
| wide / A | 58 / 64 | 71 / 96 | 90 / 110 | 384 |
| wide / B | 57 / 64 | 73 / 97 | 98 / 110 | 384 |

Volley/bounced-contact columns are explicitly conditional contact outcomes; the earlier legal/all tables include misses. A rally-bounce feed permits a volley after the opening rule has cleared. A false volley flag without contact is not counted as a groundstroke.

## Evidence limits

This is one continuing training lineage on reused development situations. Repeated observations and exact reset parity do not establish broad generalization or prove each difficult feed is physically reachable. Varied starts and timing, broader required-bounce receiving, kitchen-line/momentum decisions, paired ownership and full 2v2 play remain outside this battery's mastery claim.

The source, tests, seeds, selection, all five raw evaluations and complete analysis are preserved. Worker rollout JSONL is stored as lossless gzip with compressed and uncompressed hashes. Existing canonical model/checkpoint files and previously archived helper dependencies are referenced by hash, without duplicating large binaries. Final acceptance seeds remain unused.

[Analysis](execution-v1-evidence/movement-progress-01/results/audit/analysis.json) Â· [Frozen plan](execution-v1-evidence/movement-progress-01/results/plan.json) Â· [Training verification](execution-v1-evidence/movement-progress-01/results/training/verification.json) Â· [Archive coverage](execution-v1-evidence/movement-progress-01/results/archive-manifest.json) Â· [Coverage gaps](drill-mastery-coverage.md)
