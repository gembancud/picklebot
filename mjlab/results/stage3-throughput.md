# Stage 3 — training throughput: gate report

Date: 2026-10-02. Branch `feat/mjlab-pivot`. Task `Picklebot-Return-Stand-G1`, 4096 envs, RTX 4070.

## What changed
1. **Sync-free ball step** (`4b4e00d`). A fixed sub-step count (6 per 5 ms physics step, sized for 35 m/s relative speed) replaces batch-maximum adaptive sub-steps. The body is branch-free (all contact tests computed and masked). Court impact uses in-sub-step interpolation instead of two extra RK4 integrations. Constants are cached. The task term has no `.any()`/`bincount`/list-index syncs. Verified with a `torch.cuda.set_sync_debug_mode("error")` test.
2. **`torch.compile`** (`92f06b1`) of that step (`CompiledBallSim`, mode default, fullgraph, static shapes). The ball step goes **32.1 → 3.5 ms per physics step (9.3×)**, matching eager to 6e-6 m with identical contacts. Compile costs ~50 s once per process.

## Gate measurements
| Criterion | Result | Verdict |
|---|---|---|
| ≥ 2× training throughput at 4096 envs | Resumed `return-stand-02` from `model_700` for 20 iterations (same trained-policy workload). Steady state (18 iterations after warm-up and compile): **2.42 s per iteration = 40.6k env steps/s**. Baseline: 9.55 s mean over run 02 (10.3k/s); 11.5 s for its late iterations. **3.95× vs the run average, 4.76× on the matched workload.** | **PASS** |
| Physics tests green | 126 pass + 13 strict xfails (rejected native-contact baseline); includes new zero-sync, fixed-sub-step tunnelling and compiled-vs-eager tests | **PASS** |
| `model_700` dev evaluation unchanged (within its 95 % interval, seed 4,200,000) | Before: 96.1 % [95.0, 97.0]. After: **96.5 % [95.5, 97.3]** (1,485 / 1,539); contact 100 %; falls 0 %; paddle 7.09 m/s; landing x 4.59 m; failures 24 out, 4 wrong side | **PASS** |

**Stage 3 gate: PASS.** A 2-hour training budget now buys roughly 4× more experience (≈ 290M steps instead of ≈ 71M).

## Remaining costs (for later)
- The rest of the ball term (rules updates, diagnostics, mocap writes) is now ~40 % of the env step. Compiling the rules update would be next.
- CUDA-graph capture (`reduce-overhead`) failed on reused output buffers; not pursued.
- The fixed sub-step count is a design-speed choice: faster swings than 35 m/s relative would need more sub-steps (tunnelling test at 30 m/s passes).

Evidence: `stage3-profile*.json`, `stage3-bench-ball-compile.txt`, `stage3-gate-timing.txt`, `stage3-eval-model_700-4200000-compiled.json`.
