"""Optimization wizard dialog.

Presents a UI for configuring and running golden-section parameter
optimization.  The actual algorithm lives in ``core.optimizer``.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox


def show_optimize_wizard(parent, profile, current_config, gap, plate_length,
                         on_apply):
    """Open the optimization wizard dialog.

    Args:
        parent: Parent tk window.
        profile: Currently selected profile instance.
        current_config: Dict of current parameter values.
        gap: Current electrode gap value.
        plate_length: Current plate length value.
        on_apply: Callback ``on_apply(param_name, value, delta_e)``
                  called when the user clicks "Apply to Profile".
    """
    # Check FEMM availability before building the dialog
    try:
        from simulation.femm_simulator import HAS_FEMM
        if not HAS_FEMM:
            raise ImportError
    except (ImportError, RuntimeError):
        messagebox.showerror(
            "FEMM Not Available",
            "pyfemm is required for optimization.\n\n"
            "Install it with:  pip install pyfemm\n"
            "FEMM 4.2 must also be installed on this system.",
            parent=parent)
        return

    wiz = tk.Toplevel(parent)
    wiz.title("Optimization Wizard")
    wiz.resizable(True, True)
    wiz.transient(parent)
    wiz.grab_set()
    wiz.geometry("560x720")

    main_frame = tk.Frame(wiz)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # --- Parameter selection ---
    r = 0
    tk.Label(main_frame, text="Optimization",
             font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, pady=(4, 4))

    r += 1
    tk.Label(main_frame, text="Parameter to optimize:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    param_names = [p['name'] for p in profile.parameters]
    param_var = tk.StringVar(value=param_names[0] if param_names else "")
    param_combo = ttk.Combobox(main_frame, textvariable=param_var,
                               values=param_names, state="readonly", width=18)
    param_combo.grid(row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Search range min:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    min_var = tk.DoubleVar(value=0.01)
    tk.Entry(main_frame, textvariable=min_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Search range max:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    max_var = tk.DoubleVar(value=2.0)
    tk.Entry(main_frame, textvariable=max_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    def _update_bounds(_event=None):
        name = param_var.get()
        for p in profile.parameters:
            if p['name'] == name:
                min_var.set(p['min'])
                max_var.set(p['max'])
                break
    param_combo.bind("<<ComboboxSelected>>", _update_bounds)
    _update_bounds()

    r += 1
    tk.Label(main_frame, text="Tolerance:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    tol_var = tk.DoubleVar(value=0.001)
    tk.Entry(main_frame, textvariable=tol_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Max iterations:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    maxiter_var = tk.IntVar(value=20)
    tk.Entry(main_frame, textvariable=maxiter_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    # --- Simulation settings ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Simulation Settings",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Top voltage (V):").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    vtop_var = tk.DoubleVar(value=1000.0)
    tk.Entry(main_frame, textvariable=vtop_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Bottom voltage (V):").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    vbot_var = tk.DoubleVar(value=0.0)
    tk.Entry(main_frame, textvariable=vbot_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Permittivity (\u03b5r):").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    eps_var = tk.DoubleVar(value=1.0)
    tk.Entry(main_frame, textvariable=eps_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Mesh size (0=auto):").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    mesh_var = tk.DoubleVar(value=0.0)
    tk.Entry(main_frame, textvariable=mesh_var, width=20).grid(
        row=r, column=1, sticky=tk.W, pady=4)

    # --- Progress ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Progress",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, pady=4)

    r += 1
    progress_text = tk.Text(main_frame, height=10, width=64,
                            state=tk.DISABLED, font=("Consolas", 9))
    progress_text.grid(row=r, column=0, columnspan=2, sticky=tk.NSEW, pady=4)
    main_frame.grid_rowconfigure(r, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)

    # --- Result ---
    r += 1
    result_label = tk.Label(main_frame, text="",
                            font=("Segoe UI", 10), fg="green")
    result_label.grid(row=r, column=0, columnspan=2, pady=4)

    # --- Buttons ---
    r += 1
    btn_frame = tk.Frame(main_frame)
    btn_frame.grid(row=r, column=0, columnspan=2, pady=8)

    start_btn = tk.Button(btn_frame, text="Start Optimization", width=18)
    start_btn.pack(side=tk.LEFT, padx=4)

    apply_btn = tk.Button(btn_frame, text="Apply to Profile",
                          width=18, state=tk.DISABLED)
    apply_btn.pack(side=tk.LEFT, padx=4)

    close_btn = tk.Button(btn_frame, text="Close", width=12,
                          command=wiz.destroy)
    close_btn.pack(side=tk.LEFT, padx=4)

    # --- State ---
    opt_result = {}

    def _log(msg):
        progress_text.config(state=tk.NORMAL)
        progress_text.insert(tk.END, msg + "\n")
        progress_text.see(tk.END)
        progress_text.config(state=tk.DISABLED)

    # --- Optimizer callback (called from background thread) ---
    def _on_optimizer_event(event, *args):
        if event == 'log':
            wiz.after(0, lambda m=args[0]: _log(m))
        elif event == 'progress':
            iteration, pname, val, fef = args
            msg = (f"  Iter {iteration}: {pname} = {val:.6f}, "
                   f"\u0394E = {fef:.2f}%")
            wiz.after(0, lambda m=msg: _log(m))
        elif event == 'complete':
            result = args[0]
            opt_result.update(result)
            wiz.after(0, lambda: result_label.config(
                text=f"Optimal {result['param_name']} = "
                     f"{result['best_value']:.6f}  "
                     f"(\u0394E = {result['best_delta_e']:.2f}%)"))
            wiz.after(0, lambda: apply_btn.config(state=tk.NORMAL))

    # --- Start / Apply ---
    def _start():
        param_name = param_var.get()
        if not param_name:
            messagebox.showwarning("No parameter",
                                   "Select a parameter to optimize.",
                                   parent=wiz)
            return

        start_btn.config(state=tk.DISABLED, text="Running\u2026")
        apply_btn.config(state=tk.DISABLED)
        progress_text.config(state=tk.NORMAL)
        progress_text.delete("1.0", tk.END)
        progress_text.config(state=tk.DISABLED)
        result_label.config(text="")
        opt_result.clear()

        # Capture all GUI state before spawning thread
        bounds = (min_var.get(), max_var.get())
        tolerance = tol_var.get()
        max_iter = maxiter_var.get()
        femm_config = {
            "problem_type": "planar",
            "units": "millimeters",
            "depth": 1.0,
            "voltage_top": vtop_var.get(),
            "voltage_bottom": vbot_var.get(),
            "permittivity": eps_var.get(),
            "mesh_size": mesh_var.get(),
        }

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from core.optimizer import ProfileOptimizer
                optimizer = ProfileOptimizer(
                    profile, current_config, gap, plate_length, femm_config)
                optimizer.optimize(
                    param_name, bounds, tolerance, max_iter,
                    callback=_on_optimizer_event)
            except Exception as e:
                err_msg = str(e)
                wiz.after(0, lambda m=err_msg: _log(f"\nERROR: {m}"))
            finally:
                pythoncom.CoUninitialize()
                wiz.after(0, lambda: start_btn.config(
                    state=tk.NORMAL, text="Start Optimization"))

        threading.Thread(target=_run, daemon=True).start()

    def _apply():
        if opt_result:
            name = opt_result['param_name']
            val = opt_result['best_value']
            delta_e = opt_result['best_delta_e']
            on_apply(name, val, delta_e)

    start_btn.config(command=_start)
    apply_btn.config(command=_apply)
