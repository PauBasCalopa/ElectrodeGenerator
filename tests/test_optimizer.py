"""Unit tests for core.optimizer — NSGA-II helpers, objectives, and utilities."""

import math
import sys
import os
import unittest

# Ensure the src directory is on the path so we can import core.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.optimizer import (
    _dominates,
    _non_dominated_sort,
    _crowding_distance,
    ProfileOptimizer,
)


# ======================================================================
# _dominates
# ======================================================================

class TestDominates(unittest.TestCase):
    """Tests for the Pareto-dominance helper."""

    def test_strictly_better(self):
        self.assertTrue(_dominates([1, 2], [3, 4]))

    def test_equal_is_not_domination(self):
        self.assertFalse(_dominates([1, 2], [1, 2]))

    def test_partially_worse(self):
        self.assertFalse(_dominates([1, 5], [3, 4]))

    def test_one_equal_one_better(self):
        # a <= b on all, a < b on at least one  →  dominates
        self.assertTrue(_dominates([1, 2], [1, 3]))

    def test_all_worse(self):
        self.assertFalse(_dominates([5, 6], [1, 2]))

    def test_single_objective(self):
        self.assertTrue(_dominates([1], [2]))
        self.assertFalse(_dominates([2], [1]))

    def test_three_objectives(self):
        self.assertTrue(_dominates([1, 2, 3], [1, 2, 4]))
        self.assertFalse(_dominates([1, 2, 5], [1, 2, 4]))


# ======================================================================
# _non_dominated_sort
# ======================================================================

class TestNonDominatedSort(unittest.TestCase):
    """Tests for Deb's fast non-dominated sort."""

    def test_single_front(self):
        # All mutually non-dominated
        scores = [[1, 4], [2, 3], [3, 2], [4, 1]]
        fronts = _non_dominated_sort(scores)
        self.assertEqual(len(fronts), 1)
        self.assertEqual(sorted(fronts[0]), [0, 1, 2, 3])

    def test_two_fronts(self):
        scores = [[1, 1], [2, 2], [3, 3]]
        fronts = _non_dominated_sort(scores)
        self.assertEqual(len(fronts), 3)
        self.assertIn(0, fronts[0])    # [1,1] dominates all
        self.assertIn(1, fronts[1])    # [2,2] second front
        self.assertIn(2, fronts[2])    # [3,3] third front

    def test_empty_scores(self):
        fronts = _non_dominated_sort([])
        self.assertEqual(fronts, [])

    def test_one_solution(self):
        fronts = _non_dominated_sort([[5, 5]])
        self.assertEqual(len(fronts), 1)
        self.assertEqual(fronts[0], [0])

    def test_mixed_fronts(self):
        #  A=[1,5], B=[2,3], C=[5,1] → all non-dominated (front 0)
        #  D=[3,4] → dominated by B  (front 1)
        scores = [[1, 5], [2, 3], [5, 1], [3, 4]]
        fronts = _non_dominated_sort(scores)
        self.assertIn(0, fronts[0])
        self.assertIn(1, fronts[0])
        self.assertIn(2, fronts[0])
        self.assertIn(3, fronts[1])

    def test_all_identical(self):
        scores = [[2, 2], [2, 2], [2, 2]]
        fronts = _non_dominated_sort(scores)
        # No solution dominates another → single front
        self.assertEqual(len(fronts), 1)
        self.assertEqual(sorted(fronts[0]), [0, 1, 2])


# ======================================================================
# _crowding_distance
# ======================================================================

class TestCrowdingDistance(unittest.TestCase):
    """Tests for crowding distance computation."""

    def test_two_solutions_infinite(self):
        cd = _crowding_distance([[1, 4], [4, 1]])
        self.assertEqual(cd, [float('inf'), float('inf')])

    def test_one_solution(self):
        cd = _crowding_distance([[3, 3]])
        self.assertEqual(cd, [float('inf')])

    def test_boundary_points_infinite(self):
        front = [[1, 5], [2, 3], [5, 1]]
        cd = _crowding_distance(front)
        # Boundary solutions (min/max per objective) should be inf
        inf_count = sum(1 for d in cd if d == float('inf'))
        self.assertGreaterEqual(inf_count, 2)

    def test_interior_finite(self):
        front = [[1, 10], [3, 6], [5, 4], [9, 1]]
        cd = _crowding_distance(front)
        # Boundary indices (0 and 3) should be inf
        self.assertEqual(cd[0], float('inf'))
        self.assertEqual(cd[3], float('inf'))
        # Interior points should be finite and > 0
        self.assertGreater(cd[1], 0)
        self.assertNotEqual(cd[1], float('inf'))
        self.assertGreater(cd[2], 0)
        self.assertNotEqual(cd[2], float('inf'))

    def test_identical_scores(self):
        front = [[2, 2], [2, 2], [2, 2]]
        cd = _crowding_distance(front)
        # Boundaries are inf, interior may be 0 or inf; no crash
        self.assertEqual(len(cd), 3)


# ======================================================================
# Objective functions (static methods on ProfileOptimizer)
# ======================================================================

class TestObjectiveFunctions(unittest.TestCase):
    """Test the four NSGA-II objective functions."""

    def test_obj_delta_e_zero_enhancement(self):
        # All E values equal to E_uniform → ΔE ≈ 0
        e_vals = [100.0] * 200
        result = ProfileOptimizer._obj_delta_e([], [], e_vals, 100.0)
        self.assertAlmostEqual(result, 0.0, places=1)

    def test_obj_delta_e_positive(self):
        # 99 values at 100, 1 at 200 → peak ~ 200, ΔE ≈ 100%
        e_vals = [100.0] * 99 + [200.0]
        result = ProfileOptimizer._obj_delta_e([], [], e_vals, 100.0)
        self.assertGreater(result, 50.0)

    def test_obj_delta_e_degenerate(self):
        # e_uniform near zero → inf
        result = ProfileOptimizer._obj_delta_e([], [], [1.0, 2.0], 0.0)
        self.assertEqual(result, float('inf'))

    def test_obj_delta_e_too_few_points(self):
        result = ProfileOptimizer._obj_delta_e([], [], [1.0], 100.0)
        self.assertEqual(result, float('inf'))

    def test_obj_compactness(self):
        x = [0.0, 1.0, 2.0, 5.0]
        result = ProfileOptimizer._obj_compactness(x, [0, 0, 0, 0], [], 0)
        self.assertAlmostEqual(result, 5.0)

    def test_obj_compactness_single_point(self):
        result = ProfileOptimizer._obj_compactness([3.0], [0], [], 0)
        self.assertAlmostEqual(result, 0.0)

    def test_obj_uniformity_perfect(self):
        # All values the same → CV = 0
        e_vals = [50.0] * 100
        result = ProfileOptimizer._obj_uniformity([], [], e_vals, 0)
        self.assertAlmostEqual(result, 0.0, places=5)

    def test_obj_uniformity_varied(self):
        import statistics
        e_vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        expected = statistics.stdev(e_vals) / statistics.mean(e_vals) * 100
        result = ProfileOptimizer._obj_uniformity([], [], e_vals, 0)
        self.assertAlmostEqual(result, expected, places=3)

    def test_obj_uniformity_degenerate(self):
        result = ProfileOptimizer._obj_uniformity([], [], [0.0], 0)
        self.assertEqual(result, float('inf'))

    def test_obj_height(self):
        y = [1.0, 3.0, 7.0, 2.0]
        result = ProfileOptimizer._obj_height([], y, [], 0)
        self.assertAlmostEqual(result, 6.0)

    def test_obj_height_flat(self):
        result = ProfileOptimizer._obj_height([], [5.0, 5.0], [], 0)
        self.assertAlmostEqual(result, 0.0)


# ======================================================================
# OBJECTIVES registry
# ======================================================================

class TestObjectivesRegistry(unittest.TestCase):
    """Verify the OBJECTIVES dict is properly wired."""

    def test_all_keys_present(self):
        expected = {'delta_e', 'compactness', 'uniformity', 'height'}
        self.assertEqual(set(ProfileOptimizer.OBJECTIVES.keys()), expected)

    def test_all_have_label_and_fn(self):
        for key, obj in ProfileOptimizer.OBJECTIVES.items():
            self.assertIn('label', obj, f"{key} missing 'label'")
            self.assertIn('fn', obj, f"{key} missing 'fn'")
            self.assertTrue(callable(obj['fn']),
                            f"{key} 'fn' is not callable")

    def test_labels_non_empty(self):
        for key, obj in ProfileOptimizer.OBJECTIVES.items():
            self.assertTrue(len(obj['label']) > 0,
                            f"{key} has empty label")


# ======================================================================
# Integration-like: NDS + crowding work together
# ======================================================================

class TestNDSAndCrowdingIntegration(unittest.TestCase):
    """Test that sorting + crowding produce usable selection info."""

    def test_selection_pipeline(self):
        """Simulate one NSGA-II selection step (no FEMM needed)."""
        scores = [
            [1, 10],
            [2, 7],
            [4, 5],
            [6, 3],
            [10, 1],
            [3, 8],   # dominated by combination of 0+1
            [5, 6],   # mixed
        ]

        fronts = _non_dominated_sort(scores)
        self.assertGreaterEqual(len(fronts), 1)

        # Crowding on front 0
        front0_scores = [scores[i] for i in fronts[0]]
        cd = _crowding_distance(front0_scores)
        self.assertEqual(len(cd), len(fronts[0]))

        # Rank by crowding distance descending
        ranked = sorted(range(len(fronts[0])),
                        key=lambda k: cd[k], reverse=True)
        # Boundary solutions should be first (infinite crowding)
        self.assertEqual(cd[ranked[0]], float('inf'))

    def test_front0_is_non_dominated(self):
        """Every pair in front 0 should be mutually non-dominating."""
        scores = [[1, 5], [3, 3], [5, 1], [2, 4]]
        fronts = _non_dominated_sort(scores)
        front0 = fronts[0]
        for i in front0:
            for j in front0:
                if i != j:
                    self.assertFalse(
                        _dominates(scores[i], scores[j]),
                        f"scores[{i}] should not dominate scores[{j}] "
                        f"in front 0")


if __name__ == '__main__':
    unittest.main()
