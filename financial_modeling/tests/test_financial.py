from fractions import Fraction
import unittest
import numpy as np
from sc4055.model import P, NEXT, LABELS, condition, dp, enumerate_words, SPEC

class TestFinancial(unittest.TestCase):
    def test_probabilities(self):
        self.assertEqual(P.shape,(9,3))
        self.assertTrue(np.all(P >= 0))
        np.testing.assert_allclose(P.sum(axis=1), np.ones(9), atol=1e-12)
        for s in range(9):
            for x in range(3):
                self.assertEqual(int(NEXT[s,x]), 3*(s%3)+x)

    def test_conditioning(self):
        self.assertEqual(condition([0,1,2]), 5)
        with self.assertRaises(ValueError): condition([2])

    def test_exact_independent(self):
        for s in range(9):
            enum = enumerate_words(s,L=6,rational=True)
            p = sum(v for word,v in enum.items() if sum(((word>>(2*t))&3)==2 for t in range(6))>=3)
            self.assertEqual(p, dp(s,rational=True))

    def test_known_reference(self):
        self.assertAlmostEqual(float(dp(0,rational=True)), .002027002, places=8)
        self.assertAlmostEqual(float(dp(8,rational=True)), .782373984, places=8)

if __name__=='__main__': unittest.main()
