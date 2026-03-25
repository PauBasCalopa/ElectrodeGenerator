"""Reusable parameter-selection widget for sweep and optimization wizards.

Displays one row per profile parameter with a checkbox, label,
and editable min / max fields pre-filled from the profile definition.

Optionally includes assembly-level parameters ``s`` (gap) and ``d``
(plate length) when the caller supplies their current values.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from core.validation import InputValidator

_validator = InputValidator()


def build_param_selector(parent, profile, start_row=0, *,
                         gap=None, plate_length=None):
    """Build a parameter-selection table inside *parent*.

    Each profile parameter gets a row with:

    * ``[✓]``  checkbox
    * label
    * min entry (pre-filled from ``p['min']``)
    * max entry (pre-filled from ``p['max']``)

    When *gap* and/or *plate_length* are provided, extra rows for
    ``s`` (gap) and ``d`` (plate length) are appended after the
    profile parameters.

    Args:
        parent: Tk container (Frame / Toplevel).
        profile: Profile instance whose ``.parameters`` list is used.
        start_row: Grid row to start placing widgets.
        gap: Current gap value.  If not ``None`` an ``s`` row is added.
        plate_length: Current plate length.  If not ``None`` a ``d``
            row is added.

    Returns:
        ``(get_selected, next_row)``

        *get_selected()* validates and returns a list of dicts::

            [{'name': str, 'min': float, 'max': float}, ...]

        or ``None`` on validation error (a warning dialog is shown).
        *next_row* is the grid row after the last widget.
    """
    r = start_row

    # Header row
    tk.Label(parent, text="", width=3).grid(row=r, column=0)
    tk.Label(parent, text="Parameter", anchor=tk.W).grid(
        row=r, column=1, sticky=tk.W, padx=4)
    tk.Label(parent, text="Min", anchor=tk.W).grid(
        row=r, column=2, padx=4)
    tk.Label(parent, text="Max", anchor=tk.W).grid(
        row=r, column=3, padx=4)
    r += 1

    rows = []  # list of (BooleanVar, name, min_entry, max_entry)

    for p in profile.parameters:
        var = tk.BooleanVar(value=False)
        tk.Checkbutton(parent, variable=var).grid(row=r, column=0)
        tk.Label(parent, text=p['label'], anchor=tk.W).grid(
            row=r, column=1, sticky=tk.W, padx=4, pady=1)

        min_e = tk.Entry(parent, width=10)
        min_e.insert(0, str(p['min']))
        min_e.grid(row=r, column=2, padx=4, pady=1)

        max_e = tk.Entry(parent, width=10)
        max_e.insert(0, str(p['max']))
        max_e.grid(row=r, column=3, padx=4, pady=1)

        rows.append((var, p['name'], min_e, max_e))
        r += 1

    # Assembly-level parameters ------------------------------------------
    _ASSEMBLY_PARAMS = []
    if gap is not None:
        _ASSEMBLY_PARAMS.append(
            ('s', 's \u2014 gap', gap, 0.1, max(gap * 3, 10.0)))
    if plate_length is not None:
        _ASSEMBLY_PARAMS.append(
            ('d', 'd \u2014 plate length', plate_length,
             0.5, max(plate_length * 3, 20.0)))

    if _ASSEMBLY_PARAMS:
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            row=r, column=0, columnspan=4, sticky=tk.EW, pady=4)
        r += 1
        tk.Label(parent, text="Assembly", anchor=tk.W,
                 font=("Segoe UI", 9, "italic")).grid(
            row=r, column=1, sticky=tk.W, padx=4)
        r += 1

        for name, label, current, lo, hi in _ASSEMBLY_PARAMS:
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(parent, variable=var).grid(row=r, column=0)
            tk.Label(parent, text=label, anchor=tk.W).grid(
                row=r, column=1, sticky=tk.W, padx=4, pady=1)

            min_e = tk.Entry(parent, width=10)
            min_e.insert(0, str(lo))
            min_e.grid(row=r, column=2, padx=4, pady=1)

            max_e = tk.Entry(parent, width=10)
            max_e.insert(0, str(hi))
            max_e.grid(row=r, column=3, padx=4, pady=1)

            rows.append((var, name, min_e, max_e))
            r += 1

    def get_selected():
        """Return validated list of selected parameters or None."""
        selected = [(name, min_e, max_e)
                     for var, name, min_e, max_e in rows if var.get()]
        if not selected:
            messagebox.showwarning(
                "No parameters selected",
                "Check at least one parameter.",
                parent=parent)
            return None

        errors = []
        result = []
        for name, min_e, max_e in selected:
            r_min = _validator.validate_float(min_e.get())
            r_max = _validator.validate_float(max_e.get())
            if not r_min:
                errors.append(f"{name} min: {r_min.error_message}")
            if not r_max:
                errors.append(f"{name} max: {r_max.error_message}")
            if r_min and r_max and r_min.value >= r_max.value:
                errors.append(f"{name}: min must be less than max")
            if r_min and r_max and r_min.value < r_max.value:
                result.append({
                    'name': name,
                    'min': r_min.value,
                    'max': r_max.value,
                })

        if errors:
            messagebox.showwarning(
                "Invalid input",
                "\n".join(errors),
                parent=parent)
            return None

        return result

    return get_selected, r
