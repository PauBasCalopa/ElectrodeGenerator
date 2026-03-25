"""
Profile parameter optimization using golden-section search.

Minimizes field enhancement (ΔE%) by varying a single profile
parameter and running FEMM simulations at each candidate value.

The field-enhancement metric uses the analytical uniform field
``E_uniform = |V_top − V_bot| / gap`` as the reference, which is
independent of mesh resolution and contour sampling position.
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(self, param_name, bounds, tolerance, max_iter, callback=None,
                 cancel_flag=None):
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
            e_uniform = self._e_uniform()
            if callback:
                callback('log', f"FEMM opened. Optimizing '{param_name}'...")
                callback('log', f"  Range: [{bounds[0]}, {bounds[1]}]")
                callback('log', f"  Tolerance: {tolerance}")
                callback('log', f"  E_uniform: {e_uniform:.4f} V/unit\n")

            gr = (math.sqrt(5) + 1) / 2
            a, b = bounds
            best_val, best_fef = None, float('inf')

            # Golden-section cache: keep the interior point that is
            # NOT discarded so we only need 1 new simulation per
            # iteration instead of 2.
            c = b - (b - a) / gr
            d = a + (b - a) / gr
            fef_c = self._evaluate(sim, param_name, c, e_uniform)
            fef_d = self._evaluate(sim, param_name, d, e_uniform)

            for iteration in range(max_iter):
                if cancel_flag and cancel_flag.is_set():
                    if callback:
                        callback('log', "\nOptimization cancelled.")
                    return {}

                if abs(b - a) < tolerance:
                    if callback:
                        callback('log', "Converged (parameter interval).")
                    break

                if fef_c < fef_d:
                    b = d
                    val, fef = c, fef_c
                    # d moves to old c; recompute only the new c
                    d, fef_d = c, fef_c
                    c = b - (b - a) / gr
                    fef_c = self._evaluate(sim, param_name, c, e_uniform)
                else:
                    a = c
                    val, fef = d, fef_d
                    # c moves to old d; recompute only the new d
                    c, fef_c = d, fef_d
                    d = a + (b - a) / gr
                    fef_d = self._evaluate(sim, param_name, d, e_uniform)

                prev_best = best_fef
                if fef < best_fef:
                    best_fef = fef
                    best_val = val

                if callback:
                    callback('progress', iteration + 1, param_name, val, fef)

                # Dual convergence: stop if ΔE% improvement is negligible
                if abs(prev_best - best_fef) < tolerance * 0.01 and iteration > 0:
                    if callback:
                        callback('log', "Converged (\u0394E% stable).")
                    break

            # Final run at optimum to capture E-field data
            result = {}
            if best_val is not None:
                cfg = dict(self.base_config)
                cfg[param_name] = best_val
                final_gap = self.gap
                final_plate = self.plate_length
                if param_name == 's':
                    final_gap = best_val
                    e_uniform = self._e_uniform_for(final_gap)
                elif param_name == 'd':
                    final_plate = best_val
                x, y = self.profile.generate_points(cfg)
                is_axi = self.femm_config.get('problem_type') == 'axi'
                use_sym = self.femm_config.get('use_symmetry', False)
                curves = build_assembly_curves(x, y, final_gap, final_plate,
                                               is_axi=is_axi, use_symmetry=use_sym)
                sim.build_and_solve(curves, self.femm_config)
                contour = build_top_contour(curves)
                dist, evals = sim.get_field_along_contour(contour)

                result = {
                    'param_name': param_name,
                    'best_value': best_val,
                    'best_delta_e': best_fef,
                    'distances': dist,
                    'e_values': evals,
                    'e_uniform': e_uniform,
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

    def sweep(self, param_name, bounds, num_steps, callback=None,
              cancel_flag=None):
        """Evaluate ΔE% at evenly spaced parameter values.

        Args:
            param_name: Profile parameter to sweep.
            bounds: (min, max) range.
            num_steps: Number of evaluation points.
            callback: Optional ``callback(event, *args)``.

        Returns:
            List of ``(param_value, delta_e)`` pairs.
        """
        from simulation.femm_simulator import FEMMSimulator

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            e_uniform = self._e_uniform()
            if callback:
                callback('log', f"FEMM opened. Sweeping '{param_name}'...")
                callback('log', f"  Range: [{bounds[0]}, {bounds[1]}]")
                callback('log', f"  Steps: {num_steps}")
                callback('log', f"  E_uniform: {e_uniform:.4f} V/unit\n")

            lo, hi = bounds
            results = []
            for i in range(num_steps):
                if cancel_flag and cancel_flag.is_set():
                    if callback:
                        callback('log', "\nSweep cancelled.")
                    return results

                val = lo + i * (hi - lo) / max(num_steps - 1, 1)
                fef = self._evaluate(sim, param_name, val, e_uniform)
                results.append((val, fef))

                if callback:
                    callback('progress', i + 1, param_name, val, fef)

            if callback:
                best = min(results, key=lambda r: r[1])
                callback('log', "")
                callback('log',
                         f"SWEEP BEST: {param_name} = {best[0]:.6f}  "
                         f"(\u0394E = {best[1]:.2f}%)")
                callback('sweep_complete', results)

            return results
        finally:
            sim.close()

    def optimize_multi(self, param_names, bounds_dict, tolerance, max_iter,
                       max_rounds=5, callback=None, cancel_flag=None):
        """Sequentially optimize multiple parameters until convergence.

        Cycles through *param_names* one at a time, running
        golden-section on each while holding the others fixed at
        their current best values.  Stops when a full cycle produces
        no improvement larger than *tolerance* or *max_rounds* is
        reached.

        Args:
            param_names: List of parameter names to optimize.
            bounds_dict: ``{name: (min, max)}`` bounds for each parameter.
            tolerance: Convergence threshold (parameter interval).
            max_iter: Max iterations per single-parameter optimization.
            max_rounds: Max full cycles over all parameters.

        Returns:
            Dict with keys: best_values (dict), best_delta_e,
            distances, e_values, e_uniform.
        """
        from simulation.femm_simulator import FEMMSimulator

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            e_uniform = self._e_uniform()
            best_values = {p: self.base_config.get(p, 0) for p in param_names}
            best_fef = float('inf')

            if callback:
                callback('log', f"Multi-parameter optimization: {param_names}")
                callback('log', f"  Max rounds: {max_rounds}")
                callback('log', f"  E_uniform: {e_uniform:.4f} V/unit\n")

            for rnd in range(max_rounds):
                if cancel_flag and cancel_flag.is_set():
                    if callback:
                        callback('log', "\nOptimization cancelled.")
                    return {}

                if callback:
                    callback('log', f"--- Round {rnd + 1} ---")

                round_improved = False

                for pname in param_names:
                    if cancel_flag and cancel_flag.is_set():
                        return {}

                    # Update base_config with current best values
                    cfg = dict(self.base_config)
                    cfg.update(best_values)

                    a, b = bounds_dict[pname]
                    gr = (math.sqrt(5) + 1) / 2
                    c = b - (b - a) / gr
                    d = a + (b - a) / gr

                    # Temporarily set base_config and assembly params
                    saved = dict(self.base_config)
                    saved_gap = self.gap
                    saved_plate = self.plate_length
                    self.base_config = cfg
                    if 's' in best_values:
                        self.gap = best_values['s']
                    if 'd' in best_values:
                        self.plate_length = best_values['d']
                    local_e_uniform = self._e_uniform()

                    fef_c = self._evaluate(sim, pname, c, local_e_uniform)
                    fef_d = self._evaluate(sim, pname, d, local_e_uniform)

                    local_best_val = None
                    local_best_fef = float('inf')

                    for it in range(max_iter):
                        if cancel_flag and cancel_flag.is_set():
                            self.base_config = saved
                            self.gap = saved_gap
                            self.plate_length = saved_plate
                            return {}

                        if abs(b - a) < tolerance:
                            break

                        if fef_c < fef_d:
                            b = d
                            val, fef = c, fef_c
                            d, fef_d = c, fef_c
                            c = b - (b - a) / gr
                            fef_c = self._evaluate(sim, pname, c, local_e_uniform)
                        else:
                            a = c
                            val, fef = d, fef_d
                            c, fef_c = d, fef_d
                            d = a + (b - a) / gr
                            fef_d = self._evaluate(sim, pname, d, local_e_uniform)

                        if fef < local_best_fef:
                            local_best_fef = fef
                            local_best_val = val

                        if callback:
                            callback('progress', it + 1, pname, val, fef)

                    self.base_config = saved
                    self.gap = saved_gap
                    self.plate_length = saved_plate

                    if local_best_val is not None and local_best_fef < best_fef:
                        best_values[pname] = local_best_val
                        best_fef = local_best_fef
                        round_improved = True

                    if callback and local_best_val is not None:
                        callback('log',
                                 f"  {pname} = {local_best_val:.6f}  "
                                 f"(\u0394E = {local_best_fef:.2f}%)")

                if not round_improved:
                    if callback:
                        callback('log', "\nNo improvement this round — converged.")
                    break

            # Final evaluation at best values
            result = {}
            cfg = dict(self.base_config)
            cfg.update(best_values)
            final_gap = best_values.get('s', self.gap)
            final_plate = best_values.get('d', self.plate_length)
            if 's' in best_values:
                e_uniform = self._e_uniform_for(final_gap)
            x, y = self.profile.generate_points(cfg)
            is_axi = self.femm_config.get('problem_type') == 'axi'
            use_sym = self.femm_config.get('use_symmetry', False)
            curves = build_assembly_curves(x, y, final_gap, final_plate,
                                           is_axi=is_axi, use_symmetry=use_sym)
            sim.build_and_solve(curves, self.femm_config)
            contour = build_top_contour(curves)
            dist, evals = sim.get_field_along_contour(contour)

            result = {
                'best_values': best_values,
                'best_delta_e': best_fef,
                'distances': dist,
                'e_values': evals,
                'e_uniform': e_uniform,
            }

            if callback:
                vals_str = ", ".join(f"{k}={v:.6f}" for k, v in best_values.items())
                callback('log', "")
                callback('log',
                         f"OPTIMAL: {vals_str}  (\u0394E = {best_fef:.2f}%)")
                callback('multi_complete', result)

            return result
        finally:
            sim.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    # FEMM always returns E in V/m (SI).  Convert the model-unit gap
    # to metres so E_uniform matches the FEMM output.
    _UNIT_TO_METRE = {
        'millimeters': 1e-3,
        'centimeters': 1e-2,
        'meters':      1.0,
        'inches':      25.4e-3,
        'mils':        25.4e-6,
        'micrometers': 1e-6,
    }

    def _e_uniform(self):
        """Analytical uniform field between infinite parallel plates (V/m)."""
        return self._e_uniform_for(self.gap)

    def _e_uniform_for(self, gap):
        """Analytical uniform field for a given *gap* value (V/m)."""
        v_top = self.femm_config.get('voltage_top', 1000)
        v_bot = self.femm_config.get('voltage_bottom', 0)
        units = self.femm_config.get('units', 'millimeters')
        scale = self._UNIT_TO_METRE.get(units, 1e-3)
        gap_m = gap * scale
        if gap_m < 1e-15:
            return 1.0
        return abs(v_top - v_bot) / gap_m

    def _evaluate(self, sim, param_name, value, e_uniform):
        """Run one FEMM simulation and return the field enhancement %.

        The metric is ``(E_peak − E_uniform) / E_uniform × 100`` where
        ``E_uniform = |V_top − V_bot| / gap`` (in V/m, matching FEMM
        output) and ``E_peak`` is the 99th percentile of |E| along the
        measuring contour.

        Assembly-level parameters ``s`` (gap) and ``d`` (plate length)
        are handled transparently: when *param_name* is ``'s'`` the gap
        is updated and *e_uniform* is recomputed so the metric stays
        consistent.
        """
        cfg = dict(self.base_config)
        cfg[param_name] = value

        # Assembly-level overrides
        gap = self.gap
        plate_length = self.plate_length
        if param_name == 's':
            gap = value
            # Recompute reference field for the new gap
            e_uniform = self._e_uniform_for(gap)
        elif param_name == 'd':
            plate_length = value

        x, y = self.profile.generate_points(cfg)
        is_axi = self.femm_config.get('problem_type') == 'axi'
        use_sym = self.femm_config.get('use_symmetry', False)
        curves = build_assembly_curves(x, y, gap, plate_length,
                                       is_axi=is_axi, use_symmetry=use_sym)

        sim.build_and_solve(curves, self.femm_config)

        contour = build_top_contour(curves)
        _, e_values = sim.get_field_along_contour(contour)
        if not e_values or len(e_values) < 5:
            return float('inf')

        if e_uniform < 1e-10:
            return float('inf')

        # Use the 99th percentile instead of max to ignore numerical
        # spikes at geometry junctions (cap-profile, plate-profile).
        sorted_e = sorted(e_values)
        idx_99 = int(len(sorted_e) * 0.99)
        e_peak = sorted_e[min(idx_99, len(sorted_e) - 1)]

        return (e_peak - e_uniform) / e_uniform * 100.0
