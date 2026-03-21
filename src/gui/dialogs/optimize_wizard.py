"""Optimization wizard dialog.

Presents a UI for configuring and running golden-section parameter
optimization.  The actual algorithm lives in ``core.optimizer``.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core.validation import InputValidator

_validator = InputValidator()


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
    min_entry = tk.Entry(main_frame, width=20)
    min_entry.insert(0, "0.01")
    min_entry.grid(row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Search range max:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    max_entry = tk.Entry(main_frame, width=20)
    max_entry.insert(0, "2.0")
    max_entry.grid(row=r, column=1, sticky=tk.W, pady=4)

    def _update_bounds(_event=None):
        name = param_var.get()
        for p in profile.parameters:
            if p['name'] == name:
                min_entry.delete(0, tk.END)
                min_entry.insert(0, str(p['min']))
                max_entry.delete(0, tk.END)
                max_entry.insert(0, str(p['max']))
                break
    param_combo.bind("<<ComboboxSelected>>", _update_bounds)
    _update_bounds()

    r += 1
    tk.Label(main_frame, text="Tolerance:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    tol_entry = tk.Entry(main_frame, width=20)
    tol_entry.insert(0, "0.001")
    tol_entry.grid(row=r, column=1, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Max iterations:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    maxiter_entry = tk.Entry(main_frame, width=20)
    maxiter_entry.insert(0, "20")
    maxiter_entry.grid(row=r, column=1, sticky=tk.W, pady=4)

    # --- Simulation settings (reuse shared FEMM fields) ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=2, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Simulation Settings",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=2, sticky=tk.W, pady=4)

    r += 1
    sim_frame = tk.Frame(main_frame)
    sim_frame.grid(row=r, column=0, columnspan=2, sticky=tk.EW, pady=4)

    from gui.dialogs.femm_wizard import _build_femm_fields
    get_femm_config, _ = _build_femm_fields(sim_frame, include_auto_solve=False)

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

    def _close():
        cancel_event.set()
        wiz.destroy()

    close_btn = tk.Button(btn_frame, text="Close", width=12,
                          command=_close)
    close_btn.pack(side=tk.LEFT, padx=4)

    # --- State ---
    opt_result = {}
    cancel_event = threading.Event()

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

        # Validate all numerical inputs
        errors = []

        r_min = _validator.validate_float(min_entry.get())
        if not r_min:
            errors.append(f"Search range min: {r_min.error_message}")
        r_max = _validator.validate_float(max_entry.get())
        if not r_max:
            errors.append(f"Search range max: {r_max.error_message}")
        if r_min and r_max and r_min.value >= r_max.value:
            errors.append("Search range min must be less than max")

        r_tol = _validator.validate_float(tol_entry.get())
        if not r_tol:
            errors.append(f"Tolerance: {r_tol.error_message}")
        r_iter = _validator.validate_integer(maxiter_entry.get())
        if not r_iter:
            errors.append(f"Max iterations: {r_iter.error_message}")

        if errors:
            messagebox.showwarning("Invalid input",
                                   "\n".join(errors),
                                   parent=wiz)
            return

        femm_config = get_femm_config()
        if femm_config is None:
            return

        cancel_event.clear()
        start_btn.config(state=tk.NORMAL, text="Cancel")
        start_btn.config(command=lambda: cancel_event.set())
        apply_btn.config(state=tk.DISABLED)
        progress_text.config(state=tk.NORMAL)
        progress_text.delete("1.0", tk.END)
        progress_text.config(state=tk.DISABLED)
        result_label.config(text="")
        opt_result.clear()

        # Capture validated values before spawning thread
        bounds = (r_min.value, r_max.value)
        tolerance = r_tol.value
        max_iter = r_iter.value

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from core.optimizer import ProfileOptimizer
                optimizer = ProfileOptimizer(
                    profile, current_config, gap, plate_length, femm_config)
                optimizer.optimize(
                    param_name, bounds, tolerance, max_iter,
                    callback=_on_optimizer_event,
                    cancel_flag=cancel_event)
            except Exception as e:
                err_msg = str(e)
                wiz.after(0, lambda m=err_msg: _log(f"\nERROR: {m}"))
            finally:
                pythoncom.CoUninitialize()
                def _restore():
                    start_btn.config(state=tk.NORMAL,
                                     text="Start Optimization",
                                     command=_start)
                wiz.after(0, _restore)

        threading.Thread(target=_run, daemon=True).start()

    def _apply():
        if opt_result:
            name = opt_result['param_name']
            val = opt_result['best_value']
            delta_e = opt_result['best_delta_e']
            on_apply(name, val, delta_e)

    start_btn.config(command=_start)
    apply_btn.config(command=_apply)
