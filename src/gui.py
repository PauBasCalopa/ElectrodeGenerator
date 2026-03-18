"""
Interactive GUI for electrode profile generation.

Usage:
    python gui.py
"""

import csv
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from profiles import PROFILES, ProfileBase
from dxf_exporter import DXFExporter
from version import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION, APP_YEAR
from InputValidator import InputValidator


def _asset_path(filename: str) -> str:
    """Resolve path to an asset file, works both in dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        # In dev, assets/ is one level up from src/
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'assets', filename)


class ProfileGeneratorGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.minsize(900, 600)

        # Window icon
        icon_path = _asset_path('icon.png')
        if os.path.exists(icon_path):
            icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, icon)
            self._icon_ref = icon  # prevent garbage collection

        # State
        self.profile: ProfileBase = list(PROFILES.values())[0]
        self.param_widgets = {}          # name -> tk.DoubleVar / tk.IntVar
        self.param_frame_inner = None    # rebuilt on profile change
        self._update_job = None          # for debouncing
        self._validator = InputValidator()

        # Transform vars
        self.electrode_mode = tk.BooleanVar(value=False)
        self.gap = tk.DoubleVar(value=2.0)
        self.plate_length = tk.DoubleVar(value=5.0)

        # Cached curves for export
        self._curves = []  # list of (x[], y[], label)

        self._build_ui()
        self._build_param_controls()
        self._refresh_plot()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Equations\u2026", command=self._show_equations)
        help_menu.add_separator()
        help_menu.add_command(label="About\u2026", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        # Left panel
        self.left = tk.Frame(self.root, width=280)
        self.left.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        self.left.pack_propagate(False)

        # Profile selector
        tk.Label(self.left, text="Profile Type", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.profile_var = tk.StringVar(value=self.profile.name)
        combo = ttk.Combobox(self.left, textvariable=self.profile_var,
                             values=list(PROFILES.keys()), state="readonly", width=26)
        combo.pack(fill=tk.X, pady=(0, 8))
        combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        # Parameters frame (rebuilt dynamically)
        tk.Label(self.left, text="Parameters", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(4, 0))
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)
        self.param_frame = tk.Frame(self.left)
        self.param_frame.pack(fill=tk.X)

        # Electrode gap — always visible, used by all profiles
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Electrode Gap", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tk.Label(self.left, text="s \u2014 gap between electrodes", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))
        gap_row = tk.Frame(self.left)
        gap_row.pack(fill=tk.X)
        gap_scale = tk.Scale(gap_row, from_=0.5, to=20.0, orient=tk.HORIZONTAL,
                 variable=self.gap, resolution=0.1, showvalue=False,
                 command=lambda *_: self._schedule_refresh(), length=170)
        gap_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        gap_entry = tk.Entry(gap_row, width=8, justify=tk.RIGHT)
        gap_entry.pack(side=tk.RIGHT, padx=(4, 0))
        gap_entry.insert(0, "2.0")
        self._bind_entry_to_var(gap_entry, self.gap, gap_scale)

        # Electrode construction section
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Electrode Construction", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tk.Checkbutton(self.left, text="Build electrode assembly",
                       variable=self.electrode_mode, command=self._schedule_refresh).pack(anchor=tk.W)

        self.assembly_frame = tk.Frame(self.left)
        self.assembly_frame.pack(fill=tk.X)

        tk.Label(self.assembly_frame, text="d \u2014 flat plate length", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        plate_row = tk.Frame(self.assembly_frame)
        plate_row.pack(fill=tk.X)
        plate_scale = tk.Scale(plate_row, from_=1.0, to=30.0, orient=tk.HORIZONTAL,
                 variable=self.plate_length, resolution=0.5, showvalue=False,
                 command=lambda *_: self._schedule_refresh(), length=170)
        plate_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        plate_entry = tk.Entry(plate_row, width=8, justify=tk.RIGHT)
        plate_entry.pack(side=tk.RIGHT, padx=(4, 0))
        plate_entry.insert(0, "5.0")
        self._bind_entry_to_var(plate_entry, self.plate_length, plate_scale)

        # Info labels
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Bounding Box", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.bbox_label = tk.Label(self.left, text="", justify=tk.LEFT, font=("Consolas", 9))
        self.bbox_label.pack(anchor=tk.W)

        # Info label for derived values (e.g. k1 for Ernst)
        self.info_label = tk.Label(self.left, text="", justify=tk.LEFT, font=("Consolas", 9), fg="gray")
        self.info_label.pack(anchor=tk.W, pady=(2, 0))

        # Export buttons
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Export", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tk.Button(self.left, text="Export CSV", command=self._export_csv, width=22).pack(pady=2)
        tk.Button(self.left, text="Export PNG", command=self._export_png, width=22).pack(pady=2)
        tk.Button(self.left, text="Export DXF", command=self._export_dxf, width=22).pack(pady=2)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = tk.Label(self.root, textvariable=self.status_var, bd=1,
                          relief=tk.SUNKEN, anchor=tk.W, padx=6)
        status.pack(side=tk.BOTTOM, fill=tk.X)

        # Matplotlib canvas (right side)
        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=6, pady=6)

    # ------------------------------------------------------------------
    # Dynamic parameter controls
    # ------------------------------------------------------------------
    def _build_param_controls(self):
        # Destroy old widgets
        if self.param_frame_inner is not None:
            self.param_frame_inner.destroy()
        self.param_frame_inner = tk.Frame(self.param_frame)
        self.param_frame_inner.pack(fill=tk.X)
        self.param_widgets.clear()

        for p in self.profile.parameters:
            name = p['name']
            tk.Label(self.param_frame_inner, text=p['label'], font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))

            is_int = (p['type'] is int)
            var = tk.IntVar(value=int(p['default'])) if is_int else tk.DoubleVar(value=p['default'])
            self.param_widgets[name] = var

            row = tk.Frame(self.param_frame_inner)
            row.pack(fill=tk.X)

            # Slider
            resolution = int(p['step']) if is_int else p['step']
            scale = tk.Scale(row, from_=p['min'], to=p['max'],
                             orient=tk.HORIZONTAL, variable=var, resolution=resolution,
                             command=lambda *_: self._schedule_refresh(), length=170,
                             showvalue=False)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Entry box for exact values
            entry = tk.Entry(row, width=8, justify=tk.RIGHT)
            entry.pack(side=tk.RIGHT, padx=(4, 0))
            entry.insert(0, str(p['default']))
            self._bind_entry_to_var(entry, var, scale, is_int)

        # Ernst-specific: Auto k0 button
        if self.profile.name == "Ernst":
            tk.Button(self.param_frame_inner, text="Auto k\u2080 (no edge effect)",
                      command=self._auto_k0, width=28).pack(pady=(6, 0))

    def _bind_entry_to_var(self, entry, var, scale=None, is_int=False):
        """Keep an Entry widget and a tk variable in sync, using InputValidator.
        If a Scale widget is provided, its range is extended when the entry
        value falls outside the current slider limits."""
        def _var_changed(*_):
            val = var.get()
            entry.delete(0, tk.END)
            entry.insert(0, str(int(val) if is_int else val))
        var.trace_add('write', _var_changed)

        def _entry_commit(_event=None):
            raw = entry.get()
            if is_int:
                result = self._validator.validate_integer(raw)
            else:
                result = self._validator.validate_float(raw)
            if result.is_valid:
                val = result.value
                # Extend scale range if needed so it doesn't clamp the value
                if scale is not None:
                    lo = float(scale.cget('from'))
                    hi = float(scale.cget('to'))
                    if val < lo:
                        scale.config(from_=val)
                    if val > hi:
                        scale.config(to=val)
                var.set(val)
                self._schedule_refresh()
            else:
                self.status_var.set(result.error_message)
        entry.bind('<Return>', _entry_commit)
        entry.bind('<FocusOut>', _entry_commit)

    def _on_profile_change(self, _event=None):
        name = self.profile_var.get()
        self.profile = PROFILES[name]
        self._build_param_controls()
        self._refresh_plot()

    # ------------------------------------------------------------------
    # Ernst: auto-calculate optimal k0 from assembly gap
    # ------------------------------------------------------------------
    def _auto_k0(self):
        from profiles import ErnstProfile
        s = self.gap.get()
        k0_optimal = ErnstProfile.optimal_k0(s)
        # Clamp to slider range
        k0_var = self.param_widgets['k0']
        k0_optimal = max(0.0001, min(k0_optimal, 2.0))
        k0_var.set(round(k0_optimal, 4))
        self._schedule_refresh()
        h = ErnstProfile.profile_width(s)
        self.status_var.set(f"Auto k\u2080 = {k0_optimal:.4f} for gap s = {s:.1f} (h = {h:.1f})")

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _current_config(self) -> dict:
        config = {name: var.get() for name, var in self.param_widgets.items()}
        config['s'] = self.gap.get()  # always inject gap as 's' for all profiles
        return config

    # ------------------------------------------------------------------
    # Plot refresh (debounced)
    # ------------------------------------------------------------------
    def _schedule_refresh(self):
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
        self._update_job = self.root.after(50, self._refresh_plot)

    def _refresh_plot(self):
        self._update_job = None
        config = self._current_config()

        try:
            x, y = self.profile.generate_points(config)
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            return

        # Build list of curves to draw (and export later)
        self._curves = []

        if not self.electrode_mode.get():
            # Raw profile curve only
            self._curves.append((x, y, "Profile"))
        else:
            # Full electrode assembly
            gap = self.gap.get()
            d = self.plate_length.get()

            # Normalize curve: shift so first point is at origin
            x0, y0 = x[0], y[0]
            xn = x - x0   # curve relative to plate corner
            yn = y - y0

            # Top electrode (flat plate at y = +gap/2)
            # Right edge: curve goes rightward from (d/2, gap/2)
            self._curves.append((xn + d / 2, yn + gap / 2, "Top-Right"))
            # Left edge: mirror X, curve goes leftward from (-d/2, gap/2)
            self._curves.append((-xn - d / 2, yn + gap / 2, "Top-Left"))
            # Top flat plate
            self._curves.append((np.array([-d / 2, d / 2]), np.array([gap / 2, gap / 2]), "Top Plate"))

            # Bottom electrode (mirror top in Y, flat plate at y = -gap/2)
            self._curves.append((xn + d / 2, -yn - gap / 2, "Bot-Right"))
            self._curves.append((-xn - d / 2, -yn - gap / 2, "Bot-Left"))
            self._curves.append((np.array([-d / 2, d / 2]), np.array([-gap / 2, -gap / 2]), "Bot Plate"))

        # Draw
        self.ax.clear()
        for cx, cy, label in self._curves:
            is_plate = "Plate" in label
            style = dict(linewidth=3, color='#555555', linestyle='-') if is_plate else dict(linewidth=2, color='#1f77b4', linestyle='-')
            self.ax.plot(cx, cy, label=label, **style)

        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title(f"{self.profile.name} Profile" if not self.electrode_mode.get()
                          else f"{self.profile.name} Electrode Assembly")
        self.ax.legend(fontsize=7, loc='upper left')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal', adjustable='datalim')
        self.canvas.draw_idle()

        # Bounding box
        all_x = np.concatenate([c[0] for c in self._curves])
        all_y = np.concatenate([c[1] for c in self._curves])
        self.bbox_label.config(
            text=f"X: [{np.min(all_x):.4f}, {np.max(all_x):.4f}]\n"
                 f"Y: [{np.min(all_y):.4f}, {np.max(all_y):.4f}]"
        )

        # Info label for derived values
        info_parts = []
        if self.profile.name == "Ernst":
            from profiles import ErnstProfile
            k0 = config.get('k0', 1.0)
            s = self.gap.get()
            k1 = k0 ** 2 / 8.0
            h = ErnstProfile.profile_width(s)
            k0_opt = ErnstProfile.optimal_k0(s)
            info_parts.append(f"k\u2081 = k\u2080\u00b2/8 = {k1:.6f}")
            info_parts.append(f"h  = 3.5\u00b7s = {h:.2f}  (gap s = {s:.1f})")
            info_parts.append(f"k\u2080 optimal = {k0_opt:.6f}")
            if s >= 3.0:
                info_parts.append("\u26a0 s \u2265 3: edge effect likely")
        self.info_label.config(text="\n".join(info_parts))

        self.status_var.set("Ready")

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["curve", "x", "y"])
                for cx, cy, label in self._curves:
                    for xi, yi in zip(cx, cy):
                        writer.writerow([label, f"{xi:.6f}", f"{yi:.6f}"])
            self.status_var.set(f"Exported CSV: {path}")
        except Exception as e:
            self.status_var.set(f"CSV export failed: {e}")

    def _export_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG files", "*.png")])
        if not path:
            return
        try:
            self.fig.savefig(path, dpi=150, bbox_inches='tight')
            self.status_var.set(f"Exported PNG: {path}")
        except Exception as e:
            self.status_var.set(f"PNG export failed: {e}")

    def _export_dxf(self):
        path = filedialog.asksaveasfilename(defaultextension=".dxf",
                                            filetypes=[("DXF files", "*.dxf")])
        if not path:
            return
        try:
            exporter = DXFExporter()
            exporter.create_new_document()
            for cx, cy, label in self._curves:
                points = list(zip(cx.tolist(), cy.tolist()))
                layer = label.upper().replace(" ", "_").replace("-", "_")
                is_plate = "PLATE" in layer
                color = 7 if is_plate else 5  # white for plates, blue for curves
                exporter.add_polyline(points, layer, color)
            exporter.save_to_file(path)
            self.status_var.set(f"Exported DXF: {path}")
        except Exception as e:
            self.status_var.set(f"DXF export failed: {e}")

    # ------------------------------------------------------------------
    # Help / About dialogs
    # ------------------------------------------------------------------
    def _show_equations(self):
        """Show equations for the currently selected profile."""
        title = f"{self.profile.name} Profile \u2014 Equations"
        messagebox.showinfo(title, self.profile.equations, parent=self.root)

    def _show_about(self):
        """Show the About dialog with version and description."""
        text = (
            f"{APP_NAME}\n"
            f"Version {APP_VERSION}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            f"\u00a9 {APP_YEAR} {APP_AUTHOR}"
        )
        messagebox.showinfo(f"About {APP_NAME}", text, parent=self.root)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ProfileGeneratorGUI().run()
