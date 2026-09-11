import unittest
import numpy as np
from mlagents.torch_utils import torch
from stability_diagnostics import exact_kl, discounted, fit_stats, cosine, task_key


class MathTests(unittest.TestCase):
    def test_exact_kl_matches_torch_distributions_with_masked_branch(self):
        before = dict(mean=np.array([[0., 1.], [.2, -.5]]), std=np.array([[1., .5], [.7, 2.]]),
                      probs=[np.array([[1., 0.], [.3, .7]])])
        after = dict(mean=np.array([[.4, 1.1], [-.2, -.6]]), std=np.array([[.8, .6], [.9, 1.9]]),
                     probs=[np.array([[1., 0.], [.6, .4]])])
        kl, continuous, discrete = exact_kl(before, after)
        normal = [torch.distributions.Normal(torch.tensor(d['mean']), torch.tensor(d['std'])) for d in (before, after)]
        categorical = [torch.distributions.Categorical(probs=torch.tensor(d['probs'][0])) for d in (before, after)]
        expected = (torch.distributions.kl_divergence(*normal).sum(1)+torch.distributions.kl_divergence(*categorical)).cpu().numpy()
        np.testing.assert_allclose(kl, expected, rtol=1e-10, atol=1e-10)
        np.testing.assert_allclose(exact_kl(before, before)[0], 0, atol=1e-14)
        self.assertEqual(discrete[0], 0)

    def test_observed_terminal_returns_and_calibration(self):
        np.testing.assert_allclose(discounted([0., .1, 1.], .9), [.9, 1., 1.])
        exact = fit_stats([1., 2., 3.], [1., 2., 3.])
        self.assertEqual(exact['rmse'], 0)
        self.assertEqual(exact['explainedVariance'], 1)
        biased = fit_stats([3., 4., 5.], [1., 2., 3.])
        self.assertEqual(biased['bias'], 2)
        self.assertEqual(biased['rmse'], 2)
        self.assertEqual(biased['explainedVariance'], 1)  # EV alone misses bias.

    def test_task_labels_and_conflict_sign(self):
        self.assertEqual(len({task_key(i) for i in range(256)}), 10)
        self.assertEqual(cosine(np.array([1., 0]), np.array([-1., 0])), -1)
        self.assertIsNone(cosine(np.zeros(2), np.ones(2)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
