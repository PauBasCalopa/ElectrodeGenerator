"""Integration test — run a short optimisation on ALL four profiles.

Exercises the full pipeline (profile → assembly → FEMM → evaluate)
for Rogowski, Chang, Ernst, and Bruce with both single-objective (DE)
and multi-objective (NSGA-II) algorithms.

Run from the repo root:
    python tests/test_all_profiles_optim.py
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from simulation.femm_simulator import HAS_FEMM
    if not HAS_FEMM:
        raise ImportError
except (ImportError, RuntimeError):
    print("SKIP: pyfemm / FEMM 4.2 not available.")
    sys.exit(0)


# ── Per-profile test configuration ───────────────────────────────────

PROFILE_TESTS = {
    'Rogowski': {
        'base_config': {
            'u_start': -3.0,
            'u_end': 2.5,
            'num_points': 100,
        },
        'de_params': [
            {'name': 'u_start', 'min': -6.0, 'max': -0.5},
            {'name': 'u_end',   'min': 0.5,  'max': 4.0},
        ],
        'gs_param': ('u_end', (0.5, 4.0)),
    },
    'Chang': {
        'base_config': {
            'k': 0.85,
            'u_end': 2.0,
            'num_points': 100,
        },
        'de_params': [
            {'name': 'k',     'min': 0.1,  'max': 1.5},
            {'name': 'u_end', 'min': 0.5,  'max': 4.0},
        ],
        'gs_param': ('k', (0.1, 1.5)),
    },
    'Ernst': {
        'base_config': {
            'k0': 0.3,
            'u_end': 3.0,
            'num_points': 100,
        },
        'de_params': [
            {'name': 'k0',    'min': 0.01, 'max': 1.2},
            {'name': 'u_end', 'min': 0.5,  'max': 6.0},
        ],
        'gs_param': ('k0', (0.01, 0.8)),
    },
    'Bruce': {
        'base_config': {
            'alpha_0': 10.0,
            'num_points': 100,
        },
        'de_params': [
            {'name': 'alpha_0', 'min': 2.0, 'max': 40.0},
        ],
        'gs_param': ('alpha_0', (2.0, 40.0)),
    },
}

FEMM_CONFIG = {
    'problem_type': 'axi',
    'units': 'millimeters',
    'depth': 1.0,
    'voltage_top': 1000.0,
    'voltage_bottom': 0.0,
    'epsilon_r': 1.0,
    'mesh_size': 0,
    'use_symmetry': True,
}


def _log_callback(event, *args):
    if event == 'log':
        print(f"    {args[0]}")
    elif event == 'generation':
        pass
    elif event == 'progress':
        it, pname, val, de = args
        print(f"    Iter {it}: {pname}={val:.5f}  ΔE={de:.2f}%")
    elif event == 'complete':
        r = args[0]
        print(f"    → {r['param_name']}={r['best_value']:.5f}"
              f"  ΔE={r['best_delta_e']:.2f}%")
    elif event in ('evolution_complete', 'multi_complete'):
        r = args[0]
        vs = ", ".join(f"{k}={v:.4f}" for k, v in r['best_values'].items())
        print(f"    → {vs}  ΔE={r['best_delta_e']:.2f}%")
    elif event == 'nsga2_complete':
        r = args[0]
        n = len(r.get('pareto_front', []))
        print(f"    → Pareto front: {n} solutions")
        for i, sol in enumerate(r['pareto_front'][:5]):
            sc = ", ".join(f"{s:.2f}" for s in sol['scores'])
            print(f"      [{i}] scores=[{sc}]")
        if n > 5:
            print(f"      ... ({n - 5} more)")


def main():
    import pythoncom
    pythoncom.CoInitialize()

    from core.profiles import PROFILES
    from core.optimizer import ProfileOptimizer

    gap = 1.0
    plate_length = 2.0
    cancel = threading.Event()
    all_passed = True
    results = {}

    for profile_name, tcfg in PROFILE_TESTS.items():
        profile = PROFILES[profile_name]
        base = dict(tcfg['base_config'])
        optimizer = ProfileOptimizer(profile, base, gap, plate_length,
                                     FEMM_CONFIG)

        print(f"\n{'=' * 64}")
        print(f"  PROFILE: {profile_name}")
        print(f"{'=' * 64}")

        # ── A) Golden-section ─────────────────────────────────────────
        gs_name, gs_bounds = tcfg['gs_param']
        print(f"\n  [A] Golden-section on '{gs_name}' {gs_bounds}")
        cancel.clear()
        t0 = time.perf_counter()
        try:
            r_gs = optimizer.optimize(
                gs_name, gs_bounds,
                tolerance=0.2, max_iter=4,
                callback=_log_callback, cancel_flag=cancel)
            elapsed = time.perf_counter() - t0
            if r_gs and 'best_value' in r_gs:
                tag = "✓" if r_gs['best_delta_e'] < float('inf') else "⚠ (all inf)"
                print(f"  {tag} {gs_name}={r_gs['best_value']:.5f}"
                      f"  ΔE={r_gs['best_delta_e']:.2f}%  ({elapsed:.1f}s)")
            else:
                print(f"  ⚠ No result ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ✗ CRASH: {e}")
            all_passed = False

        # ── B) DE (multi-param where available) ───────────────────────
        de_params = tcfg['de_params']
        pnames = [p['name'] for p in de_params]
        print(f"\n  [B] Differential Evolution on {pnames}")
        cancel.clear()
        t0 = time.perf_counter()
        try:
            r_de = optimizer.optimize_evolution(
                de_params,
                population_size=4,
                generations=2,
                mutation_factor=0.8,
                crossover_prob=0.7,
                callback=_log_callback, cancel_flag=cancel)
            elapsed = time.perf_counter() - t0
            if r_de and 'best_values' in r_de:
                tag = "✓" if r_de['best_delta_e'] < float('inf') else "⚠ (all inf)"
                vs = ", ".join(f"{k}={v:.4f}" for k, v in r_de['best_values'].items())
                print(f"  {tag} {vs}  ΔE={r_de['best_delta_e']:.2f}%  ({elapsed:.1f}s)")
            else:
                print(f"  ⚠ No result ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ✗ CRASH: {e}")
            all_passed = False

        # ── C) NSGA-II (ΔE% + compactness) ───────────────────────────
        print(f"\n  [C] NSGA-II on {pnames}, objectives: ΔE% + Width")
        cancel.clear()
        t0 = time.perf_counter()
        try:
            r_ns = optimizer.optimize_nsga2(
                de_params,
                objective_keys=['delta_e', 'compactness'],
                population_size=4,
                generations=2,
                mutation_factor=0.8,
                crossover_prob=0.7,
                callback=_log_callback, cancel_flag=cancel)
            elapsed = time.perf_counter() - t0
            if r_ns and r_ns.get('pareto_front'):
                pareto = r_ns['pareto_front']
                inf_count = sum(1 for sol in pareto
                                for s in sol['scores']
                                if s == float('inf'))
                if inf_count:
                    print(f"  ⚠ Pareto has {len(pareto)} solutions"
                          f" but {inf_count} inf scores  ({elapsed:.1f}s)")
                else:
                    print(f"  ✓ Pareto: {len(pareto)} solutions,"
                          f" all finite  ({elapsed:.1f}s)")
            else:
                print(f"  ⚠ No result ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ✗ CRASH: {e}")
            all_passed = False

        results[profile_name] = {
            'gs': r_gs if 'r_gs' in dir() else None,
            'de': r_de if 'r_de' in dir() else None,
            'nsga2': r_ns if 'r_ns' in dir() else None,
        }

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'=' * 64}")
    if all_passed:
        print("  ALL PROFILES PASSED — no crashes")
    else:
        print("  SOME PROFILES FAILED — see above")
    print(f"{'=' * 64}\n")

    pythoncom.CoUninitialize()
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
