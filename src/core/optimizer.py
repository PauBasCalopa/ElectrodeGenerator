"""
Profile parameter optimization using golden-section search.

Minimizes field enhancement (ΔE%) by varying a single profile
parameter and running FEMM simulations at each candidate value.
"""

import math

from core.assembly import build_assembly_curves
from core.contour import build_top_contour


class ProfileOptimizer:
    """Optimizes a profile parameter to minimize field enhancement."""

    def __init__(self, profile, base_config, gap, plate_length, femm_config):
        self.profile = profile
        self.base_config = base_config
        self.gap = gap
        self.plate_length = plate_length
        self.femm_config = femm_config

    def optimize(self, param_name, bounds, tolerance, max_iter, callback=None):
        """Run golden-section search.

        Args:
            param_name: Name of the profile parameter to optimize.
            bounds: (min, max) search range.
            tolerance: Convergence threshold on the parameter interval.
            max_iter: Maximum number of iterations.
            callback: Optional ``callback(event, *args)`` called with:
                - ``('log', message)`` for informational messages
                - ``('progress', iteration, param_name, value, delta_e)``
                - ``('complete', result_dict)``

        Returns:
            Dict with keys: param_name, best_value, best_delta_e,
            distances, e_values.  Empty dict if optimization fails.
        """
        from simulation.femm_simulator import FEMMSimulator

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            if callback:
                callback('log', f"FEMM opened. Optimizing '{param_name}'...")
                callback('log', f"  Range: [{bounds[0]}, {bounds[1]}]")
                callback('log', f"  Tolerance: {tolerance}\n")

            gr = (math.sqrt(5) + 1) / 2
            a, b = bounds
            best_val, best_fef = None, float('inf')

            for iteration in range(max_iter):
                if abs(b - a) < tolerance:
                    if callback:
                        callback('log', "Converged.")
                    break

                c = b - (b - a) / gr
                d = a + (b - a) / gr

                fef_c = self._evaluate(sim, param_name, c)
                fef_d = self._evaluate(sim, param_name, d)

                if fef_c < fef_d:
                    b = d
                    val, fef = c, fef_c
                else:
                    a = c
                    val, fef = d, fef_d

                if fef < best_fef:
                    best_fef = fef
                    best_val = val

                if callback:
                    callback('progress', iteration + 1, param_name, val, fef)

            # Final run at optimum to capture E-field data
            result = {}
            if best_val is not None:
                cfg = dict(self.base_config)
                cfg[param_name] = best_val
                x, y = self.profile.generate_points(cfg)
                curves = build_assembly_curves(x, y, self.gap, self.plate_length)
                sim.build_and_solve(curves, self.femm_config)
                contour = build_top_contour(curves)
                dist, evals = sim.get_field_along_contour(contour)

                result = {
                    'param_name': param_name,
                    'best_value': best_val,
                    'best_delta_e': best_fef,
                    'distances': dist,
                    'e_values': evals,
                }

                if callback:
                    callback('log', "")
                    callback('log',
                             f"OPTIMAL: {param_name} = {best_val:.6f}  "
                             f"(\u0394E = {best_fef:.2f}%)")
                    callback('complete', result)

            return result
        finally:
            sim.close()

    def _evaluate(self, sim, param_name, value):
        """Run one FEMM simulation and return the field enhancement %.

        The metric is (E_max - E_center) / E_center * 100, computed
        along the top electrode contour.
        """
        cfg = dict(self.base_config)
        cfg[param_name] = value
        x, y = self.profile.generate_points(cfg)
        curves = build_assembly_curves(x, y, self.gap, self.plate_length)

        sim.build_and_solve(curves, self.femm_config)

        contour = build_top_contour(curves)
        _, e_values = sim.get_field_along_contour(contour)
        if not e_values or len(e_values) < 5:
            return float('inf')

        e_center = e_values[len(e_values) // 2]
        if e_center < 1e-10:
            return float('inf')
        e_max = max(e_values)

        return (e_max - e_center) / e_center * 100.0
