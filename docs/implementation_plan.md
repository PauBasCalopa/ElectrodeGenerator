# Implementation Plan: Interactive Rogowski GUI

## Goal

Build an interactive desktop GUI where users can select a profile type (Rogowski, Chang, Ernst), adjust parameters with sliders/inputs, see the profile update live, mirror/copy the geometry, and export to CSV, PNG, or DXF.

---

## Technology Choice

**Tkinter + matplotlib embedded**

- Tkinter is in the Python standard library (no new dependency)
- matplotlib's `FigureCanvasTkAgg` allows embedding a live plot directly in the window
- Already using matplotlib — no learning curve for the plotting side

---

## Architecture: Multiple Profiles

### Base class + subclasses in `profiles.py` (replaces `rogowski_geometry.py`)

```
ProfileBase (abstract)
├── RogowskiProfile
├── ChangProfile
└── ErnstProfile
```

Each profile defines:
- `name` — display name for the GUI dropdown
- `parameters` — list of parameter definitions (name, label, default, min, max, step)
- `generate_points(config)` — returns (x[], y[]) arrays
- `get_bounding_box()` / `to_polyline_points()` — inherited from base class

This way the GUI doesn't need to know the equations — it reads the parameter list from the selected profile and builds sliders dynamically.

### Profile Equations

| Profile   | Equations |
|-----------|-----------|
| Rogowski  | X = (s/π)(u + 1 + eᵘ cos v), Y = (s/π)(v + eᵘ sin v), v = π/2 |
| Chang     | X = u + cos(v)·sinh(u), Y = v + k·sin(v)·cosh(u), v = π/2, k > 0 (compactness) |
| Ernst     | X = u + k₀·cos(v)·sinh(u) + k₁·cos(2v)·sinh(2u), Y = v + k₀·sin(v)·cosh(u) + k₁·sin(2v)·cosh(2u), v = π/2, k₁ ≈ k₀²/8 |

#### Chang Profile

```
X = u + cos(v) · sinh(u)
Y = v + k · sin(v) · cosh(u)
```

- **v** = π/2 (constant)
- **u** = variable, range [0, u_max] where u_max depends on electrode width
- **k** = constant > 0, defines profile compactness (k=1 gives Rogowski-like shape, smaller k gives more compact profiles)

#### Ernst Profile

```
X = u + k₀ · cos(v) · sinh(u) + k₁ · cos(2v) · sinh(2u)
Y = v + k₀ · sin(v) · cosh(u) + k₁ · sin(2v) · cosh(2u)
```

- **v** = π/2 (constant, same meaning as Chang)
- **u** = variable, range [0, u_max] (same meaning as Chang)
- **k₀** = primary shape constant > 0
- **k₁** ≈ k₀² / 8 (auto-calculated from k₀, not an independent input)

Note: since k₁ is derived from k₀, the GUI only needs a slider for k₀. k₁ is computed internally and displayed as read-only info.

Rogowski, Chang and Ernst will be fully implemented.

---

## GUI Layout

```
┌──────────────────────────────────────────────────────────┐
│  Profile Generator                                 [—][x]│
├────────────────────┬─────────────────────────────────────┤
│                    │                                     │
│  Profile Type      │                                     │
│  [▼ Rogowski    ]  │                                     │
│                    │         Live Plot                   │
│  Parameters        │         (matplotlib canvas)         │
│  ──────────────    │                                     │
│                    │                                     │
│  s:    [====|==]   │                                     │
│        [ 1.00  ]   │                                     │
│                    │                                     │
│  u_start: [=|===]  │                                     │
│        [-2.00  ]   │                                     │
│                    │                                     │
│  u_end: [====|=]   │                                     │
│        [ 2.00  ]   │                                     │
│                    │                                     │
│  points: [==|===]  │                                     │
│        [ 100   ]   │                                     │
│                    │                                     │
│  ──────────────    │                                     │
│  Transform         │                                     │
│  [✓] Mirror H      │                                     │
│  [✓] Mirror V      │                                     │
│  [✓] Copy original │                                     │
│                    │                                     │
│  ──────────────    │                                     │
│  Bounding Box      │                                     │
│  X: [-0.95, 0.95]  │                                     │
│  Y: [-2.85, 2.85]  │                                     │
│                    │                                     │
│  ──────────────    │                                     │
│  [Export CSV]      │                                     │
│  [Export PNG]      │                                     │
│  [Export DXF]      │                                     │
│                    │                                     │
├────────────────────┴─────────────────────────────────────┤
│  Status: Ready                                           │
└──────────────────────────────────────────────────────────┘
```

Key features:
- **Profile dropdown** at the top — sliders rebuild dynamically per profile
- **Transform section** with three checkboxes:
  - **Mirror H** — reflect across X axis (negate Y)
  - **Mirror V** — reflect across Y axis (negate X)
  - **Copy original** — when checked, the mirrored copy is drawn alongside the original; when unchecked, only the mirrored version is shown

Mirror and copy logic lives in the GUI layer (post-processing on the generated points), not in the profile classes. This keeps the profile equations clean.

### Mirror / Copy Behavior

| Mirror H | Mirror V | Copy original | Result |
|-----------|-----------|---------------|--------|
| ☐         | ☐         | —             | Original curve only |
| ✓         | ☐         | ☐             | Horizontally mirrored curve only (Y negated) |
| ✓         | ☐         | ✓             | Original + horizontally mirrored copy |
| ☐         | ✓         | ☐             | Vertically mirrored curve only (X negated) |
| ☐         | ✓         | ✓             | Original + vertically mirrored copy |
| ✓         | ✓         | ☐             | Both axes mirrored (X and Y negated) |
| ✓         | ✓         | ✓             | Original + mirrored copy (both axes) |

---

## File Structure

```
main.py                  — CLI entry point (update to use profiles.py)
profiles.py              — NEW: base class + all profile implementations
dxf_exporter.py          — DXF export (no changes)
gui.py                   — NEW: GUI application
rogowski_geometry.py     — REMOVE (absorbed into profiles.py)
```

---

## Implementation Steps

### Step 1 — `profiles.py`: Base class + Rogowski

- `ProfileBase` abstract class with:
  - `name: str` property
  - `parameters: list` property — each entry is a dict: `{name, label, default, min, max, step, type}`
  - `generate_points(config) -> (x[], y[])` abstract method
  - `get_bounding_box(config)` concrete method (calls generate_points)
  - `to_polyline_points(config)` concrete method
- `RogowskiProfile` — move existing equations here
- `ChangProfile` — X = u + cos(v)·sinh(u), Y = v + k·sin(v)·cosh(u), u ∈ [0, u_max]
- `ErnstProfile` — X = u + k₀·cos(v)·sinh(u) + k₁·cos(2v)·sinh(2u), Y = v + k₀·sin(v)·cosh(u) + k₁·sin(2v)·cosh(2u), k₁ = k₀²/8, u ∈ [0, u_max]
- `PROFILES` dict mapping name -> class for the GUI dropdown

### Step 2 — `gui.py`: Window and layout

- `ProfileGeneratorGUI` class wrapping `tk.Tk`
- Left panel: `tk.Frame` (fixed width ~280px)
- Right panel: matplotlib `FigureCanvasTkAgg`
- Bottom: `tk.Label` status bar

### Step 3 — Profile dropdown + dynamic sliders

- `ttk.Combobox` at top of left panel listing profile names
- On profile change:
  - Destroy existing parameter widgets
  - Read `profile.parameters` list
  - Create slider + entry for each parameter
  - Trigger plot refresh

### Step 4 — Live plot

- On any parameter change, build config dict from current widget values
- Call `profile.generate_points(config)`
- Apply mirror/copy transforms (see below)
- `ax.clear()` → `ax.plot()` → `canvas.draw_idle()`
- Update bounding box labels
- Debounce with `after(50, ...)` to avoid redrawing mid-drag

### Step 5 — Mirror / Copy transforms

Three `tk.Checkbutton` widgets in a "Transform" section:
- **Mirror H** (`BooleanVar`) — when checked, reflect across X axis (negate Y values)
- **Mirror V** (`BooleanVar`) — when checked, reflect across Y axis (negate X values)
- **Copy original** (`BooleanVar`) — when checked, draw both the original and the mirrored version; when unchecked, replace the original with the mirrored version

Implementation (in the GUI update loop, after `generate_points`):
1. Start with original `x, y` arrays
2. If neither mirror is checked → plot original only, ignore copy checkbox
3. If a mirror is checked:
   - Compute `x_m, y_m` by negating the appropriate axis/axes
   - If copy original is checked → plot both `(x, y)` and `(x_m, y_m)` as separate curves
   - If copy original is unchecked → plot only `(x_m, y_m)`
4. Export functions use the same logic — CSV/DXF/PNG all export exactly what is shown on screen

Checkbox changes trigger the same debounced plot refresh as slider changes.

### Step 6 — Export buttons

| Button       | Action                                                        |
|--------------|---------------------------------------------------------------|
| Export CSV   | Save x,y points via `csv.writer` — file dialog               |
| Export PNG   | Save current figure via `fig.savefig()` — file dialog         |
| Export DXF   | Use existing `DXFExporter` — file dialog                      |

All exports include mirrored/copied curves if active — what you see is what you export.

### Step 7 — Update `main.py`

- Update CLI to import from `profiles.py` instead of `rogowski_geometry.py`
- Add `--profile` argument to select profile type from CLI

### Step 8 — Add remaining profiles

- **Chang** — implement with equations above. Note: u starts at 0, k controls compactness.
- **Ernst** — implement with equations above. k₁ auto-derived from k₀ (k₁ = k₀²/8). GUI shows computed k₁ as read-only info label.

Each is a self-contained class in `profiles.py` — no GUI changes needed.

---

## Parameter Definition Format

Each profile declares its parameters. The GUI reads this list and builds controls automatically. Adding a new profile with different parameters requires zero GUI code changes.

### Rogowski

```python
parameters = [
    {'name': 's',          'label': 's (electrode distance)', 'default': 1.0,   'min': 0.1,   'max': 20.0,  'step': 0.1, 'type': float},
    {'name': 'u_start',    'label': 'u start',                'default': -2.0,  'min': -10.0, 'max': 0.0,   'step': 0.1, 'type': float},
    {'name': 'u_end',      'label': 'u end',                  'default': 2.0,   'min': 0.0,   'max': 10.0,  'step': 0.1, 'type': float},
    {'name': 'num_points', 'label': 'Points',                 'default': 100,   'min': 10,    'max': 1000,  'step': 10,  'type': int},
]
```

### Chang

```python
parameters = [
    {'name': 'k',          'label': 'k (compactness)',        'default': 1.0,   'min': 0.01,  'max': 2.0,   'step': 0.01, 'type': float},
    {'name': 'u_end',      'label': 'u max (electrode width)','default': 2.0,   'min': 0.1,   'max': 10.0,  'step': 0.1,  'type': float},
    {'name': 'num_points', 'label': 'Points',                 'default': 100,   'min': 10,    'max': 1000,  'step': 10,   'type': int},
]
```

u_start is always 0 for Chang (not exposed as a slider).

### Ernst

```python
parameters = [
    {'name': 'k0',         'label': 'k₀ (shape constant)',   'default': 1.0,   'min': 0.01,  'max': 2.0,   'step': 0.01, 'type': float},
    {'name': 'u_end',      'label': 'u max (electrode width)','default': 2.0,   'min': 0.1,   'max': 10.0,  'step': 0.1,  'type': float},
    {'name': 'num_points', 'label': 'Points',                 'default': 100,   'min': 10,    'max': 1000,  'step': 10,   'type': int},
]
```

u_start is always 0 for Ernst (same as Chang). k₁ = k₀²/8 is auto-calculated and displayed as a read-only label below the k₀ slider.

---

## New Dependencies

None. Tkinter ships with Python on Windows.

---

## Entry Points

```bash
# GUI mode
python gui.py

# CLI mode (existing, updated)
python main.py
python main.py --profile rogowski
```

---

## Estimated Scope

| Step | Description                    | Complexity |
|------|--------------------------------|------------|
| 1    | profiles.py base + Rogowski    | Medium     |
| 2    | gui.py window + layout         | Small      |
| 3    | Profile dropdown + dyn sliders | Medium     |
| 4    | Live plot + debounce           | Medium     |
| 5    | Mirror / Copy transforms       | Medium     |
| 6    | Export buttons (CSV/PNG/DXF)   | Small      |
| 7    | Update main.py for profiles    | Small      |
| 8    | Add Chang + Ernst profiles     | Medium     |

Two new files (`profiles.py`, `gui.py`), one updated (`main.py`), one removed (`rogowski_geometry.py`). Roughly 400–450 lines total new code.
