"""Parameter sweep wizard dialog.

Evaluates field enhancement (ΔE%) at evenly spaced parameter values
to explore the landscape before optimizing.  The sweep algorithm
lives in ``core.optimizer.ProfileOptimizer.sweep``.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core.validation import InputValidator

_validator = InputValidator()


def show_sweep_wizard(parent, profile, current_config, gap, plate_length):
    """Open the parameter-sweep wizard dialog.

    Args:
        parent: Parent tk window.
        profile: Currently selected profile instance.
        current_config: Dict of current parameter values.
        gap: Current electrode gap value.
        plate_length: Current plate length value.
    """
    # Check FEMM availability before building the dialog
    try:
        from simulation.femm_simulator import HAS_FEMM
        if not HAS_FEMM:
            raise ImportError
    except (ImportError, RuntimeError):
        messagebox.showerror(
            "FEMM Not Available",
            "pyfemm is required for parameter sweeps.\n\n"
            "Install it with:  pip install pyfemm\n"
            "FEMM 4.2 must also be installed on this system.",
            parent=parent)
        return

    wiz = tk.Toplevel(parent)
    wiz.title("Parameter Sweep")
    wiz.resizable(True, True)
    wiz.transient(parent)
    wiz.grab_set()
    wiz.geometry("560x620")

    main_frame = tk.Frame(wiz)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # --- Parameter selection ---
    r = 0
    tk.Label(main_frame, text="Parameter to sweep",
             font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=(4, 4))

    r += 1
    param_frame = tk.Frame(main_frame)
    param_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)

    from gui.dialogs._param_selector import build_param_selector
    get_selected, _ = build_param_selector(param_frame, profile,
                                            gap=gap, plate_length=plate_length)

    # --- Sweep settings ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Sweep",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=4)

    r += 1
    tk.Label(main_frame, text="Number of steps:").grid(
        row=r, column=0, sticky=tk.W, pady=4)
    steps_entry = tk.Entry(main_frame, width=20)
    steps_entry.insert(0, "10")
    steps_entry.grid(row=r, column=1, sticky=tk.W, pady=4)

    # --- Simulation settings ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Simulation Settings",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=4)

    r += 1
    sim_frame = tk.Frame(main_frame)
    sim_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)

    from gui.dialogs.femm_wizard import _build_femm_fields
    get_femm_config, _ = _build_femm_fields(sim_frame, include_auto_solve=False)

    # --- Progress ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Progress",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=4)

    r += 1
    progress_text = tk.Text(main_frame, height=10, width=64,
                            state=tk.DISABLED, font=("Consolas", 9))
    progress_text.grid(row=r, column=0, columnspan=4, sticky=tk.NSEW, pady=4)
    main_frame.grid_rowconfigure(r, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)

    # --- Result ---
    r += 1
    result_label = tk.Label(main_frame, text="",
                            font=("Segoe UI", 10), fg="green")
    result_label.grid(row=r, column=0, columnspan=4, pady=4)

    # --- Buttons ---
    r += 1
    btn_frame = tk.Frame(main_frame)
    btn_frame.grid(row=r, column=0, columnspan=4, pady=8)

    start_btn = tk.Button(btn_frame, text="Start Sweep", width=14)
    start_btn.pack(side=tk.LEFT, padx=4)

    def _close():
        cancel_event.set()
        wiz.destroy()

    close_btn = tk.Button(btn_frame, text="Close", width=12,
                          command=_close)
    close_btn.pack(side=tk.LEFT, padx=4)

    # --- State ---
    cancel_event = threading.Event()

    def _log(msg):
        progress_text.config(state=tk.NORMAL)
        progress_text.insert(tk.END, msg + "\n")
        progress_text.see(tk.END)
        progress_text.config(state=tk.DISABLED)

    # --- Callback (background thread -> UI) ---
    def _on_event(event, *args):
        if event == 'log':
            wiz.after(0, lambda m=args[0]: _log(m))
        elif event == 'progress':
            iteration, pname, val, fef = args
            msg = (f"  Step {iteration}: {pname} = {val:.6f}, "
                   f"\u0394E = {fef:.2f}%")
            wiz.after(0, lambda m=msg: _log(m))
        elif event == 'sweep_complete':
            pairs = args[0]
            if pairs:
                best = min(pairs, key=lambda p: p[1])
                wiz.after(0, lambda: result_label.config(
                    text=f"Best: \u0394E = {best[1]:.2f}% "
                         f"at value = {best[0]:.6f}"))

    # --- Start ---
    def _start():
        selected = get_selected()
        if selected is None:
            return
        if len(selected) != 1:
            messagebox.showwarning(
                "Select one parameter",
                "Sweep works on exactly one parameter.\n"
                "Check only one checkbox.",
                parent=wiz)
            return

        errors = []
        r_steps = _validator.validate_integer(steps_entry.get())
        if not r_steps:
            errors.append(f"Steps: {r_steps.error_message}")
        if errors:
            messagebox.showwarning("Invalid input",
                                   "\n".join(errors), parent=wiz)
            return

        femm_config = get_femm_config()
        if femm_config is None:
            return

        p = selected[0]
        cancel_event.clear()
        start_btn.config(text="Cancel",
                         command=lambda: cancel_event.set())
        progress_text.config(state=tk.NORMAL)
        progress_text.delete("1.0", tk.END)
        progress_text.config(state=tk.DISABLED)
        result_label.config(text="")

        num_steps = r_steps.value

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from core.optimizer import ProfileOptimizer
                optimizer = ProfileOptimizer(
                    profile, current_config, gap, plate_length, femm_config)
                optimizer.sweep(
                    p['name'], (p['min'], p['max']), num_steps,
                    callback=_on_event,
                    cancel_flag=cancel_event)
            except Exception as e:
                err_msg = str(e)
                wiz.after(0, lambda m=err_msg: _log(f"\nERROR: {m}"))
            finally:
                pythoncom.CoUninitialize()
                wiz.after(0, lambda: start_btn.config(
                    text="Start Sweep", command=_start))

        threading.Thread(target=_run, daemon=True).start()

    start_btn.config(command=_start)
