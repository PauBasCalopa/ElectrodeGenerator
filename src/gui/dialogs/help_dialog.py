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
            "  • Golden-section parameter optimizer"
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
            "Click 'Optimize…' to open the optimization wizard.\n\n"
            "The optimizer performs a golden-section search over a\n"
            "selected profile parameter to minimize ΔE%.\n\n"
            "Settings:\n"
            "  Parameter       — which profile parameter to vary\n"
            "  Range (min/max) — search bounds\n"
            "  Tolerance       — convergence threshold\n"
            "  Max iterations  — limit on evaluations\n\n"
            "Each iteration runs a full FEMM simulation.\n"
            "Progress is shown in real time.\n\n"
            "Controls:\n"
            "  • Click 'Start Optimization' to begin\n"
            "  • The button changes to 'Cancel' while running\n"
            "  • Click 'Cancel' to stop at any time\n"
            "  • When complete, click 'Apply to Profile' to use\n"
            "    the optimal value found"
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
