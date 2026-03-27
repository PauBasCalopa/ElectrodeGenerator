"""Chapter-based user manual dialog."""

import tkinter as tk
from tkinter import ttk

# ──────────────────────────────────────────────────────────
# Chapter content — (title, body) pairs
# ──────────────────────────────────────────────────────────

CHAPTERS = [
    (
        "Overview",
        (
            "Electrode Profile Generator\n"
            "══════════════════════════════\n\n"
            "A desktop tool for designing parallel-plate electrodes with\n"
            "mathematically defined edge profiles.\n\n"
            "Supported profiles:\n"
            "  • Rogowski — conformal-mapping profile scaled by gap s\n"
            "  • Chang   — parametric profile with compactness factor k\n"
            "  • Ernst   — two-term profile with auto-calculated k₁\n"
            "  • Bruce   — piecewise sinusoidal + circular termination\n\n"
            "Key features:\n"
            "  • Live interactive preview with electrode assembly\n"
            "  • Closing arcs (tangent in planar, perpendicular to axis in axi)\n"
            "  • Export to CSV, PNG, DXF, and FEMM Lua script\n"
            "  • Live FEMM simulation with E-field extraction\n"
            "  • Parameter sweep (single or multi-parameter)\n"
            "  • Three optimisation algorithms:\n"
            "      Golden-section, Differential Evolution, NSGA-II"
        ),
    ),
    (
        "GUI Interface",
        (
            "GUI Interface\n"
            "══════════════════════════════\n\n"
            "The main window has two panels:\n\n"
            "Left panel — profile selection, parameters, electrode\n"
            "assembly settings, and export buttons.\n\n"
            "Right panel — live matplotlib plot showing the current\n"
            "profile or electrode assembly.\n\n"
            "Profile selection\n"
            "─────────────────\n"
            "Use the 'Profile Type' dropdown to switch profiles.\n"
            "The parameter sliders update automatically.\n\n"
            "Parameter entry\n"
            "─────────────────\n"
            "  • Sliders — drag for quick adjustment\n"
            "  • Entry boxes — type a value and press Enter\n"
            "  • Accepts both '.' and ',' as decimal separator\n"
            "  • If you type beyond the slider range, it auto-extends"
        ),
    ),
    (
        "Electrode Assembly",
        (
            "Electrode Assembly\n"
            "══════════════════════════════\n\n"
            "Check 'Build electrode assembly' to display the full\n"
            "mirrored electrode pair with flat plates and closing arcs.\n\n"
            "Parameters:\n"
            "  s (gap)          — distance between the two electrodes\n"
            "  d (plate length) — length of the flat plate portion\n\n"
            "Closing arcs\n"
            "─────────────────\n"
            "The electrode tips are closed with a smooth arc:\n\n"
            "  Planar mode — a tangent arc connects the right and left\n"
            "  profile tips. The arc center is computed so that the\n"
            "  arc starts tangent to both profile ends and maintains\n"
            "  equal distance from both endpoints.\n\n"
            "  Axisymmetric mode — the arc runs from the profile tip\n"
            "  to the axis of symmetry (r = 0), arriving perpendicular\n"
            "  to the axis. The center lies on r = 0."
        ),
    ),
    (
        "Rogowski Profile",
        (
            "Rogowski Profile\n"
            "══════════════════════════════\n\n"
            "Derived from conformal mapping. The electrode gap s\n"
            "scales the entire profile.\n\n"
            "Equations:\n"
            "  X = (s/π) · (u + 1 + eᵘ · cos(v))\n"
            "  Y = (s/π) · (v + eᵘ · sin(v))\n"
            "  v = π/2 (constant)\n\n"
            "Parameters:\n"
            "  s      — electrode gap\n"
            "  u      — parameter variable (u ∈ [u_start, u_end])\n\n"
            "Properties:\n"
            "  • As u → −∞, Y → s/2\n"
            "  • The natural gap between two mirrored curves is s\n"
            "  • Produces a uniform field in the gap region"
        ),
    ),
    (
        "Chang Profile",
        (
            "Chang Profile\n"
            "══════════════════════════════\n\n"
            "Parametric conformal-mapping profile with a\n"
            "compactness factor k.\n\n"
            "Equations:\n"
            "  X = u + cos(v) · sinh(u)\n"
            "  Y = v + k · sin(v) · cosh(u)\n"
            "  v = π/2 (constant)\n\n"
            "Parameters:\n"
            "  k       — compactness factor (k > 0, default 0.85)\n"
            "  u_max   — defines the electrode width\n\n"
            "Properties:\n"
            "  • Higher k → more compact profile\n"
            "  • u ∈ [0, u_max]"
        ),
    ),
    (
        "Ernst Profile",
        (
            "Ernst Profile\n"
            "══════════════════════════════\n\n"
            "Adds a second-order correction term to the Chang\n"
            "mapping for improved field uniformity.\n\n"
            "Equations:\n"
            "  X = u + k₀·cos(v)·sinh(u) + k₁·cos(2v)·sinh(2u)\n"
            "  Y = v + k₀·sin(v)·cosh(u) + k₁·sin(2v)·cosh(2u)\n"
            "  v = π/2 (constant)\n"
            "  k₁ = k₀² / 8  (auto-calculated)\n\n"
            "Parameters:\n"
            "  k₀  — primary shape constant\n"
            "  k₁  — secondary constant (derived from k₀)\n\n"
            "Edge-effect relationships:\n"
            "  k₀ = 1.72 · e⁻ʰ     (k₀ from profile width h)\n"
            "  h  = 3.5 · s          (width for edge-free design)\n"
            "  k₀ = 1.72 · e⁻³·⁵ˢ   (optimal k₀ from gap s)\n\n"
            "  Edge effects become significant at s ≈ 3.\n"
            "  Use the 'Auto k₀' button to compute the optimal value."
        ),
    ),
    (
        "Bruce Profile",
        (
            "Bruce Profile\n"
            "══════════════════════════════\n\n"
            "A piecewise construction combining a sinusoidal\n"
            "transition zone with a circular termination.\n\n"
            "Region 1 — Sinusoidal (α₀ ≤ α ≤ π/2):\n"
            "  Xbr = (s/2) · sin(α)\n"
            "  Ybr = (s/2) · (π/2 − α + sin(α)·cos(α)) / sin²(α₀)\n\n"
            "Region 2 — Circular (0 ≤ α ≤ α₀):\n"
            "  Xbr = R₀ − R₀·cos(α) + X(α₀)\n"
            "  Ybr = R₀ · sin(α)\n"
            "  R₀  = (s/2) / sin²(α₀)\n\n"
            "Parameters:\n"
            "  α₀  — characteristic angle defining the transition\n"
            "  s   — electrode gap\n\n"
            "Properties:\n"
            "  • Profile endpoints are rotated into the standard\n"
            "    electrode coordinate frame\n"
            "  • Smooth C¹ continuity at the sinusoidal/circular join"
        ),
    ),
    (
        "Exporting",
        (
            "Exporting\n"
            "══════════════════════════════\n\n"
            "All exports use a default filename of\n"
            "  ProfileType_YYYYMMDD_HHMMSS.ext\n\n"
            "CSV — exports all visible curves as a table with\n"
            "columns: curve, x, y.\n\n"
            "PNG — saves the current plot as a 150 DPI image.\n\n"
            "DXF — opens the DXF wizard:\n"
            "  • DXF version: R12 (FEMM), R2000 (SolidWorks)\n"
            "  • Entity type: Spline (smooth) or Polyline (segmented)\n"
            "  • Merge layers: combine all curves into one layer\n"
            "  • R12 forces Polyline (no SPLINE entities in R12)\n"
            "  • Structural curves (plates, caps) are always polylines\n\n"
            "FEMM Lua — opens the FEMM wizard:\n"
            "  • Problem type: planar or axisymmetric\n"
            "  • Units, depth, voltages, εr, mesh size\n"
            "  • Optional auto-solve\n"
            "  • Axisymmetric mode exports only the right half (r ≥ 0)"
        ),
    ),
    (
        "FEMM Simulation",
        (
            "FEMM Simulation\n"
            "══════════════════════════════\n\n"
            "Click 'Run FEMM Simulation…' to drive FEMM 4.2 directly.\n"
            "Requires pyfemm and FEMM 4.2 installed.\n\n"
            "The simulation:\n"
            "  1. Opens FEMM (hidden)\n"
            "  2. Builds geometry, materials, and boundaries\n"
            "  3. Meshes and solves\n"
            "  4. Extracts E-field along a measuring contour\n"
            "  5. Displays the E-field plot\n\n"
            "Measuring contour\n"
            "─────────────────\n"
            "The contour follows the top electrode with a small\n"
            "offset into the gap.\n\n"
            "  Planar mode   — contour runs along the full top electrode\n"
            "  Axi mode      — contour starts from r = 0 (axis) and\n"
            "                   follows the top electrode outward\n\n"
            "Field enhancement ΔE%\n"
            "─────────────────\n"
            "  ΔE% = (E_max − E_uniform) / E_uniform × 100\n\n"
            "  Where E_uniform = V / gap, the ideal parallel-plate field."
        ),
    ),
    (
        "Profile Optimizer",
        (
            "Profile Optimizer\n"
            "══════════════════════════════\n\n"
            "Click 'Optimize…' to open the optimization wizard.\n"
            "Select one or more profile parameters (including the\n"
            "assembly gap s and plate length d) and choose an\n"
            "algorithm.  The Points slider is excluded — it\n"
            "affects discretisation, not the physical shape.\n\n"
            "For each selected parameter, set min/max bounds that\n"
            "define the search space.  A quick Sweep can help\n"
            "identify reasonable bounds before optimising.\n\n"
            "Three algorithms are available:\n\n"
            "Golden-section\n"
            "─────────────────\n"
            "Fast 1-D line search based on the golden ratio.  Each\n"
            "step reduces the interval by φ = 1.618, requiring\n"
            "only one new FEMM evaluation per step.  Minimises\n"
            "ΔE %.  When multiple parameters are selected they are\n"
            "optimised one at a time, sequentially.\n\n"
            "  Tolerance — stop when the parameter range is\n"
            "    narrower than this value.  For shape params (k₀,\n"
            "    u_end, α₀) 0.001 is sufficient; for gap s or\n"
            "    plate length d use 0.01 (they have mm units).\n\n"
            "  Max iter — upper limit on evaluations per param.\n"
            "    Golden-section converges geometrically: a range\n"
            "    of [0, 3] with tolerance 0.001 needs ~17 iters,\n"
            "    so 20 is a safe default.  If convergence hasn't\n"
            "    happened by 30, the landscape is likely\n"
            "    multi-modal — switch to Differential Evolution.\n\n"
            "  Strengths: very fast (10-20 evals per param),\n"
            "  guaranteed for unimodal landscapes.\n"
            "  Limitations: no parameter interactions; may miss\n"
            "  the global optimum if multiple local minima exist.\n\n"
            "Differential Evolution\n"
            "─────────────────\n"
            "Population-based global optimiser (DE/rand/1/bin).\n"
            "All selected parameters are optimised simultaneously,\n"
            "so parameter interactions are captured naturally.\n\n"
            "  Population — number of candidates per generation.\n"
            "    Rule of thumb: 5-10× the number of optimised\n"
            "    params.  E.g. 3 params → population 15-30.\n"
            "    Very small populations (< 10) risk premature\n"
            "    convergence to a local minimum.\n\n"
            "  Generations — how many evolution cycles to run.\n"
            "    Total FEMM evals ≈ population × generations.\n"
            "    Start with 20-30.  If the progress log shows\n"
            "    ΔE % still improving in the last generations,\n"
            "    increase this.  Typical budget: pop=20, gen=30\n"
            "    → 600 evals → ~20 min at 2 s each.\n\n"
            "  F (mutation) — scale factor for the donor vector.\n"
            "    Controls how bold the mutations are:\n"
            "      F = 0.5  conservative, fine-grained search\n"
            "      F = 0.8  good balance (default)\n"
            "      F = 1.0  aggressive, larger jumps\n"
            "    For each candidate x, three random others a, b, c\n"
            "    are chosen and the donor = a + F·(b − c).  Higher\n"
            "    F → donor strays further from the base vector.\n\n"
            "  CR (crossover) — probability that each gene comes\n"
            "    from the mutated donor vs. the current candidate:\n"
            "      CR = 0.5  conservative, preserves parent\n"
            "      CR = 0.7  moderate (default)\n"
            "      CR = 0.9  aggressive, almost all from donor\n"
            "    Guideline: independent params (k₀ vs d) → lower\n"
            "    CR (0.5-0.7).  Tightly coupled params (k₀ vs\n"
            "    u_end) → higher CR (0.7-0.9).\n\n"
            "  Tuning: if converges too early, increase F or\n"
            "  population.  If wanders, decrease F or increase\n"
            "  generations.\n\n"
            "NSGA-II — multi-objective (default)\n"
            "─────────────────\n"
            "Multi-objective Pareto optimisation using non-dominated\n"
            "sorting + crowding distance.  Returns a Pareto front:\n"
            "a set of trade-off solutions where no solution is\n"
            "better than another on all objectives at once.\n\n"
            "  Population — controls exploration AND the maximum\n"
            "    number of Pareto front solutions returned.  For a\n"
            "    dense, well-resolved front use 30-50.  For a rough\n"
            "    exploration 15-20 is enough.\n\n"
            "  Generations — how many rounds of evolution.  Early\n"
            "    generations give a rough front; more generations\n"
            "    refine it.  More objectives need more generations.\n"
            "    Start with 20-30; increase if the front is still\n"
            "    changing in the final generations.\n\n"
            "  F and CR — same as Differential Evolution (see\n"
            "    above).  Defaults: F = 0.8, CR = 0.7.  Higher F\n"
            "    spreads solutions wider along the Pareto front.\n\n"
            "  Objectives (select ≥ 2):\n"
            "    ΔE %     — field enhancement at the electrode\n"
            "               edge (lower = more uniform field)\n"
            "    Width    — radial extent of the profile\n"
            "               (lower = more compact electrode)\n"
            "    CV(E) %  — coefficient of variation of the\n"
            "               E-field (lower = flatter field)\n"
            "    Height   — vertical extent of the profile\n"
            "               (lower = thinner electrode)\n\n"
            "  Common pairs:\n"
            "    ΔE % + Width  — compactness vs. uniformity\n"
            "    ΔE % + Height — thickness-constrained designs\n"
            "    ΔE % + CV(E)  — overall field homogeneity\n\n"
            "  For 2 objectives: pop=20, gen=30 is usually enough.\n"
            "  For 3-4 objectives: try pop=40, gen=50.\n\n"
            "  Tuning: if the front has gaps, increase population.\n"
            "  If solutions cluster, increase generations or F.\n"
            "  If all solutions look similar, widen bounds.\n\n"
            "After the run a Pareto Front table appears.  Select a\n"
            "row and click 'Apply to Profile' to use those values.\n\n"
            "Choosing the right algorithm\n"
            "─────────────────\n"
            "  1 param, quick check       → Golden-section\n"
            "  2+ params, single objective → Differential Evolution\n"
            "  2+ params, 2+ objectives   → NSGA-II (default)\n"
            "  Fine-tuning a known design  → Golden-section\n\n"
            "Controls and workflow\n"
            "─────────────────\n"
            "  • Click 'Start' to begin\n"
            "  • The button changes to 'Stop' while running\n"
            "  • Click 'Stop' to halt early — the best result\n"
            "    found so far is kept and can still be applied\n"
            "  • Click 'Apply to Profile' to send the result back\n"
            "  • Click 'Export CSV' to save results to a file:\n"
            "    - NSGA-II exports the full Pareto front table\n"
            "    - DE / Golden-section export the best values\n\n"
            "The wizard is non-modal: it stays open while you\n"
            "interact with the main window.  You can apply a result,\n"
            "run a FEMM simulation, then return to the wizard to\n"
            "try a different Pareto solution."
        ),
    ),
    (
        "Parameter Sweep",
        (
            "Parameter Sweep\n"
            "══════════════════════════════\n\n"
            "Click 'Sweep…' to open the sweep wizard.\n"
            "A sweep evaluates ΔE % at evenly spaced values\n"
            "across a parameter range, producing a landscape view\n"
            "of how the objective varies with the parameter.\n\n"
            "You can select one or more parameters.\n"
            "  • 1 parameter  → a single sweep\n"
            "  • 2+ parameters→ sweeps run sequentially (one per\n"
            "    parameter), sharing the same FEMM session.\n"
            "    Each parameter is swept independently while the\n"
            "    others are held at their current values.\n\n"
            "Settings:\n"
            "  Parameter — which profile parameter(s) to vary\n"
            "  Range     — min/max bounds for each parameter\n"
            "  Steps     — number of evaluation points (more =\n"
            "              finer resolution)\n\n"
            "The sweep logs each evaluation and highlights the\n"
            "best value found.  Solver errors (invalid geometries)\n"
            "are skipped automatically with a log message.\n\n"
            "When to use\n"
            "─────────────────\n"
            "Run a sweep before a full optimisation to get\n"
            "intuition about the parameter landscape:\n"
            "  • Is the landscape smooth or rugged (multiple\n"
            "    local minima)?\n"
            "  • Where is the approximate optimum region?\n"
            "  • Are the current bounds reasonable?\n\n"
            "This helps choose the right algorithm and set\n"
            "appropriate bounds for the optimiser.\n\n"
            "Export\n"
            "─────────────────\n"
            "Click 'Export CSV' to save all sweep data (parameter\n"
            "values and corresponding ΔE %) to a CSV file for\n"
            "external analysis or plotting."
        ),
    ),
]


def show_help_dialog(parent):
    """Open the chapter-based user manual window."""
    win = tk.Toplevel(parent)
    win.title("User Manual")
    win.geometry("720x500")
    win.minsize(540, 350)
    win.transient(parent)

    # ── layout: tree on left, text on right ──
    pw = ttk.PanedWindow(win, orient=tk.HORIZONTAL)
    pw.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # chapter list
    tree_frame = ttk.Frame(pw)
    tree = tk.Listbox(tree_frame, activestyle="dotbox", width=22,
                       exportselection=False)
    tree.pack(fill=tk.BOTH, expand=True)
    pw.add(tree_frame, weight=0)

    for title, _ in CHAPTERS:
        tree.insert(tk.END, title)

    # content area
    text_frame = ttk.Frame(pw)
    text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED,
                   font=("Consolas", 10), padx=10, pady=10)
    sb = ttk.Scrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    pw.add(text_frame, weight=1)

    def _on_select(event):
        sel = tree.curselection()
        if not sel:
            return
        _, body = CHAPTERS[sel[0]]
        text.configure(state=tk.NORMAL)
        text.delete("1.0", tk.END)
        text.insert(tk.END, body)
        text.configure(state=tk.DISABLED)
        text.yview_moveto(0)

    tree.bind("<<ListboxSelect>>", _on_select)

    # select first chapter
    tree.selection_set(0)
    tree.event_generate("<<ListboxSelect>>")

    # close button
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 8))
