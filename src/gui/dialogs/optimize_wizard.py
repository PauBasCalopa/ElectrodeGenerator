"""Optimization wizard dialog.

Presents a UI for configuring and running parameter optimization.
Three algorithms are available:

* **Golden-section** — fast 1D search for one or a few parameters
  (sequential multi-parameter when more than one is selected).
* **Differential Evolution** — population-based global search that
  optimizes all selected parameters simultaneously.
* **NSGA-II** — multi-objective Pareto optimisation.  Returns a set
  of trade-off solutions (Pareto front) that the user can browse and
  apply individually.

The actual algorithms live in ``core.optimizer``.
"""

import csv
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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
    wiz.title("Optimize Parameters")
    wiz.resizable(True, True)
    wiz.transient(parent)
    wiz.geometry("580x700")

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
    tk.Label(main_frame, text="Parameters to optimize",
             font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=(4, 4))

    r += 1
    param_frame = tk.Frame(main_frame)
    param_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)

    from gui.dialogs._param_selector import build_param_selector
    get_selected, _ = build_param_selector(param_frame, profile,
                                            gap=gap, plate_length=plate_length)

    # --- Algorithm selection ---
    r += 1
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
        row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)
    r += 1
    tk.Label(main_frame, text="Algorithm",
             font=("Segoe UI", 10, "bold")).grid(
        row=r, column=0, columnspan=4, sticky=tk.W, pady=4)

    r += 1
    algo_var = tk.StringVar(value="nsga2")
    algo_combo = ttk.Combobox(main_frame, textvariable=algo_var,
                              values=["golden", "evolution", "nsga2"],
                              state="readonly", width=24)
    algo_combo.grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=4)

    # --- Golden-section settings ---
    r += 1
    gs_frame = tk.Frame(main_frame)
    gs_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW)

    tk.Label(gs_frame, text=(
        "Fast 1-D search that narrows a parameter range by the\n"
        "golden ratio each step.  Minimises \u0394E %.  When multiple\n"
        "parameters are selected they are optimised sequentially."),
        font=("Segoe UI", 8), fg="#555555", justify=tk.LEFT).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

    tk.Label(gs_frame, text="Tolerance:").grid(
        row=1, column=0, sticky=tk.W, pady=4)
    tol_entry = tk.Entry(gs_frame, width=20)
    tol_entry.insert(0, "0.001")
    tol_entry.grid(row=1, column=1, sticky=tk.W, pady=4)

    tk.Label(gs_frame, text="Max iterations:").grid(
        row=2, column=0, sticky=tk.W, pady=4)
    maxiter_entry = tk.Entry(gs_frame, width=20)
    maxiter_entry.insert(0, "20")
    maxiter_entry.grid(row=2, column=1, sticky=tk.W, pady=4)

    # --- DE settings ---
    de_frame = tk.Frame(main_frame)
    de_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW)

    tk.Label(de_frame, text=(
        "Population-based global search (Differential Evolution).\n"
        "Optimises all selected parameters simultaneously to\n"
        "minimise \u0394E %.  Good for rugged landscapes."),
        font=("Segoe UI", 8), fg="#555555", justify=tk.LEFT).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

    tk.Label(de_frame, text="Population size:").grid(
        row=1, column=0, sticky=tk.W, pady=4)
    pop_entry = tk.Entry(de_frame, width=20)
    pop_entry.insert(0, "16")
    pop_entry.grid(row=1, column=1, sticky=tk.W, pady=4)

    tk.Label(de_frame, text="Generations:").grid(
        row=2, column=0, sticky=tk.W, pady=4)
    gen_entry = tk.Entry(de_frame, width=20)
    gen_entry.insert(0, "30")
    gen_entry.grid(row=2, column=1, sticky=tk.W, pady=4)

    tk.Label(de_frame, text="Mutation (F):").grid(
        row=3, column=0, sticky=tk.W, pady=4)
    mut_entry = tk.Entry(de_frame, width=20)
    mut_entry.insert(0, "0.8")
    mut_entry.grid(row=3, column=1, sticky=tk.W, pady=4)

    tk.Label(de_frame, text="Crossover (CR):").grid(
        row=4, column=0, sticky=tk.W, pady=4)
    cr_entry = tk.Entry(de_frame, width=20)
    cr_entry.insert(0, "0.7")
    cr_entry.grid(row=4, column=1, sticky=tk.W, pady=4)

    # --- NSGA-II settings + objective checkboxes ---
    nsga2_frame = tk.Frame(main_frame)
    nsga2_frame.grid(row=r, column=0, columnspan=4, sticky=tk.EW)

    tk.Label(nsga2_frame, text=(
        "Multi-objective Pareto optimisation (NSGA-II).\n"
        "Returns a set of trade-off solutions instead of a single\n"
        "optimum.  Select \u2265 2 objectives below."),
        font=("Segoe UI", 8), fg="#555555", justify=tk.LEFT).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

    tk.Label(nsga2_frame, text="Objectives",
             font=("Segoe UI", 9, "bold")).grid(
        row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 2))

    _OBJ_DESCRIPTIONS = {
        'delta_e': '\u0394E % \u2014 field enhancement at electrode edge (lower = more uniform)',
        'compactness': 'Width \u2014 radial extent of the profile (lower = more compact)',
        'uniformity': 'CV(E) % \u2014 field coefficient of variation (lower = flatter E)',
        'height': 'Height \u2014 vertical extent of the profile (lower = thinner)',
    }

    from core.optimizer import ProfileOptimizer
    _obj_keys = list(ProfileOptimizer.OBJECTIVES.keys())
    _obj_vars = {}
    for oi, okey in enumerate(_obj_keys):
        desc = _OBJ_DESCRIPTIONS.get(okey, okey)
        var = tk.BooleanVar(value=(oi < 2))  # first two checked by default
        cb = tk.Checkbutton(nsga2_frame, text=desc, variable=var)
        cb.grid(row=2 + oi, column=0, columnspan=2, sticky=tk.W, padx=12)
        _obj_vars[okey] = var

    nsga2_sep_row = 2 + len(_obj_keys)
    ttk.Separator(nsga2_frame, orient=tk.HORIZONTAL).grid(
        row=nsga2_sep_row, column=0, columnspan=2, sticky=tk.EW, pady=4)

    ns_row = nsga2_sep_row + 1
    tk.Label(nsga2_frame, text="Population size:").grid(
        row=ns_row, column=0, sticky=tk.W, pady=4)
    nsga_pop_entry = tk.Entry(nsga2_frame, width=20)
    nsga_pop_entry.insert(0, "20")
    nsga_pop_entry.grid(row=ns_row, column=1, sticky=tk.W, pady=4)

    tk.Label(nsga2_frame, text="Generations:").grid(
        row=ns_row + 1, column=0, sticky=tk.W, pady=4)
    nsga_gen_entry = tk.Entry(nsga2_frame, width=20)
    nsga_gen_entry.insert(0, "30")
    nsga_gen_entry.grid(row=ns_row + 1, column=1, sticky=tk.W, pady=4)

    tk.Label(nsga2_frame, text="Mutation (F):").grid(
        row=ns_row + 2, column=0, sticky=tk.W, pady=4)
    nsga_mut_entry = tk.Entry(nsga2_frame, width=20)
    nsga_mut_entry.insert(0, "0.8")
    nsga_mut_entry.grid(row=ns_row + 2, column=1, sticky=tk.W, pady=4)

    tk.Label(nsga2_frame, text="Crossover (CR):").grid(
        row=ns_row + 3, column=0, sticky=tk.W, pady=4)
    nsga_cr_entry = tk.Entry(nsga2_frame, width=20)
    nsga_cr_entry.insert(0, "0.7")
    nsga_cr_entry.grid(row=ns_row + 3, column=1, sticky=tk.W, pady=4)

    # --- Pareto front table (shown only after nsga2 run) ---
    # Created here (before _toggle_algo) so the reference is available
    # when the initial toggle fires.
    pareto_r = r + 1  # reserve a row for it; actual grid row set later
    pareto_lf = tk.LabelFrame(main_frame, text="Pareto Front")
    pareto_lf.grid(row=99, column=0, columnspan=4, sticky=tk.NSEW, pady=4)
    pareto_lf.grid_remove()  # hidden until nsga2_complete

    pareto_tree = ttk.Treeview(pareto_lf, selectmode="browse", height=8)
    pareto_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    pareto_sb = ttk.Scrollbar(pareto_lf, orient=tk.VERTICAL,
                               command=pareto_tree.yview)
    pareto_tree.configure(yscrollcommand=pareto_sb.set)
    pareto_sb.pack(side=tk.RIGHT, fill=tk.Y)

    _pareto_data = []  # populated by nsga2_complete

    def _toggle_algo(*_):
        algo = algo_var.get()
        gs_frame.grid_remove()
        de_frame.grid_remove()
        nsga2_frame.grid_remove()
        pareto_lf.grid_remove()
        if algo == "golden":
            gs_frame.grid()
        elif algo == "evolution":
            de_frame.grid()
        else:
            nsga2_frame.grid()

    algo_var.trace_add('write', _toggle_algo)
    _toggle_algo()  # initial state

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

    # Place the Pareto table in its final row position (after result label)
    r += 1
    pareto_lf.grid_configure(row=r)

    # --- Buttons (pinned at bottom, outside scroll) ---
    btn_frame = tk.Frame(wiz)
    btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)

    start_btn = tk.Button(btn_frame, text="Start", width=14)
    start_btn.pack(side=tk.LEFT, padx=4)

    apply_btn = tk.Button(btn_frame, text="Apply to Profile",
                          width=18, state=tk.DISABLED)
    apply_btn.pack(side=tk.LEFT, padx=4)

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
    opt_result = {}
    cancel_event = threading.Event()

    def _safe_after(func):
        """Schedule *func* on the Tk main loop only if the wizard
        window still exists.  Prevents TclError when the user closes
        the dialog while the background thread is still running."""
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
            msg = (f"  Iter {iteration}: {pname} = {val:.6f}, "
                   f"\u0394E = {fef:.2f}%")
            _safe_after(lambda m=msg: _log(m))
        elif event == 'generation':
            pass  # logged via 'log' events from optimizer
        elif event == 'complete':
            result = args[0]
            opt_result.update(result)
            _safe_after(lambda: result_label.config(
                text=f"Optimal {result['param_name']} = "
                     f"{result['best_value']:.6f}  "
                     f"(\u0394E = {result['best_delta_e']:.2f}%)"))
            _safe_after(lambda: apply_btn.config(state=tk.NORMAL))
            _safe_after(lambda: export_csv_btn.config(state=tk.NORMAL))
        elif event in ('multi_complete', 'evolution_complete'):
            result = args[0]
            opt_result.update(result)
            vals = result['best_values']
            vals_str = ", ".join(f"{k}={v:.4f}" for k, v in vals.items())
            _safe_after(lambda: result_label.config(
                text=f"Optimal: {vals_str}  "
                     f"(\u0394E = {result['best_delta_e']:.2f}%)"))
            _safe_after(lambda: apply_btn.config(state=tk.NORMAL))
            _safe_after(lambda: export_csv_btn.config(state=tk.NORMAL))
        elif event == 'nsga2_complete':
            result = args[0]
            opt_result.update(result)
            _safe_after(lambda res=result: _populate_pareto(res))

    # --- Pareto helpers ---
    def _populate_pareto(result):
        """Fill the Pareto Treeview with solutions from NSGA-II."""
        _pareto_data.clear()
        _pareto_data.extend(result.get('pareto_front', []))

        obj_labels = result.get('objective_labels', [])
        p_names = result.get('param_names', [])

        cols = obj_labels + p_names
        pareto_tree['columns'] = cols
        pareto_tree.heading('#0', text='#')
        pareto_tree.column('#0', width=40, stretch=False)
        for c in cols:
            pareto_tree.heading(c, text=c)
            pareto_tree.column(c, width=80, anchor=tk.E)

        pareto_tree.delete(*pareto_tree.get_children())
        for i, sol in enumerate(_pareto_data):
            sc_vals = [f"{s:.3f}" for s in sol['scores']]
            p_vals = [f"{sol['values'][n]:.5f}" for n in p_names]
            pareto_tree.insert('', tk.END, iid=str(i), text=str(i),
                               values=sc_vals + p_vals)

        pareto_lf.grid()
        result_label.config(
            text=f"Pareto front: {len(_pareto_data)} solutions "
                 f"— select a row and click Apply")
        apply_btn.config(state=tk.NORMAL)
        export_csv_btn.config(state=tk.NORMAL)

    def _on_pareto_select(_event=None):
        sel = pareto_tree.selection()
        if sel:
            idx = int(sel[0])
            sol = _pareto_data[idx]
            sc_str = ", ".join(
                f"{lb}={s:.2f}"
                for lb, s in zip(
                    opt_result.get('objective_labels', []),
                    sol['scores']))
            result_label.config(text=f"Selected #{idx}: {sc_str}")

    pareto_tree.bind('<<TreeviewSelect>>', _on_pareto_select)

    # --- Start ---
    def _start():
        selected = get_selected()
        if selected is None:
            return

        algorithm = algo_var.get()

        errors = []
        if algorithm == "golden":
            r_tol = _validator.validate_float(tol_entry.get())
            if not r_tol:
                errors.append(f"Tolerance: {r_tol.error_message}")
            r_iter = _validator.validate_integer(maxiter_entry.get())
            if not r_iter:
                errors.append(f"Max iterations: {r_iter.error_message}")
        elif algorithm == "evolution":
            r_pop = _validator.validate_integer(pop_entry.get())
            if not r_pop:
                errors.append(f"Population: {r_pop.error_message}")
            r_gen = _validator.validate_integer(gen_entry.get())
            if not r_gen:
                errors.append(f"Generations: {r_gen.error_message}")
            r_mut = _validator.validate_float(mut_entry.get())
            if not r_mut:
                errors.append(f"Mutation (F): {r_mut.error_message}")
            r_cr = _validator.validate_float(cr_entry.get())
            if not r_cr:
                errors.append(f"Crossover (CR): {r_cr.error_message}")
        else:  # nsga2
            obj_keys = [k for k, v in _obj_vars.items() if v.get()]
            if len(obj_keys) < 2:
                errors.append("Select at least 2 objectives for NSGA-II.")
            r_pop = _validator.validate_integer(nsga_pop_entry.get())
            if not r_pop:
                errors.append(f"Population: {r_pop.error_message}")
            r_gen = _validator.validate_integer(nsga_gen_entry.get())
            if not r_gen:
                errors.append(f"Generations: {r_gen.error_message}")
            r_mut = _validator.validate_float(nsga_mut_entry.get())
            if not r_mut:
                errors.append(f"Mutation (F): {r_mut.error_message}")
            r_cr = _validator.validate_float(nsga_cr_entry.get())
            if not r_cr:
                errors.append(f"Crossover (CR): {r_cr.error_message}")
        if errors:
            messagebox.showwarning("Invalid input",
                                   "\n".join(errors), parent=wiz)
            return

        femm_config = get_femm_config()
        if femm_config is None:
            return

        cancel_event.clear()
        start_btn.config(text="Stop",
                         command=lambda: cancel_event.set())
        apply_btn.config(state=tk.DISABLED)
        export_csv_btn.config(state=tk.DISABLED)
        progress_text.config(state=tk.NORMAL)
        progress_text.delete("1.0", tk.END)
        progress_text.config(state=tk.DISABLED)
        result_label.config(text="")
        opt_result.clear()
        _pareto_data.clear()
        pareto_tree.delete(*pareto_tree.get_children())
        pareto_lf.grid_remove()

        def _run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from core.optimizer import ProfileOptimizer
                optimizer = ProfileOptimizer(
                    profile, current_config, gap, plate_length, femm_config)

                if algorithm == "nsga2":
                    optimizer.optimize_nsga2(
                        selected,
                        objective_keys=obj_keys,
                        population_size=r_pop.value,
                        generations=r_gen.value,
                        mutation_factor=r_mut.value,
                        crossover_prob=r_cr.value,
                        callback=_on_event,
                        cancel_flag=cancel_event)
                elif algorithm == "evolution":
                    optimizer.optimize_evolution(
                        selected,
                        population_size=r_pop.value,
                        generations=r_gen.value,
                        mutation_factor=r_mut.value,
                        crossover_prob=r_cr.value,
                        callback=_on_event,
                        cancel_flag=cancel_event)
                elif len(selected) == 1:
                    p = selected[0]
                    optimizer.optimize(
                        p['name'], (p['min'], p['max']),
                        r_tol.value, r_iter.value,
                        callback=_on_event,
                        cancel_flag=cancel_event)
                else:
                    names = [p['name'] for p in selected]
                    bounds = {p['name']: (p['min'], p['max'])
                              for p in selected}
                    optimizer.optimize_multi(
                        names, bounds, r_tol.value, r_iter.value,
                        callback=_on_event,
                        cancel_flag=cancel_event)
            except Exception as e:
                err_msg = str(e)
                _safe_after(lambda m=err_msg: _log(f"\nERROR: {m}"))
            finally:
                pythoncom.CoUninitialize()
                _safe_after(lambda: start_btn.config(
                    text="Start", command=_start))

        threading.Thread(target=_run, daemon=True).start()

    # --- Apply ---
    def _apply():
        if not opt_result:
            return
        # NSGA-II — apply selected Pareto row
        if 'pareto_front' in opt_result:
            sel = pareto_tree.selection()
            if not sel:
                messagebox.showinfo(
                    "No selection",
                    "Select a row from the Pareto front table first.",
                    parent=wiz)
                return
            idx = int(sel[0])
            sol = _pareto_data[idx]
            for name, val in sol['values'].items():
                on_apply(name, val, sol['scores'][0])
            return
        # Single-objective results
        if 'best_values' in opt_result:
            for name, val in opt_result['best_values'].items():
                on_apply(name, val, opt_result['best_delta_e'])
        else:
            on_apply(opt_result['param_name'],
                     opt_result['best_value'],
                     opt_result['best_delta_e'])

    # --- Export CSV ---
    def _export_csv():
        if not opt_result:
            return
        path = filedialog.asksaveasfilename(
            parent=wiz,
            title="Export optimisation results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if 'pareto_front' in opt_result:
                    obj_labels = opt_result.get('objective_labels', [])
                    p_names = opt_result.get('param_names', [])
                    writer.writerow(obj_labels + p_names)
                    for sol in _pareto_data:
                        row = [f"{s:.6f}" for s in sol['scores']]
                        row += [f"{sol['values'][n]:.6f}" for n in p_names]
                        writer.writerow(row)
                elif 'best_values' in opt_result:
                    names = list(opt_result['best_values'].keys())
                    writer.writerow(names + ['delta_e_pct'])
                    vals = [f"{opt_result['best_values'][n]:.6f}"
                            for n in names]
                    vals.append(f"{opt_result['best_delta_e']:.6f}")
                    writer.writerow(vals)
                else:
                    writer.writerow([opt_result['param_name'],
                                     'delta_e_pct'])
                    writer.writerow([f"{opt_result['best_value']:.6f}",
                                     f"{opt_result['best_delta_e']:.6f}"])
            _log(f"Results exported to {path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e), parent=wiz)

    start_btn.config(command=_start)
    apply_btn.config(command=_apply)
    export_csv_btn.config(command=_export_csv)
