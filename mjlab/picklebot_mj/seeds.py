"""Seed ranges for the mjlab track (D-038). Disjoint by construction; final seeds stay unused
until a candidate is frozen for acceptance (same discipline as docs/DECISIONS.md)."""

from itertools import chain


class SeedBlocks:
    """Several disjoint seed ranges read as one (membership, iteration, indexing)."""

    def __init__(self, *ranges: range):
        self.ranges = ranges

    def __contains__(self, seed) -> bool:
        return any(seed in r for r in self.ranges)

    def __iter__(self):
        return chain(*self.ranges)

    def __len__(self) -> int:
        return sum(len(r) for r in self.ranges)

    def __getitem__(self, i: int) -> int:
        for r in self.ranges:
            if i < len(r):
                return r[i]
            i -= len(r)
        raise IndexError(i)


TRAIN_SEEDS = range(1, 1_000)  # rsl_rl / env seeds for training runs
# Development evaluations (reusable, reported as such). Block 2 was opened for Stage 5F by D-111 (block 1 nearly used
# up); its allocation is recorded in mjlab/results/seed-ledger.json.
DEV_EVAL_SEEDS = SeedBlocks(range(4_200_000, 4_201_000), range(4_210_000, 4_220_000))
FINAL_SEEDS = range(9_200_000, 9_201_000)  # reserved; never used for training, selection or tuning


def check_disjoint() -> None:
    ranges = [set(TRAIN_SEEDS), set(DEV_EVAL_SEEDS), set(FINAL_SEEDS)]
    for i in range(3):
        for j in range(i + 1, 3):
            assert not ranges[i] & ranges[j]
