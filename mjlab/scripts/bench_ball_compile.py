"""Benchmark eager vs torch.compile (default, reduce-overhead) for the training ball step.

Usage: python scripts/bench_ball_compile.py [--n 4096] [--substeps 6] [--iters 200]
"""

import argparse
import json
import time

import torch

from picklebot_mj.ball_sim import BallSim, BallState, CompiledBallSim, PaddleState, _rotvec_to_matrix


def make(n, dev="cuda", seed=0):
    g = torch.Generator(device=dev).manual_seed(seed)
    r = lambda *s: torch.rand(*s, device=dev, generator=g)
    s = BallState(r(n, 3) * torch.tensor([4.0, 2.0, 1.2], device=dev) + torch.tensor([-6.0, -1.0, 0.1], device=dev),
                  (r(n, 3) - 0.5) * torch.tensor([20.0, 4.0, 10.0], device=dev), (r(n, 3) - 0.5) * 200)
    pd = PaddleState(s.pos + (r(n, 3) - 0.5) * 0.3, _rotvec_to_matrix((r(n, 3) - 0.5) * 3),
                     (r(n, 3) - 0.5) * 14, (r(n, 3) - 0.5) * 30)
    return s, pd


def bench(sim, s, pd, k, iters):
    for _ in range(5):
        sim.step(s, 0.005, k, pd, adaptive=False)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        out, _ = sim.step(s, 0.005, k, pd, adaptive=False)
    torch.cuda.synchronize()
    return 1000 * (time.perf_counter() - t0) / iters


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--substeps", type=int, default=6)
    ap.add_argument("--iters", type=int, default=200)
    a = ap.parse_args()
    s, pd = make(a.n)
    res = {}
    ref, ref_ev = BallSim().step(s, 0.005, a.substeps, pd, adaptive=False)
    for name, sim in (("eager", BallSim()), ("compile_default", CompiledBallSim(mode="default")),
                      ("compile_reduce_overhead", CompiledBallSim(mode="reduce-overhead"))):
        t_compile = time.perf_counter()
        out, ev = sim.step(s, 0.005, a.substeps, pd, adaptive=False)
        torch.cuda.synchronize()
        t_compile = time.perf_counter() - t_compile
        err = max(float((out.pos - ref.pos).abs().max()), float((out.vel - ref.vel).abs().max()))
        same_hits = bool(torch.equal(ev.paddle_contact, ref_ev.paddle_contact) and torch.equal(ev.court_contact, ref_ev.court_contact))
        res[name] = {"ms_per_physics_step": round(bench(sim, s, pd, a.substeps, a.iters), 3),
                     "first_call_s": round(t_compile, 1), "max_abs_err_vs_eager": err, "same_contacts": same_hits}
        print(name, res[name], flush=True)
    print(json.dumps(res, indent=1))
