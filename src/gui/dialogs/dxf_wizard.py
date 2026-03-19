"""DXF export configuration wizard dialog."""

import tkinter as tk
from tkinter import ttk


def show_dxf_wizard(parent, on_export):
    """Open a dialog to configure DXF export parameters.

    Args:
        parent: Parent tk window.
        on_export: Callback ``on_export(dxf_config)`` called with the
                   chosen settings when the user clicks Export.
    """
    wiz = tk.Toplevel(parent)
    wiz.title("DXF Export")
    wiz.resizable(False, False)
    wiz.transient(parent)
    wiz.grab_set()

    dxf_ver = tk.StringVar(value="R2000")
    curve_type = tk.StringVar(value="Spline")
    single_layer = tk.BooleanVar(value=False)

    r = 0
    tk.Label(wiz, text="DXF version:").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    ver_combo = ttk.Combobox(
        wiz, textvariable=dxf_ver,
        values=["R12", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"],
        state="readonly", width=18)
    ver_combo.grid(row=r, column=1, padx=8, pady=4)

    r += 1
    tk.Label(wiz, text="Curve entity type:").grid(
        row=r, column=0, sticky=tk.W, padx=8, pady=4)
    type_combo = ttk.Combobox(
        wiz, textvariable=curve_type,
        values=["Spline", "Polyline"],
        state="readonly", width=18)
    type_combo.grid(row=r, column=1, padx=8, pady=4)

    # R12 has no spline support — auto-force Polyline
    def _on_ver_change(_event=None):
        if dxf_ver.get() == "R12":
            curve_type.set("Polyline")
            type_combo.config(state="disabled")
        else:
            type_combo.config(state="readonly")
    ver_combo.bind("<<ComboboxSelected>>", _on_ver_change)

    r += 1
    tk.Checkbutton(wiz, text="Merge all curves into one layer",
                   variable=single_layer).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

    r += 1

    def _do_export():
        dxf_config = {
            "dxf_version": dxf_ver.get(),
            "curve_type": curve_type.get(),
            "single_layer": single_layer.get(),
        }
        wiz.destroy()
        on_export(dxf_config)

    tk.Button(wiz, text="Export DXF", command=_do_export,
              width=22).grid(row=r, column=0, columnspan=2, pady=12)
