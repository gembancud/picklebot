import copy
import unittest
from worker_coverage import verify_worker_coverage


def row(update, workers):
    return dict(update=update, workers=workers, bufferExperiences=sum(workers.values()))


class WorkerCoverageTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row(1, {'0': 40, '1': 60}), row(2, {'0': 100}), row(3, {'0': 30, '1': 70})]

    def test_asynchronous_gap_then_return(self):
        before = copy.deepcopy(self.rows)
        result = verify_worker_coverage(self.rows, 2)
        self.assertEqual(result['experiencesByWorker'], {'0': 170, '1': 130})
        self.assertEqual(result['updatesWithMissingWorkers'], [dict(update=2, missingWorkers=['1'])])
        self.assertEqual(self.rows, before)

    def test_disjoint_contributors_cover_run(self):
        self.assertEqual(verify_worker_coverage([row(1, {'0': 5}), row(2, {'1': 6})], 2)['updates'], 2)

    def test_worker_missing_entire_run(self):
        with self.assertRaisesRegex(AssertionError, 'never contributed'):
            verify_worker_coverage([row(1, {'0': 100})], 2)

    def test_unknown_worker(self):
        with self.assertRaisesRegex(AssertionError, 'Unknown'):
            verify_worker_coverage([row(1, {'0': 5, '1': 5, '2': 5})], 2)

    def test_count_mismatch(self):
        self.rows[0]['bufferExperiences'] += 1
        with self.assertRaisesRegex(AssertionError, 'do not cover'):
            verify_worker_coverage(self.rows, 2)

    def test_invalid_counts(self):
        for count in [0, -1, 1.5, True]:
            with self.subTest(count=count), self.assertRaisesRegex(AssertionError, 'Invalid'):
                verify_worker_coverage([row(1, {'0': count, '1': 5})], 2)

    def test_duplicate_update(self):
        with self.assertRaisesRegex(AssertionError, 'Duplicate'):
            verify_worker_coverage([self.rows[0], self.rows[0]], 2)

    def test_empty(self):
        with self.assertRaisesRegex(AssertionError, 'No prepared'):
            verify_worker_coverage([], 2)


if __name__ == '__main__':
    unittest.main()
