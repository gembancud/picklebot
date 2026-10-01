"""Seed ranges for the mjlab track (D-038). Disjoint by construction; final seeds stay unused
until a candidate is frozen for acceptance (same discipline as docs/DECISIONS.md)."""

TRAIN_SEEDS = range(1, 1_000)  # rsl_rl / env seeds for training runs
DEV_EVAL_SEEDS = range(4_200_000, 4_201_000)  # development evaluations (reusable, reported as such)
FINAL_SEEDS = range(9_200_000, 9_201_000)  # reserved; never used for training, selection or tuning


def check_disjoint() -> None:
    ranges = [set(TRAIN_SEEDS), set(DEV_EVAL_SEEDS), set(FINAL_SEEDS)]
    for i in range(3):
        for j in range(i + 1, 3):
            assert not ranges[i] & ranges[j]
