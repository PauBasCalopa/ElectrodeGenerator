"""Integration test — run a short DE optimisation on the Ernst profile.

This exercises the full pipeline (profile → assembly → FEMM → evaluate)
and deliberately uses a parameter range that can produce geometries
with r < 0 in axisymmetric mode, verifying that the error-resilience
(try/except → inf) works correctly.

Run from the repo root:
    cd src
    python -m tests.test_ernst_optim
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# --- Check FEMM availability early ---
try:
    from simulation.femm_simulator import HAS_FEMM
    if not HAS_FEMM:
        raise ImportError
except (ImportError, RuntimeError):
    print("SKIP: pyfemm / FEMM 4.2 not available — cannot run integration test.")
    sys.exit(0)


def main():
    import pythoncom
    pythoncom.CoInitialize()

    from core.profiles import PROFILES
    from core.optimizer import ProfileOptimizer

    profile = PROFILES['Ernst']

    # Starting config — deliberately use a wide k0 range that will push
    # the geometry into invalid territory on some candidates.
    base_config = {
        'k0': 0.3,
        'u_end': 3.0,
        'num_points': 100,
    }
    gap = 1.0
    plate_length = 2.0
    femm_config = {
        'problem_type': 'axi',
        'units': 'millimeters',
        'depth': 1.0,
        'voltage_top': 1000.0,
        'voltage_bottom': 0.0,
        'epsilon_r': 1.0,
        'mesh_size': 0,
        'use_symmetry': True,
    }

    optimizer = ProfileOptimizer(profile, base_config, gap, plate_length,
                                 femm_config)

    # Collect log messages
    logs = []
    errors_skipped = 0

    def callback(event, *args):
        nonlocal errors_skipped
        if event == 'log':
            msg = args[0]
            logs.append(msg)
            print(msg)
            if 'skipped' in msg.lower() or 'inf' in msg.lower():
                errors_skipped += 1
        elif event == 'progress':
            it, pname, val, de = args
            msg = f"  Iter {it}: {pname} = {val:.6f}, ΔE = {de:.2f}%"
            logs.append(msg)
            print(msg)
        elif event == 'generation':
            gen, front_size, _ = args
            msg = f"  Gen {gen}: best-front = {front_size}"
            logs.append(msg)
            print(msg)
        elif event in ('complete', 'multi_complete', 'evolution_complete'):
            result = args[0]
            print(f"\n=== RESULT: {result} ===\n")
        elif event == 'nsga2_complete':
            result = args[0]
            n = len(result.get('pareto_front', []))
            print(f"\n=== NSGA-II RESULT: {n} solutions on Pareto front ===")
            for i, sol in enumerate(result['pareto_front']):
                sc = ", ".join(f"{s:.3f}" for s in sol['scores'])
                vs = ", ".join(f"{k}={v:.4f}" for k, v in sol['values'].items())
                print(f"  [{i}]  scores=[{sc}]  {vs}")
            print()

    cancel = threading.Event()

    # ── TEST 1: Golden-section on k0 ──────────────────────────────────
    print("=" * 60)
    print("TEST 1: Golden-section — optimise k0 (Ernst, axi)")
    print("         Range [0.01, 0.8] — should find valid geometries")
    print("=" * 60)
    t0 = time.perf_counter()
    result1 = optimizer.optimize(
        'k0', (0.01, 0.8), tolerance=0.05, max_iter=8,
        callback=callback, cancel_flag=cancel)
    t1 = time.perf_counter()
    print(f"  Elapsed: {t1 - t0:.1f}s")
    assert result1, "Golden-section returned empty result"
    assert 'best_value' in result1, "Missing best_value"
    print(f"  ✓ k0 = {result1['best_value']:.5f}, ΔE = {result1['best_delta_e']:.2f}%\n")

    # ── TEST 2: DE on k0 + u_end (wide range → geometry errors) ──────
    print("=" * 60)
    print("TEST 2: Differential Evolution — k0 + u_end (Ernst, axi)")
    print("         Wide range: k0 ∈ [0.01, 1.7], u_end ∈ [0.5, 8.0]")
    print("         Expect some solver errors → skipped via inf")
    print("=" * 60)
    param_list = [
        {'name': 'k0',    'min': 0.01, 'max': 1.7},
        {'name': 'u_end', 'min': 0.5,  'max': 8.0},
    ]
    t0 = time.perf_counter()
    result2 = optimizer.optimize_evolution(
        param_list,
        population_size=6,
        generations=4,
        mutation_factor=0.8,
        crossover_prob=0.7,
        callback=callback,
        cancel_flag=cancel)
    t1 = time.perf_counter()
    print(f"  Elapsed: {t1 - t0:.1f}s")
    assert result2, "DE returned empty result"
    assert 'best_values' in result2, "Missing best_values"
    assert result2['best_delta_e'] < float('inf'), "best_delta_e is inf"
    vals = result2['best_values']
    print(f"  ✓ k0 = {vals['k0']:.5f}, u_end = {vals['u_end']:.5f}")
    print(f"    ΔE = {result2['best_delta_e']:.2f}%\n")

    # ── TEST 3: NSGA-II on k0 + u_end, objectives: ΔE% + Width ──────
    print("=" * 60)
    print("TEST 3: NSGA-II — k0 + u_end, objectives: ΔE% + Width")
    print("=" * 60)
    t0 = time.perf_counter()
    result3 = optimizer.optimize_nsga2(
        param_list,
        objective_keys=['delta_e', 'compactness'],
        population_size=6,
        generations=4,
        mutation_factor=0.8,
        crossover_prob=0.7,
        callback=callback,
        cancel_flag=cancel)
    t1 = time.perf_counter()
    print(f"  Elapsed: {t1 - t0:.1f}s")
    assert result3, "NSGA-II returned empty result"
    pareto = result3.get('pareto_front', [])
    assert len(pareto) >= 1, "Empty Pareto front"
    for sol in pareto:
        for s in sol['scores']:
            assert s < float('inf'), f"inf score in Pareto front: {sol}"
    print(f"  ✓ Pareto front has {len(pareto)} solutions, all finite\n")

    # ── TEST 4: Stop mid-run ─────────────────────────────────────────
    print("=" * 60)
    print("TEST 4: Early stop (cancel after 2 s) — DE on Ernst")
    print("=" * 60)

    def _cancel_after(seconds):
        time.sleep(seconds)
        cancel.set()

    cancel.clear()
    stopper = threading.Thread(target=_cancel_after, args=(2.0,))
    stopper.start()
    t0 = time.perf_counter()
    result4 = optimizer.optimize_evolution(
        param_list,
        population_size=6,
        generations=50,   # way more than 2 s worth
        mutation_factor=0.8,
        crossover_prob=0.7,
        callback=callback,
        cancel_flag=cancel)
    stopper.join()
    t1 = time.perf_counter()
    elapsed = t1 - t0
    print(f"  Elapsed: {elapsed:.1f}s (should be well under 50-gen time)")
    # If stop comes during initial population, result is {} — that's OK.
    # If at least one generation ran, we should get best-so-far.
    if result4:
        assert 'best_values' in result4
        print(f"  ✓ Best-so-far returned after stop")
    else:
        print(f"  ✓ Stopped before any generation — empty result (expected)")
    assert elapsed < 30, f"Cancel did not work — ran for {elapsed:.0f}s"
    print()

    # ── Summary ──────────────────────────────────────────────────────
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

    pythoncom.CoUninitialize()


if __name__ == '__main__':
    main()
