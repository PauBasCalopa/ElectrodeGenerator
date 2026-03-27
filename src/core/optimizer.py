"""
Profile parameter optimization.

Provides three optimization strategies:

* **Golden-section search** — fast 1D line search for single
  parameters (or sequential multi-parameter).
* **Differential Evolution (DE)** — population-based global
  optimizer that searches all selected parameters simultaneously,
  capturing parameter interactions.
* **NSGA-II** — multi-objective evolutionary optimizer that
  produces a Pareto front of trade-off solutions (e.g. minimise
  ΔE% *and* maximise compactness simultaneously).

The field-enhancement metric uses the analytical uniform field
``E_uniform = |V_top − V_bot| / gap`` as the reference, which is
independent of mesh resolution and contour sampling position.
"""

import math
import random
import statistics

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

            # Seed best from initial evaluations
            if fef_c < fef_d:
                best_val, best_fef = c, fef_c
            else:
                best_val, best_fef = d, fef_d

            for iteration in range(max_iter):
                if cancel_flag and cancel_flag.is_set():
                    if callback:
                        callback('log', "\nStopped — returning best so far.")
                    break

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
            if best_val is not None and best_fef < float('inf'):
                try:
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
                except Exception:
                    result = {
                        'param_name': param_name,
                        'best_value': best_val,
                        'best_delta_e': best_fef,
                        'distances': [],
                        'e_values': [],
                        'e_uniform': e_uniform,
                    }

                if callback:
                    callback('log', "")
                    callback('log',
                             f"OPTIMAL: {param_name} = {best_val:.6f}  "
                             f"(\u0394E = {best_fef:.2f}%)")
                    callback('complete', result)
            elif callback:
                callback('log', "\nNo valid geometry found in search range.")

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
                    if fef == float('inf'):
                        callback('progress', i + 1, param_name, val, fef)
                        callback('log', f"    (skipped — solver error)")
                    else:
                        callback('progress', i + 1, param_name, val, fef)

            if callback:
                valid = [(v, f) for v, f in results if f != float('inf')]
                if valid:
                    best = min(valid, key=lambda r: r[1])
                    callback('log', "")
                    callback('log',
                             f"SWEEP BEST: {param_name} = {best[0]:.6f}  "
                             f"(\u0394E = {best[1]:.2f}%)")
                else:
                    callback('log', "")
                    callback('log',
                             f"SWEEP: all {num_steps} steps failed.")
                callback('sweep_complete', results)

            return results
        finally:
            sim.close()

    def sweep_multi(self, param_list, num_steps, callback=None,
                    cancel_flag=None):
        """Sweep multiple parameters one at a time.

        Opens FEMM once, sweeps each parameter independently while
        holding all others at their current values, then closes FEMM.

        Args:
            param_list: List of ``{'name': str, 'min': float, 'max': float}``
                dicts (same format returned by the param selector).
            num_steps: Number of evaluation points per parameter.
            callback: Optional ``callback(event, *args)``.
            cancel_flag: Optional ``threading.Event`` to cancel.

        Returns:
            Dict mapping ``param_name`` to list of ``(value, delta_e)``
            pairs.
        """
        from simulation.femm_simulator import FEMMSimulator

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            all_results = {}

            for idx, p in enumerate(param_list):
                if cancel_flag and cancel_flag.is_set():
                    if callback:
                        callback('log', "\nSweep cancelled.")
                    return all_results

                pname = p['name']
                lo, hi = p['min'], p['max']
                e_uniform = self._e_uniform()

                if callback:
                    callback('log',
                             f"=== Sweep {idx + 1}/{len(param_list)}: "
                             f"'{pname}' [{lo}, {hi}] ===")
                    callback('log', f"  Steps: {num_steps}")
                    callback('log', f"  E_uniform: {e_uniform:.4f} V/m\n")

                results = []
                for i in range(num_steps):
                    if cancel_flag and cancel_flag.is_set():
                        if callback:
                            callback('log', "\nSweep cancelled.")
                        return all_results

                    val = lo + i * (hi - lo) / max(num_steps - 1, 1)
                    fef = self._evaluate(sim, pname, val, e_uniform)
                    results.append((val, fef))

                    if callback:
                        if fef == float('inf'):
                            callback('progress', i + 1, pname, val, fef)
                            callback('log', f"    (skipped — solver error)")
                        else:
                            callback('progress', i + 1, pname, val, fef)

                all_results[pname] = results

                if callback and results:
                    valid = [(v, f) for v, f in results if f != float('inf')]
                    if valid:
                        best = min(valid, key=lambda r: r[1])
                        callback('log', "")
                        callback('log',
                                 f"  BEST: {pname} = {best[0]:.6f}  "
                                 f"(\u0394E = {best[1]:.2f}%)\n")
                    else:
                        callback('log', "")
                        callback('log',
                                 f"  {pname}: all steps failed.\n")

            if callback:
                callback('sweep_multi_complete', all_results)

            return all_results
        finally:
            sim.close()

    def optimize_evolution(self, param_list, population_size=16,
                           generations=30, mutation_factor=0.8,
                           crossover_prob=0.7, callback=None,
                           cancel_flag=None):
        """Optimize parameters using Differential Evolution (DE/rand/1/bin).

        Evolves a *population* of candidate parameter vectors over
        multiple *generations*.  Unlike golden-section, DE searches
        all parameters simultaneously so it captures interactions.

        Args:
            param_list: List of ``{'name': str, 'min': float, 'max': float}``
                dicts (same format returned by the param selector).
            population_size: Number of individuals (≥ 4).
            generations: Maximum number of generations.
            mutation_factor: DE scale factor *F* ∈ (0, 2]. Controls the
                amplification of differential variation.
            crossover_prob: Crossover probability *CR* ∈ [0, 1].
            callback: Optional ``callback(event, *args)``.
            cancel_flag: Optional ``threading.Event`` to cancel.

        Returns:
            Dict with keys: best_values, best_delta_e, distances,
            e_values, e_uniform.
        """
        from simulation.femm_simulator import FEMMSimulator

        n_params = len(param_list)
        pop_size = max(population_size, 4)
        names = [p['name'] for p in param_list]
        lo = [p['min'] for p in param_list]
        hi = [p['max'] for p in param_list]

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            e_uniform = self._e_uniform()

            if callback:
                callback('log', "Differential Evolution")
                callback('log', f"  Parameters: {names}")
                callback('log', f"  Population: {pop_size}")
                callback('log', f"  Generations: {generations}")
                callback('log', f"  F = {mutation_factor},  CR = {crossover_prob}")
                callback('log', f"  E_uniform: {e_uniform:.4f} V/m")
                callback('log', f"  Budget: ≤ {pop_size * (generations + 1)} simulations\n")

            # --- Initialise population uniformly within bounds ----------
            population = []
            for _ in range(pop_size):
                ind = [random.uniform(lo[j], hi[j]) for j in range(n_params)]
                population.append(ind)

            # Evaluate initial population
            fitness = []
            for i, ind in enumerate(population):
                if cancel_flag and cancel_flag.is_set():
                    break
                fef = self._evaluate_vector(sim, names, ind, e_uniform)
                fitness.append(fef)

            if len(fitness) < pop_size:
                # Stopped during initial evaluation — not enough data
                if callback:
                    callback('log', "\nStopped during initial population.")
                return {}

            best_idx = min(range(pop_size), key=lambda k: fitness[k])
            best_ind = list(population[best_idx])
            best_fef = fitness[best_idx]

            if callback:
                vals_str = ", ".join(f"{names[j]}={best_ind[j]:.4f}"
                                     for j in range(n_params))
                callback('log',
                         f"Gen  0: best \u0394E = {best_fef:.2f}%  ({vals_str})")

            # --- Evolution loop ----------------------------------------
            stopped = False
            for gen in range(1, generations + 1):
                if cancel_flag and cancel_flag.is_set():
                    stopped = True
                    break

                for i in range(pop_size):
                    if cancel_flag and cancel_flag.is_set():
                        stopped = True
                        break

                    # Pick three distinct donors ≠ i
                    candidates = [c for c in range(pop_size) if c != i]
                    a, b, c = random.sample(candidates, 3)

                    # Mutant vector: donor = pop[a] + F*(pop[b] - pop[c])
                    mutant = [
                        population[a][j]
                        + mutation_factor * (population[b][j] - population[c][j])
                        for j in range(n_params)
                    ]

                    # Clip to bounds
                    mutant = [max(lo[j], min(hi[j], mutant[j]))
                              for j in range(n_params)]

                    # Binomial crossover
                    j_rand = random.randrange(n_params)
                    trial = [
                        mutant[j] if (random.random() < crossover_prob
                                      or j == j_rand)
                        else population[i][j]
                        for j in range(n_params)
                    ]

                    # Selection
                    trial_fef = self._evaluate_vector(
                        sim, names, trial, e_uniform)
                    if trial_fef <= fitness[i]:
                        population[i] = trial
                        fitness[i] = trial_fef

                if stopped:
                    break

                # Track generation best
                gen_best_idx = min(range(pop_size), key=lambda k: fitness[k])
                if fitness[gen_best_idx] < best_fef:
                    best_fef = fitness[gen_best_idx]
                    best_ind = list(population[gen_best_idx])

                if callback:
                    vals_str = ", ".join(
                        f"{names[j]}={best_ind[j]:.4f}"
                        for j in range(n_params))
                    callback('log',
                             f"Gen {gen:2d}: best \u0394E = {best_fef:.2f}%"
                             f"  ({vals_str})")
                    callback('generation', gen, best_fef, best_ind)

            if stopped and callback:
                callback('log', "\nStopped — returning best so far.")

            # --- Final evaluation at best individual -------------------
            best_values = {names[j]: best_ind[j] for j in range(n_params)}
            result = {
                'best_values': best_values,
                'best_delta_e': best_fef,
                'distances': [],
                'e_values': [],
                'e_uniform': e_uniform,
            }

            if best_fef < float('inf'):
                try:
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
                    result['distances'] = dist
                    result['e_values'] = evals
                    result['e_uniform'] = e_uniform
                except Exception:
                    pass  # keep result with empty field data

            if callback:
                vals_str = ", ".join(f"{k}={v:.6f}"
                                     for k, v in best_values.items())
                callback('log', "")
                callback('log',
                         f"OPTIMAL: {vals_str}  (\u0394E = {best_fef:.2f}%)")
                callback('evolution_complete', result)

            return result
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

            stopped = False
            for rnd in range(max_rounds):
                if cancel_flag and cancel_flag.is_set():
                    stopped = True
                    break

                if callback:
                    callback('log', f"--- Round {rnd + 1} ---")

                round_improved = False

                for pname in param_names:
                    if cancel_flag and cancel_flag.is_set():
                        stopped = True
                        break

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
                            stopped = True
                            break

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

                if stopped:
                    break

                if not round_improved:
                    if callback:
                        callback('log', "\nNo improvement this round — converged.")
                    break

            if stopped and callback:
                callback('log', "\nStopped — returning best so far.")

            # Final evaluation at best values
            result = {
                'best_values': best_values,
                'best_delta_e': best_fef,
                'distances': [],
                'e_values': [],
                'e_uniform': e_uniform,
            }

            if best_fef < float('inf'):
                try:
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
                    result['distances'] = dist
                    result['e_values'] = evals
                    result['e_uniform'] = e_uniform
                except Exception:
                    pass  # keep result with empty field data

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

        Returns ``inf`` if the geometry is invalid or the solver fails
        (e.g. negative radius in axisymmetric mode).
        """
        try:
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
        except Exception:
            return float('inf')

    def _evaluate_vector(self, sim, names, values, e_uniform):
        """Evaluate a multi-parameter candidate vector.

        Sets all *names* to the corresponding *values*, handles
        assembly-level overrides for ``s`` and ``d``, and returns
        the field enhancement %.

        Returns ``inf`` if the geometry is invalid or the solver fails.
        """
        try:
            cfg = dict(self.base_config)
            gap = self.gap
            plate_length = self.plate_length

            for name, val in zip(names, values):
                cfg[name] = val
                if name == 's':
                    gap = val
                elif name == 'd':
                    plate_length = val

            if 's' in cfg and cfg['s'] != self.gap:
                e_uniform = self._e_uniform_for(gap)

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

            sorted_e = sorted(e_values)
            idx_99 = int(len(sorted_e) * 0.99)
            e_peak = sorted_e[min(idx_99, len(sorted_e) - 1)]

            return (e_peak - e_uniform) / e_uniform * 100.0
        except Exception:
            return float('inf')

    # ------------------------------------------------------------------
    # Multi-objective helpers
    # ------------------------------------------------------------------

    # Available objectives — each is a short key, a display label, and
    # a callable ``(x, y, e_values, e_uniform) -> float`` where lower
    # is always better.
    OBJECTIVES = {
        'delta_e': {
            'label': 'ΔE %',
            'fn': None,  # set below
        },
        'compactness': {
            'label': 'Width',
            'fn': None,
        },
        'uniformity': {
            'label': 'CV(E) %',
            'fn': None,
        },
        'height': {
            'label': 'Height',
            'fn': None,
        },
    }

    @staticmethod
    def _obj_delta_e(x, y, e_values, e_uniform):
        """Field enhancement: (E_99th − E_uniform) / E_uniform × 100."""
        if e_uniform < 1e-10 or len(e_values) < 5:
            return float('inf')
        s = sorted(e_values)
        idx = int(len(s) * 0.99)
        e_peak = s[min(idx, len(s) - 1)]
        return (e_peak - e_uniform) / e_uniform * 100.0

    @staticmethod
    def _obj_compactness(x, y, e_values, e_uniform):
        """Electrode width: max(x) − min(x)."""
        return float(max(x) - min(x))

    @staticmethod
    def _obj_uniformity(x, y, e_values, e_uniform):
        """Field coefficient of variation: std(E)/mean(E) × 100."""
        if len(e_values) < 2:
            return float('inf')
        mn = statistics.mean(e_values)
        if mn < 1e-10:
            return float('inf')
        return statistics.stdev(e_values) / mn * 100.0

    @staticmethod
    def _obj_height(x, y, e_values, e_uniform):
        """Profile height: max(y) − min(y)."""
        return float(max(y) - min(y))

    # Wire static methods into OBJECTIVES dict.
    OBJECTIVES['delta_e']['fn'] = _obj_delta_e
    OBJECTIVES['compactness']['fn'] = _obj_compactness
    OBJECTIVES['uniformity']['fn'] = _obj_uniformity
    OBJECTIVES['height']['fn'] = _obj_height

    def _evaluate_objectives(self, sim, names, values, objective_keys):
        """Evaluate a candidate vector on multiple objectives.

        Returns a list of floats (one per objective, lower is better),
        or a list of ``inf`` if the simulation fails.
        """
        inf_result = [float('inf')] * len(objective_keys)
        try:
            cfg = dict(self.base_config)
            gap = self.gap
            plate_length = self.plate_length

            for name, val in zip(names, values):
                cfg[name] = val
                if name == 's':
                    gap = val
                elif name == 'd':
                    plate_length = val

            e_uniform = self._e_uniform_for(gap)

            x, y = self.profile.generate_points(cfg)
            is_axi = self.femm_config.get('problem_type') == 'axi'
            use_sym = self.femm_config.get('use_symmetry', False)
            curves = build_assembly_curves(x, y, gap, plate_length,
                                           is_axi=is_axi, use_symmetry=use_sym)

            sim.build_and_solve(curves, self.femm_config)

            contour = build_top_contour(curves)
            _, e_values = sim.get_field_along_contour(contour)
            if not e_values or len(e_values) < 5:
                return inf_result

            scores = []
            for key in objective_keys:
                fn = self.OBJECTIVES[key]['fn']
                scores.append(fn(x, y, e_values, e_uniform))
            return scores
        except Exception:
            return inf_result

    # ------------------------------------------------------------------
    # NSGA-II
    # ------------------------------------------------------------------

    def optimize_nsga2(self, param_list, objective_keys,
                       population_size=20, generations=30,
                       mutation_factor=0.8, crossover_prob=0.7,
                       callback=None, cancel_flag=None):
        """Multi-objective optimization using NSGA-II.

        Evolves a population toward the Pareto front of the selected
        objectives.  Uses DE-style mutation and crossover operators.

        Args:
            param_list: ``[{'name', 'min', 'max'}, ...]``
            objective_keys: List of keys from ``OBJECTIVES``
                (e.g. ``['delta_e', 'compactness']``).
            population_size: Number of individuals (≥ 4).
            generations: Maximum generations.
            mutation_factor: DE scale factor *F*.
            crossover_prob: Crossover probability *CR*.
            callback: ``callback(event, *args)``.
            cancel_flag: ``threading.Event`` to stop early.

        Returns:
            Dict with ``'pareto_front'`` — list of dicts, each with
            ``'values'`` (param dict) and ``'scores'`` (objective list).
        """
        from simulation.femm_simulator import FEMMSimulator

        n_params = len(param_list)
        n_obj = len(objective_keys)
        pop_size = max(population_size, 4)
        names = [p['name'] for p in param_list]
        lo = [p['min'] for p in param_list]
        hi = [p['max'] for p in param_list]
        obj_labels = [self.OBJECTIVES[k]['label'] for k in objective_keys]

        sim = FEMMSimulator()
        sim.open(hide=True)

        try:
            if callback:
                callback('log', "NSGA-II Multi-Objective Optimization")
                callback('log', f"  Parameters: {names}")
                callback('log', f"  Objectives: {obj_labels}")
                callback('log', f"  Population: {pop_size}")
                callback('log', f"  Generations: {generations}")
                callback('log',
                         f"  Budget: \u2264 {pop_size * (generations + 1) * 2}"
                         f" simulations\n")

            # --- Initialise population ---------------------------------
            population = []
            scores = []
            for _ in range(pop_size):
                ind = [random.uniform(lo[j], hi[j])
                       for j in range(n_params)]
                population.append(ind)

            for i, ind in enumerate(population):
                if cancel_flag and cancel_flag.is_set():
                    break
                sc = self._evaluate_objectives(sim, names, ind,
                                               objective_keys)
                scores.append(sc)

            if len(scores) < pop_size:
                if callback:
                    callback('log', "\nStopped during initial population.")
                return {}

            fronts = _non_dominated_sort(scores)
            if callback:
                callback('log',
                         f"Gen  0: {len(fronts[0])} solutions on front 0")

            # --- Main NSGA-II loop ------------------------------------
            stopped = False
            for gen in range(1, generations + 1):
                if cancel_flag and cancel_flag.is_set():
                    stopped = True
                    break

                # Create offspring via DE operators
                offspring = []
                off_scores = []
                for i in range(pop_size):
                    if cancel_flag and cancel_flag.is_set():
                        stopped = True
                        break

                    candidates = [c for c in range(pop_size) if c != i]
                    a, b, c = random.sample(candidates, 3)

                    mutant = [
                        population[a][j]
                        + mutation_factor
                        * (population[b][j] - population[c][j])
                        for j in range(n_params)
                    ]
                    mutant = [max(lo[j], min(hi[j], mutant[j]))
                              for j in range(n_params)]

                    j_rand = random.randrange(n_params)
                    trial = [
                        mutant[j]
                        if (random.random() < crossover_prob
                            or j == j_rand)
                        else population[i][j]
                        for j in range(n_params)
                    ]

                    sc = self._evaluate_objectives(
                        sim, names, trial, objective_keys)
                    offspring.append(trial)
                    off_scores.append(sc)

                if stopped:
                    break

                # Merge parent + offspring
                merged_pop = population + offspring
                merged_sc = scores + off_scores

                # Non-dominated sort on merged population
                merged_fronts = _non_dominated_sort(merged_sc)

                # Select best pop_size individuals
                new_pop = []
                new_sc = []
                for front in merged_fronts:
                    if len(new_pop) + len(front) <= pop_size:
                        for idx in front:
                            new_pop.append(merged_pop[idx])
                            new_sc.append(merged_sc[idx])
                    else:
                        # Fill remaining slots by crowding distance
                        cd = _crowding_distance(
                            [merged_sc[idx] for idx in front])
                        ranked = sorted(
                            range(len(front)),
                            key=lambda k: cd[k], reverse=True)
                        for k in ranked:
                            if len(new_pop) >= pop_size:
                                break
                            idx = front[k]
                            new_pop.append(merged_pop[idx])
                            new_sc.append(merged_sc[idx])
                        break

                population = new_pop
                scores = new_sc
                fronts = _non_dominated_sort(scores)

                if callback:
                    callback('log',
                             f"Gen {gen:2d}: "
                             f"{len(fronts[0])} solutions on front 0")
                    callback('generation', gen, len(fronts[0]), None)

            if stopped and callback:
                callback('log', "\nStopped — returning best front so far.")

            # --- Build Pareto front result ----------------------------
            fronts = _non_dominated_sort(scores)
            pareto = []
            for idx in fronts[0]:
                vals = {names[j]: population[idx][j]
                        for j in range(n_params)}
                pareto.append({
                    'values': vals,
                    'scores': scores[idx],
                })
            # Sort by first objective
            pareto.sort(key=lambda p: p['scores'][0])

            result = {
                'pareto_front': pareto,
                'objective_keys': objective_keys,
                'objective_labels': obj_labels,
                'param_names': names,
            }

            if callback:
                callback('log', "")
                callback('log',
                         f"Pareto front: {len(pareto)} solutions")
                header = "  ".join(f"{lb:>10s}" for lb in obj_labels)
                callback('log', f"  {'':>6s}  {header}")
                for i, p in enumerate(pareto):
                    sc_str = "  ".join(f"{s:10.3f}" for s in p['scores'])
                    callback('log', f"  [{i:3d}]  {sc_str}")
                callback('nsga2_complete', result)

            return result
        finally:
            sim.close()


# ----------------------------------------------------------------------
# Module-level NSGA-II helpers
# ----------------------------------------------------------------------

def _dominates(a, b):
    """Return True if solution *a* dominates *b* (all \u2264, at least one <)."""
    better = False
    for ai, bi in zip(a, b):
        if ai > bi:
            return False
        if ai < bi:
            better = True
    return better


def _non_dominated_sort(scores):
    """Fast non-dominated sort (Deb et al., 2002).

    Args:
        scores: list of objective-value lists (lower is better).

    Returns:
        List of fronts, each front a list of indices into *scores*.
    """
    n = len(scores)
    domination_count = [0] * n
    dominated_set = [[] for _ in range(n)]
    fronts = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if _dominates(scores[p], scores[q]):
                dominated_set[p].append(q)
            elif _dominates(scores[q], scores[p]):
                domination_count[p] += 1
        if domination_count[p] == 0:
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominated_set[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    # Remove trailing empty front
    if not fronts[-1]:
        fronts.pop()
    return fronts


def _crowding_distance(front_scores):
    """Compute crowding distance for one front.

    Args:
        front_scores: list of objective-value lists for the members
            of a single front.

    Returns:
        List of crowding distances (same length as *front_scores*).
    """
    n = len(front_scores)
    if n <= 2:
        return [float('inf')] * n

    n_obj = len(front_scores[0])
    distances = [0.0] * n

    for m in range(n_obj):
        order = sorted(range(n), key=lambda k: front_scores[k][m])
        obj_min = front_scores[order[0]][m]
        obj_max = front_scores[order[-1]][m]
        span = obj_max - obj_min if obj_max > obj_min else 1.0

        distances[order[0]] = float('inf')
        distances[order[-1]] = float('inf')
        for i in range(1, n - 1):
            distances[order[i]] += (
                (front_scores[order[i + 1]][m]
                 - front_scores[order[i - 1]][m]) / span
            )

    return distances
