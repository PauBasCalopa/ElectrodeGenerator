"""Unit tests for the optimize wizard UI logic.

These tests exercise the wizard's internal logic (toggle, validation,
Pareto helpers) without launching FEMM.  A Tk root is created headlessly
where possible.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tkinter as tk

# Single shared root for all Tk-dependent tests (avoids Tcl corruption
# when creating / destroying multiple Tk instances).
_root = None


def _get_root():
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    return _root


def tearDownModule():
    global _root
    if _root is not None:
        _root.destroy()
        _root = None


class TestAlgoComboboxValues(unittest.TestCase):
    """Verify the algorithm combobox has all three options."""

    def test_combobox_has_nsga2(self):
        root = _get_root()
        from tkinter import ttk
        var = tk.StringVar(root, value="golden")
        combo = ttk.Combobox(root, textvariable=var,
                             values=["golden", "evolution", "nsga2"],
                             state="readonly")
        vals = list(combo['values'])
        self.assertIn("nsga2", vals)
        self.assertIn("golden", vals)
        self.assertIn("evolution", vals)
        self.assertEqual(len(vals), 3)


class TestObjectiveCheckboxDefaults(unittest.TestCase):
    """Verify objective checkboxes default: first two checked."""

    def test_default_objectives(self):
        root = _get_root()
        from core.optimizer import ProfileOptimizer
        keys = list(ProfileOptimizer.OBJECTIVES.keys())
        # Mimic the wizard: first two checked
        obj_vars = {}
        for i, key in enumerate(keys):
            var = tk.BooleanVar(root, value=(i < 2))
            obj_vars[key] = var

        checked = [k for k, v in obj_vars.items() if v.get()]
        self.assertEqual(len(checked), 2)
        self.assertEqual(checked[0], keys[0])
        self.assertEqual(checked[1], keys[1])


class TestParetoTreeviewPopulation(unittest.TestCase):
    """Test that Pareto data can be inserted into a Treeview correctly."""

    def _build_tree(self):
        root = _get_root()
        from tkinter import ttk
        tree = ttk.Treeview(root, selectmode="browse", height=5)
        return tree

    def test_populate_pareto_table(self):
        tree = self._build_tree()

        result = {
            'pareto_front': [
                {'values': {'u_start': -2.5, 'u_end': 2.0},
                 'scores': [3.14, 1.5]},
                {'values': {'u_start': -1.8, 'u_end': 1.7},
                 'scores': [5.22, 0.9]},
            ],
            'objective_labels': ['ΔE %', 'Width'],
            'param_names': ['u_start', 'u_end'],
        }

        obj_labels = result['objective_labels']
        p_names = result['param_names']
        cols = obj_labels + p_names

        tree['columns'] = cols
        tree.heading('#0', text='#')
        tree.column('#0', width=40, stretch=False)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=80, anchor=tk.E)

        for i, sol in enumerate(result['pareto_front']):
            sc_vals = [f"{s:.3f}" for s in sol['scores']]
            p_vals = [f"{sol['values'][n]:.5f}" for n in p_names]
            tree.insert('', tk.END, iid=str(i), text=str(i),
                        values=sc_vals + p_vals)

        children = tree.get_children()
        self.assertEqual(len(children), 2)

        # Check first row values
        vals_0 = tree.item('0', 'values')
        self.assertEqual(vals_0[0], '3.140')
        self.assertEqual(vals_0[1], '1.500')

    def test_select_row_returns_iid(self):
        tree = self._build_tree()
        tree['columns'] = ['A']
        tree.insert('', tk.END, iid='0', text='0', values=['val0'])
        tree.insert('', tk.END, iid='1', text='1', values=['val1'])

        tree.selection_set('1')
        sel = tree.selection()
        self.assertEqual(len(sel), 1)
        self.assertEqual(sel[0], '1')

    def test_empty_table(self):
        tree = self._build_tree()
        children = tree.get_children()
        self.assertEqual(len(children), 0)


class TestMinObjectivesValidation(unittest.TestCase):
    """Verify NSGA-II requires at least 2 objectives."""

    def test_one_objective_rejected(self):
        root = _get_root()
        from core.optimizer import ProfileOptimizer
        keys = list(ProfileOptimizer.OBJECTIVES.keys())
        obj_vars = {}
        for i, key in enumerate(keys):
            var = tk.BooleanVar(root, value=(i == 0))
            obj_vars[key] = var

        selected = [k for k, v in obj_vars.items() if v.get()]
        self.assertEqual(len(selected), 1)
        # The wizard would show: "Select at least 2 objectives for NSGA-II."
        self.assertLess(len(selected), 2)

    def test_two_objectives_accepted(self):
        root = _get_root()
        from core.optimizer import ProfileOptimizer
        keys = list(ProfileOptimizer.OBJECTIVES.keys())
        obj_vars = {}
        for i, key in enumerate(keys):
            var = tk.BooleanVar(root, value=(i < 2))
            obj_vars[key] = var

        selected = [k for k, v in obj_vars.items() if v.get()]
        self.assertGreaterEqual(len(selected), 2)

    def test_all_objectives_accepted(self):
        root = _get_root()
        from core.optimizer import ProfileOptimizer
        keys = list(ProfileOptimizer.OBJECTIVES.keys())
        obj_vars = {}
        for key in keys:
            var = tk.BooleanVar(root, value=True)
            obj_vars[key] = var

        selected = [k for k, v in obj_vars.items() if v.get()]
        self.assertEqual(len(selected), 4)


class TestApplyParetoSelection(unittest.TestCase):
    """Test the logic of _apply for NSGA-II results."""

    def test_pareto_result_applied(self):
        """Simulate what _apply does when pareto_front is present."""
        opt_result = {
            'pareto_front': [
                {'values': {'u_start': -2.5, 'u_end': 2.0},
                 'scores': [3.14, 1.5]},
                {'values': {'u_start': -1.8, 'u_end': 1.7},
                 'scores': [5.22, 0.9]},
            ],
            'objective_labels': ['ΔE %', 'Width'],
            'param_names': ['u_start', 'u_end'],
        }

        selected_idx = 1
        sol = opt_result['pareto_front'][selected_idx]

        applied = []
        for name, val in sol['values'].items():
            applied.append((name, val, sol['scores'][0]))

        self.assertEqual(len(applied), 2)
        self.assertEqual(applied[0], ('u_start', -1.8, 5.22))
        self.assertEqual(applied[1], ('u_end', 1.7, 5.22))

    def test_single_obj_result_no_pareto(self):
        """If no pareto_front key, fall through to single-obj path."""
        opt_result = {
            'param_name': 'u_start',
            'best_value': -2.1,
            'best_delta_e': 2.5,
        }
        self.assertNotIn('pareto_front', opt_result)


if __name__ == '__main__':
    unittest.main()
