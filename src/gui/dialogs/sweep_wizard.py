"""Parameter sweep wizard dialog.

Evaluates field enhancement (ΔE%) at evenly spaced parameter values
to explore the landscape before optimizing.  When multiple parameters
are selected they are swept one at a time while holding the others
fixed.  The sweep algorithm lives in ``core.optimizer.ProfileOptimizer``.
"""

import csv
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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
    wiz.geometry("580x660")

    # --- Scrollable content area ---
    outer = tk.Frame(wiz)
    outer.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(outer, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    main_frame = tk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=main_frame, anchor=tk.NW)

    def _on_frame_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event):
        canvas.itemconfig(win_id, width=event.width)

    main_frame.bind("<Configure>", _on_frame_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    wiz.bind("<Destroy>", lambda _: canvas.unbind_all("<MouseWheel>"))

    # --- Parameter selection ---
    r = 0
    tk.Label(main_frame, text="Parameters to sweep",
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

    # --- Buttons (pinned at bottom, outside scroll) ---
    btn_frame = tk.Frame(wiz)
    btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)

    start_btn = tk.Button(btn_frame, text="Start Sweep", width=14)
    start_btn.pack(side=tk.LEFT, padx=4)

    export_csv_btn = tk.Button(btn_frame, text="Export CSV",
                               width=12, state=tk.DISABLED)
    export_csv_btn.pack(side=tk.LEFT, padx=4)

    def _close():
        cancel_event.set()
        wiz.destroy()

    close_btn = tk.Button(btn_frame, text="Close", width=12,
                          command=_close)
    close_btn.pack(side=tk.LEFT, padx=4)

    # --- State ---
    sweep_results = {}  # {param_name: [(value, delta_e), ...]}
    _sweep_param_name = ['']  # mutable container for single-sweep name
    cancel_event = threading.Event()

    def _safe_after(func):
        """Schedule *func* on the Tk main loop only if the wizard
        window still exists."""
        try:
            if wiz.winfo_exists():
                wiz.after(0, func)
        except Exception:
            pass

    def _log(msg):
        progress_text.config(state=tk.NORMAL)
        progress_text.insert(tk.END, msg + "\n")
        progress_text.see(tk.END)
        progress_text.config(state=tk.DISABLED)

    # --- Callback (background thread -> UI) ---
    def _on_event(event, *args):
        if event == 'log':
            _safe_after(lambda m=args[0]: _log(m))
        elif event == 'progress':
            iteration, pname, val, fef = args
            msg = (f"  Step {iteration}: {pname} = {val:.6f}, "
                   f"\u0394E = {fef:.2f}%")
            _safe_after(lambda m=msg: _log(m))
        elif event == 'sweep_complete':
            pairs = args[0]
            sweep_results.clear()
            sweep_results[_sweep_param_name[0]] = pairs
            if pairs:
                best = min(pairs, key=lambda p: p[1])
                _safe_after(lambda: result_label.config(
                    text=f"Best: \u0394E = {best[1]:.2f}% "
                         f"at value = {best[0]:.6f}"))
            _safe_after(lambda: export_csv_btn.config(state=tk.NORMAL))
        elif event == 'sweep_multi_complete':
            all_results = args[0]
            sweep_results.clear()
            sweep_results.update(all_results)
            parts = []
            for pname, pairs in all_results.items():
                if pairs:
                    best = min(pairs, key=lambda p: p[1])
                    parts.append(
                        f"{pname} = {best[0]:.4f} "
                        f"(\u0394E = {best[1]:.2f}%)")
            _safe_after(lambda t=", ".join(parts):
                      result_label.config(text=f"Best: {t}"))
            _safe_after(lambda: export_csv_btn.config(state=tk.NORMAL))

    # --- Start ---
    def _start():
        selected = get_selected()
        if selected is None:
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

        cancel_event.clear()
        start_btn.config(text="Cancel",
                         command=lambda: cancel_event.set())
        export_csv_btn.config(state=tk.DISABLED)
        progress_text.config(state=tk.NORMAL)
        progress_text.delete("1.0", tk.END)
        progress_text.config(state=tk.DISABLED)
        result_label.config(text="")
        sweep_results.clear()

        num_steps = r_steps.value
        if len(selected) == 1:
            _sweep_param_name[0] = selected[0]['name']

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from core.optimizer import ProfileOptimizer
                optimizer = ProfileOptimizer(
                    profile, current_config, gap, plate_length, femm_config)
                if len(selected) == 1:
                    p = selected[0]
                    optimizer.sweep(
                        p['name'], (p['min'], p['max']), num_steps,
                        callback=_on_event,
                        cancel_flag=cancel_event)
                else:
                    optimizer.sweep_multi(
                        selected, num_steps,
                        callback=_on_event,
                        cancel_flag=cancel_event)
            except Exception as e:
                err_msg = str(e)
                _safe_after(lambda m=err_msg: _log(f"\nERROR: {m}"))
            finally:
                pythoncom.CoUninitialize()
                _safe_after(lambda: start_btn.config(
                    text="Start Sweep", command=_start))

        threading.Thread(target=_run, daemon=True).start()

    # --- Export CSV ---
    def _export_csv():
        if not sweep_results:
            return
        path = filedialog.asksaveasfilename(
            parent=wiz,
            title="Export sweep results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['parameter', 'value', 'delta_e_pct'])
                for pname, pairs in sweep_results.items():
                    for val, de in pairs:
                        writer.writerow([pname, f"{val:.6f}",
                                         f"{de:.6f}"])
            _log(f"Sweep exported to {path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e), parent=wiz)

    start_btn.config(command=_start)
    export_csv_btn.config(command=_export_csv)
