"""FEMM configuration wizard dialogs (export and simulation)."""

import tkinter as tk
from tkinter import ttk


def _build_femm_fields(wiz, include_auto_solve=True):
    """Build the shared FEMM configuration fields inside *wiz*.

    Returns:
        ``(get_config, next_row)`` — *get_config* is a callable that
        reads all widgets and returns a config dict; *next_row* is the
        grid row index after the last field so callers can append
        their own buttons.
    """
    prob_type = tk.StringVar(value="planar")
    units = tk.StringVar(value="millimeters")
    depth_var = tk.DoubleVar(value=1.0)
    v_top = tk.DoubleVar(value=1000.0)
    v_bot = tk.DoubleVar(value=0.0)
    eps_r = tk.DoubleVar(value=1.0)
    mesh_var = tk.DoubleVar(value=0.0)
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
    tk.Entry(wiz, textvariable=depth_var, width=20).grid(
        row=r, column=1, padx=8, pady=4)

    r += 1
    ttk.Separator(wiz, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Top electrode voltage (V):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    tk.Entry(wiz, textvariable=v_top, width=20).grid(
        row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Bottom electrode voltage (V):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    tk.Entry(wiz, textvariable=v_bot, width=20).grid(
        row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Relative permittivity (\u03b5r):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    tk.Entry(wiz, textvariable=eps_r, width=20).grid(
        row=r, column=1, padx=8, pady=4)

    r += 1
    ttk.Separator(wiz, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Mesh size (0 = auto):").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    tk.Entry(wiz, textvariable=mesh_var, width=20).grid(
        row=r, column=1, padx=8, pady=4)

    if include_auto_solve:
        r += 1
        tk.Checkbutton(wiz, text="Auto-solve after generation",
                       variable=auto_solve).grid(
            row=r, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

    def _get_config():
        cfg = {
            "problem_type": prob_type.get(),
            "units": units.get(),
            "depth": depth_var.get(),
            "voltage_top": v_top.get(),
            "voltage_bottom": v_bot.get(),
            "permittivity": eps_r.get(),
            "mesh_size": mesh_var.get(),
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
        wiz.destroy()
        on_simulate(femm_config)

    tk.Button(wiz, text="Simulate in FEMM", command=_do_simulate,
              width=22).grid(row=next_row, column=0, columnspan=2, pady=12)
