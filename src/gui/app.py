"""
Interactive GUI for electrode profile generation.

This module defines the main GUI class.  Business logic (assembly
geometry, optimization, contour building) lives in ``core/``;
export formats live in ``exporters/``; FEMM integration lives in
``simulation/``.  This file is purely UI wiring.
"""

import os
import sys
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.profiles import PROFILES, ProfileBase
from core.assembly import build_assembly_curves
from core.contour import build_top_contour
from core.validation import InputValidator
from version import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION, APP_YEAR


def _asset_path(filename: str) -> str:
    """Resolve path to an asset file, works both in dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        # In dev, assets/ is two levels up from src/gui/
        base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
    return os.path.join(base, 'assets', filename)


class ProfileGeneratorGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.minsize(900, 600)
        self.root.geometry("1200x800")

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
        self.gap = tk.DoubleVar(value=1.0)
        self.plate_length = tk.DoubleVar(value=5.0)

        # Cached curves for export — always plain Python lists
        self._curves = []  # list of (x_list, y_list, label)

        # Simulation thread control
        self._sim_stop_event = None  # threading.Event to keep FEMM open

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
        help_menu.add_command(label="User Manual\u2026", command=self._show_manual)
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

        # Electrode assembly
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Electrode Assembly", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        tk.Label(self.left, text="s \u2014 gap between electrodes", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))
        gap_row = tk.Frame(self.left)
        gap_row.pack(fill=tk.X)
        gap_scale = tk.Scale(gap_row, from_=0.1, to=10.0, orient=tk.HORIZONTAL,
                 variable=self.gap, resolution=0.1, showvalue=False,
                 command=lambda *_: self._schedule_refresh(), length=170)
        gap_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        gap_entry = tk.Entry(gap_row, width=8, justify=tk.RIGHT)
        gap_entry.pack(side=tk.RIGHT, padx=(4, 0))
        gap_entry.insert(0, "1.0")
        self._bind_entry_to_var(gap_entry, self.gap, gap_scale)

        tk.Label(self.left, text="d \u2014 flat plate length", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        plate_row = tk.Frame(self.left)
        plate_row.pack(fill=tk.X)
        plate_scale = tk.Scale(plate_row, from_=0.5, to=30.0, orient=tk.HORIZONTAL,
                 variable=self.plate_length, resolution=0.5, showvalue=False,
                 command=lambda *_: self._schedule_refresh(), length=170)
        plate_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        plate_entry = tk.Entry(plate_row, width=8, justify=tk.RIGHT)
        plate_entry.pack(side=tk.RIGHT, padx=(4, 0))
        plate_entry.insert(0, "5.0")
        self._bind_entry_to_var(plate_entry, self.plate_length, plate_scale)

        tk.Checkbutton(self.left, text="Build electrode assembly",
                       variable=self.electrode_mode, command=self._schedule_refresh).pack(anchor=tk.W, pady=(4, 0))

        # Info label for derived values (e.g. k1 for Ernst)
        self.info_label = tk.Label(self.left, text="", justify=tk.LEFT, font=("Consolas", 9), fg="gray")
        self.info_label.pack(anchor=tk.W, pady=(2, 0))

        # Export buttons
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Export", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tk.Button(self.left, text="Export CSV", command=self._export_csv, width=22).pack(pady=2)
        tk.Button(self.left, text="Export PNG", command=self._export_png, width=22).pack(pady=2)
        tk.Button(self.left, text="Export DXF\u2026", command=self._show_dxf_wizard, width=22).pack(pady=2)
        tk.Button(self.left, text="Export FEMM Lua\u2026", command=self._show_femm_wizard, width=22).pack(pady=2)

        # Simulation
        ttk.Separator(self.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 2))
        tk.Label(self.left, text="Simulation", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.sim_btn = tk.Button(self.left, text="Simulate in FEMM", command=self._simulate_femm, width=22)
        self.sim_btn.pack(pady=2)
        tk.Button(self.left, text="Optimize\u2026", command=self._show_optimize_wizard, width=22).pack(pady=2)

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

            resolution = int(p['step']) if is_int else p['step']
            scale = tk.Scale(row, from_=p['min'], to=p['max'],
                             orient=tk.HORIZONTAL, variable=var, resolution=resolution,
                             command=lambda *_: self._schedule_refresh(), length=170,
                             showvalue=False)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

            entry = tk.Entry(row, width=8, justify=tk.RIGHT)
            entry.pack(side=tk.RIGHT, padx=(4, 0))
            entry.insert(0, str(p['default']))
            self._bind_entry_to_var(entry, var, scale, is_int)

        # Ernst-specific: Auto k0 button
        if self.profile.name == "Ernst":
            tk.Button(self.param_frame_inner, text="Auto k\u2080 (no edge effect)",
                      command=self._auto_k0, width=28).pack(pady=(6, 0))

    def _bind_entry_to_var(self, entry, var, scale=None, is_int=False):
        """Keep an Entry widget and a tk variable in sync."""
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
        from core.profiles import ErnstProfile
        s = self.gap.get()
        k0_optimal = ErnstProfile.optimal_k0(s)
        k0_optimal = max(0.0001, min(k0_optimal, 2.0))
        k0_var = self.param_widgets['k0']
        k0_var.set(round(k0_optimal, 4))
        self._schedule_refresh()
        h = ErnstProfile.profile_width(s)
        self.status_var.set(f"Auto k\u2080 = {k0_optimal:.4f} for gap s = {s:.1f} (h = {h:.1f})")

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _current_config(self) -> dict:
        config = {name: var.get() for name, var in self.param_widgets.items()}
        config['s'] = self.gap.get()
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

        if not self.electrode_mode.get():
            self._curves = [(x.tolist(), y.tolist(), "Profile")]
        else:
            gap = self.gap.get()
            d = self.plate_length.get()
            self._curves = build_assembly_curves(x, y, gap, d)

        # Draw
        self.ax.clear()
        for cx, cy, label in self._curves:
            is_structural = "Plate" in label or "Cap" in label or "Back" in label
            style = (dict(linewidth=3, color='#555555', linestyle='-') if is_structural
                     else dict(linewidth=2, color='#1f77b4', linestyle='-'))
            self.ax.plot(cx, cy, **style)

        # Draw E-field measurement contour in electrode mode
        if self.electrode_mode.get() and self._curves:
            contour_pts = build_top_contour(self._curves)
            if contour_pts:
                cx_c = [p[0] for p in contour_pts]
                cy_c = [p[1] for p in contour_pts]
                self.ax.plot(cx_c, cy_c, linewidth=1, color='#e74c3c',
                             linestyle='--', alpha=0.7, label='E-field contour')

        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title(f"{self.profile.name} Profile" if not self.electrode_mode.get()
                          else f"{self.profile.name} Electrode Assembly")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal', adjustable='datalim')
        self.canvas.draw_idle()

        # Info label for derived values
        info_parts = []
        if self.profile.name == "Ernst":
            from core.profiles import ErnstProfile
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
    def _default_filename(self, ext: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.profile.name}_{stamp}{ext}"

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=self._default_filename(".csv"),
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            from exporters.csv_exporter import export_csv
            export_csv(self._curves, path)
            self.status_var.set(f"Exported CSV: {path}")
        except Exception as e:
            self.status_var.set(f"CSV export failed: {e}")

    def _export_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=self._default_filename(".png"),
            filetypes=[("PNG files", "*.png")])
        if not path:
            return
        try:
            from exporters.png_exporter import export_png
            export_png(self.fig, path)
            self.status_var.set(f"Exported PNG: {path}")
        except Exception as e:
            self.status_var.set(f"PNG export failed: {e}")

    def _show_dxf_wizard(self):
        from gui.dialogs.dxf_wizard import show_dxf_wizard
        show_dxf_wizard(self.root, self._export_dxf)

    def _export_dxf(self, dxf_config):
        path = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            initialfile=self._default_filename(".dxf"),
            filetypes=[("DXF files", "*.dxf")])
        if not path:
            return
        try:
            from exporters.dxf_exporter import DXFExporter
            version = dxf_config.get("dxf_version", "R2000")
            use_spline = dxf_config.get("curve_type", "Spline") == "Spline"
            single = dxf_config.get("single_layer", False)

            exporter = DXFExporter()
            exporter.create_new_document(dxfversion=version)
            for cx, cy, label in self._curves:
                points = list(zip(cx, cy))
                if single:
                    layer = "PROFILE"
                else:
                    layer = label.upper().replace(" ", "_").replace("-", "_")
                is_structural = "Plate" in label or "Cap" in label or "Back" in label
                color = 7 if is_structural else 5
                if is_structural or not use_spline:
                    exporter.add_polyline(points, layer, color)
                else:
                    exporter.add_spline(points, layer, color)
            exporter.save_to_file(path)
            self.status_var.set(f"Exported DXF: {path}")
        except Exception as e:
            self.status_var.set(f"DXF export failed: {e}")

    # ------------------------------------------------------------------
    # FEMM export
    # ------------------------------------------------------------------
    def _show_femm_wizard(self):
        from gui.dialogs.femm_wizard import show_femm_wizard
        show_femm_wizard(self.root, self._export_femm)

    def _export_femm(self, femm_config):
        is_axi = femm_config.get("problem_type") == "axi"

        try:
            config = self._current_config()
            x, y = self.profile.generate_points(config)
            curves = build_assembly_curves(
                x, y, self.gap.get(), self.plate_length.get(), is_axi)
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".lua",
            initialfile=self._default_filename(".lua"),
            filetypes=[("Lua scripts", "*.lua")])
        if not path:
            return

        if femm_config.get("auto_solve", False):
            fee_path = os.path.splitext(path)[0] + ".fee"
            femm_config["save_path"] = fee_path.replace("\\", "/")

        try:
            from exporters.femm_exporter import FEMMExporter
            exporter = FEMMExporter()
            script = exporter.generate_script(curves, femm_config)
            with open(path, 'w') as f:
                f.write(script)
            self.status_var.set(f"Exported FEMM Lua: {path}")
        except Exception as e:
            self.status_var.set(f"FEMM export failed: {e}")

    # ------------------------------------------------------------------
    # Simulate in FEMM
    # ------------------------------------------------------------------
    def _simulate_femm(self):
        try:
            from simulation.femm_simulator import HAS_FEMM
            if not HAS_FEMM:
                raise ImportError
        except (ImportError, RuntimeError):
            messagebox.showerror(
                "FEMM Not Available",
                "pyfemm is required for simulation.\n\n"
                "Install it with:  pip install pyfemm\n"
                "FEMM 4.2 must also be installed on this system.",
                parent=self.root)
            return

        from gui.dialogs.femm_wizard import show_simulate_wizard
        show_simulate_wizard(self.root, self._run_femm_simulation)

    def _run_femm_simulation(self, femm_config):
        """Launch FEMM simulation in a background thread."""
        is_axi = femm_config.get("problem_type") == "axi"

        config = self._current_config()
        x, y = self.profile.generate_points(config)
        curves = build_assembly_curves(
            x, y, self.gap.get(), self.plate_length.get(), is_axi)
        contour = build_top_contour(curves)

        if self._sim_stop_event is not None:
            self._sim_stop_event.set()

        stop_event = threading.Event()
        self._sim_stop_event = stop_event

        self.sim_btn.config(state=tk.DISABLED, text="Running\u2026")
        self.status_var.set("Opening FEMM\u2026")

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from simulation.femm_simulator import FEMMSimulator
                sim = FEMMSimulator()
                sim.open(hide=False)
                self.root.after(0, lambda: self.status_var.set("Building and solving\u2026"))
                sim.build_and_solve(curves, femm_config)
                sim.select_contour(contour)
                sim.show_field_plot()
                self.root.after(0, lambda: self.status_var.set(
                    "FEMM simulation complete \u2014 results open in FEMM"))
                self.root.after(0, lambda: self.sim_btn.config(
                    state=tk.NORMAL, text="Simulate in FEMM"))
                stop_event.wait()
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self.status_var.set(f"Simulation error: {m}"))
            finally:
                pythoncom.CoUninitialize()
                self.root.after(0, lambda: self.sim_btn.config(
                    state=tk.NORMAL, text="Simulate in FEMM"))

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Optimization wizard
    # ------------------------------------------------------------------
    def _show_optimize_wizard(self):
        from gui.dialogs.optimize_wizard import show_optimize_wizard

        def _on_apply(param_name, value, delta_e):
            if param_name == 's':
                self.gap.set(value)
            elif param_name == 'd':
                self.plate_length.set(value)
            elif param_name in self.param_widgets:
                self.param_widgets[param_name].set(value)
            self._schedule_refresh()
            self.status_var.set(
                f"Applied optimal {param_name} = {value:.6f} "
                f"(\u0394E = {delta_e:.2f}%)")

        show_optimize_wizard(
            self.root,
            self.profile,
            self._current_config(),
            self.gap.get(),
            self.plate_length.get(),
            on_apply=_on_apply,
        )

    # ------------------------------------------------------------------
    # Help / About dialogs
    # ------------------------------------------------------------------
    def _show_manual(self):
        from gui.dialogs.help_dialog import show_help_dialog
        show_help_dialog(self.root)

    def _show_about(self):
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
