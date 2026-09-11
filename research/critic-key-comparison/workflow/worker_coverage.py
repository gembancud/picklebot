"""Validate asynchronous worker coverage without imposing synchronized PPO buffers."""
from collections import Counter


def verify_worker_coverage(prepared, worker_count):
    assert type(worker_count) is int and worker_count > 0
    expected = set(map(str, range(worker_count)))
    assert prepared, 'No prepared updates'
    totals = Counter()
    omissions = []
    seen_updates = set()
    for row in prepared:
        update = row['update']
        assert update not in seen_updates, 'Duplicate update'
        seen_updates.add(update)
        workers = row['workers']
        assert workers and set(workers) <= expected, 'Unknown or empty worker IDs'
        assert all(type(n) is int and n > 0 for n in workers.values()), 'Invalid worker experience count'
        assert sum(workers.values()) == row['bufferExperiences'], 'Worker counts do not cover the buffer'
        totals.update(workers)
        missing = sorted(expected - set(workers), key=int)
        if missing:
            omissions.append(dict(update=update, missingWorkers=missing))
    assert set(totals) == expected, 'A worker never contributed to an optimizer buffer'
    return dict(status='all_workers_contributed_across_run', updates=len(prepared),
                experiencesByWorker=dict(sorted(totals.items(), key=lambda x: int(x[0]))),
                updatesWithMissingWorkers=omissions,
                interpretation='Asynchronous workers need not appear in every individual buffer; '
                               'worker completion, drill coverage and private actions are checked independently.')
