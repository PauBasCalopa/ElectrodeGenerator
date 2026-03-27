"""FEMM configuration wizard dialogs (export and simulation)."""

import tkinter as tk
from tkinter import ttk, messagebox

from core.validation import InputValidator

_validator = InputValidator()


def _build_femm_fields(wiz, include_auto_solve=True):
    """Build the shared FEMM configuration fields inside *wiz*.

    Returns:
        ``(get_config, next_row)`` — *get_config* is a callable that
        reads and validates all widgets and returns a config dict
        (or None on validation error); *next_row* is the grid row
        index after the last field so callers can append their own
        buttons.
    """
    prob_type = tk.StringVar(value="axi")
    units = tk.StringVar(value="millimeters")
    auto_solve = tk.BooleanVar(value=False)

    r = 0
    tk.Label(wiz, text="Problem type:").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    ttk.Combobox(wiz, textvariable=prob_type,
                 values=["planar", "axi"], state="readonly", width=18
                 ).grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Units:").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    ttk.Combobox(wiz, textvariable=units,
                 values=["millimeters", "centimeters", "meters",
                         "inches", "mils", "micrometers"],
                 state="readonly", width=18
                 ).grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Depth (planar):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    depth_entry = tk.Entry(wiz, width=20)
    depth_entry.insert(0, "1.0")
    depth_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    ttk.Separator(wiz, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Top electrode voltage (V):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    vtop_entry = tk.Entry(wiz, width=20)
    vtop_entry.insert(0, "1000.0")
    vtop_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Bottom electrode voltage (V):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    vbot_entry = tk.Entry(wiz, width=20)
    vbot_entry.insert(0, "0.0")
    vbot_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Relative permittivity (\u03b5r):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    epsr_entry = tk.Entry(wiz, width=20)
    epsr_entry.insert(0, "1.0")
    epsr_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    ttk.Separator(wiz, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Mesh size (0 = auto):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    mesh_entry = tk.Entry(wiz, width=20)
    mesh_entry.insert(0, "0.0")
    mesh_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Electrode mesh size (0 = auto):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    emesh_entry = tk.Entry(wiz, width=20)
    emesh_entry.insert(0, "0.0")
    emesh_entry.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    use_symmetry = tk.BooleanVar(value=True)
    tk.Checkbutton(wiz, text="Use symmetry (model half gap only)",
                   variable=use_symmetry).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

    if include_auto_solve:
        r += 1
        tk.Checkbutton(wiz, text="Auto-solve after generation",
                       variable=auto_solve).grid(
            row=r, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

    def _get_config():
        """Read and validate all fields. Returns config dict or None on error."""
        errors = []

        fields = [
            ("Depth", depth_entry, {}),
            ("Top electrode voltage", vtop_entry, {}),
            ("Bottom electrode voltage", vbot_entry, {}),
            ("Relative permittivity", epsr_entry, {}),
            ("Mesh size", mesh_entry, {}),
            ("Electrode mesh size", emesh_entry, {}),
        ]
        values = {}
        for label, entry_w, opts in fields:
            result = _validator.validate_float(entry_w.get(), **opts)
            if not result.is_valid:
                errors.append(f"{label}: {result.error_message}")
            else:
                values[label] = result.value

        if errors:
            messagebox.showwarning(
                "Invalid input",
                "\n".join(errors),
                parent=wiz)
            return None

        cfg = {
            "problem_type": prob_type.get(),
            "units": units.get(),
            "depth": values["Depth"],
            "voltage_top": values["Top electrode voltage"],
            "voltage_bottom": values["Bottom electrode voltage"],
            "permittivity": values["Relative permittivity"],
            "mesh_size": values["Mesh size"],
            "electrode_mesh_size": values["Electrode mesh size"],
            "use_symmetry": use_symmetry.get(),
        }
        if include_auto_solve:
            cfg["auto_solve"] = auto_solve.get()
        return cfg

    return _get_config, r + 1


# ------------------------------------------------------------------
# Export wizard
# ------------------------------------------------------------------
def show_femm_wizard(parent, on_export):
    """Open a dialog to configure FEMM export parameters.

    Args:
        parent: Parent tk window.
        on_export: Callback ``on_export(femm_config)`` called with the
                   chosen settings when the user clicks Export.
    """
    wiz = tk.Toplevel(parent)
    wiz.title("FEMM Export")
    wiz.resizable(False, False)
    wiz.transient(parent)
    wiz.grab_set()

    get_config, next_row = _build_femm_fields(wiz, include_auto_solve=True)

    def _do_export():
        femm_config = get_config()
        if femm_config is None:
            return
        wiz.destroy()
        on_export(femm_config)

    tk.Button(wiz, text="Export Lua Script", command=_do_export,
              width=22).grid(row=next_row, column=0, columnspan=2, pady=12)


# ------------------------------------------------------------------
# Simulation wizard
# ------------------------------------------------------------------
def show_simulate_wizard(parent, on_simulate):
    """Open a dialog to configure FEMM simulation parameters.

    Args:
        parent: Parent tk window.
        on_simulate: Callback ``on_simulate(femm_config)`` called with
                     the chosen settings when the user clicks Simulate.
    """
    wiz = tk.Toplevel(parent)
    wiz.title("FEMM Simulation")
    wiz.resizable(False, False)
    wiz.transient(parent)
    wiz.grab_set()

    get_config, next_row = _build_femm_fields(wiz, include_auto_solve=False)

    def _do_simulate():
        femm_config = get_config()
        if femm_config is None:
            return
        wiz.destroy()
        on_simulate(femm_config)

    tk.Button(wiz, text="Simulate in FEMM", command=_do_simulate,
              width=22).grid(row=next_row, column=0, columnspan=2, pady=12)
