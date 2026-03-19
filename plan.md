# Architecture Refactoring Plan

## Current State — Problem Diagnosis

**File inventory** (source lines):

| File | Lines | Responsibility |
|---|---|---|
| `gui.py` | **912** | UI + geometry + plotting + 4 export formats + simulation + optimization |
| `InputValidator.py` | 326 | Input validation (docstring references wrong project) |
| `profiles.py` | 191 | Profile math — **cleanest module** |
| `femm_exporter.py` | 188 | Lua script generation |
| `femm_simulator.py` | 180 | Live pyfemm COM driver |
| `dxf_exporter.py` | 172 | DXF export (has legacy methods) |
| `main.py` | 84 | Entry point + CLI mode |
| `contour.py` | 71 | Shared contour building — **recently extracted, clean** |
| `version.py` | 11 | Metadata |
| **Total** | **~2,135** | |

## 6 Architectural Problems

1. **`gui.py` is a 912-line monolith** mixing 6 unrelated concerns:
   - UI construction & widget binding (~200 lines)
   - Electrode assembly geometry building (~80 lines of pure math)
   - Plot refresh logic (~60 lines)
   - Export orchestration: CSV, PNG, DXF wizard, FEMM wizard (~200 lines)
   - Simulation thread management (~80 lines)
   - Optimization wizard with golden-section search (~250 lines)

2. **Duplicated FEMM model-building** between `femm_simulator.py` and `femm_exporter.py`:
   - Both implement: problem setup, materials, boundaries, electrode geometry, outer box, dielectric block labels
   - One emits Python COM calls, the other emits Lua strings — same logic, two representations

3. **Business logic trapped in GUI class**:
   - `_build_assembly_curves()` and `_build_curves_from_points()` are pure geometry with zero UI dependency
   - `_evaluate()` and the golden-section loop are pure algorithm — no UI needed

4. **Naming & hygiene issues**:
   - `InputValidator.py` uses PascalCase filename (rest uses snake_case)
   - Its docstring says "AC Ramp Breakdown Test System"
   - `dxf_exporter.py` has unused legacy methods (`add_rogowski_curve`, `add_bounding_box`)

5. **No package structure** — everything flat in `src/`, imports rely on `sys.path` / working directory

6. **Implicit coupling** — `gui.py` does lazy imports (`from femm_simulator import ...`) inside methods to avoid import errors when pyfemm isn't installed. This is a dependency-injection problem.

---

## Target Architecture

```
src/
├── main.py                      # Entry point only (slim)
├── version.py                   # Unchanged
│
├── core/                        # Pure logic — zero UI, zero I/O
│   ├── __init__.py
│   ├── profiles.py              # ProfileBase ABC + all profiles + PROFILES registry
│   ├── assembly.py              # build_assembly_curves(), build_curves_from_points()
│   ├── contour.py               # build_top_contour()  (existing, moved)
│   ├── optimizer.py             # ProfileOptimizer (algorithm only)
│   └── validation.py            # InputValidator (renamed, fixed docstring)
│
├── exporters/                   # File output — no UI
│   ├── __init__.py
│   ├── csv_exporter.py          # export_csv(curves, path)
│   ├── png_exporter.py          # export_png(fig, path)
│   ├── dxf_exporter.py          # DXFExporter (cleaned)
│   └── femm_exporter.py         # FEMMExporter (Lua gen, delegates to femm_model)
│
├── simulation/                  # FEMM integration
│   ├── __init__.py
│   ├── femm_model.py            # FEMMModelBuilder — shared model-building logic
│   ├── femm_simulator.py        # FEMMSimulator (live COM, uses femm_model)
│   └── femm_runner.py           # Thread orchestration for simulate + optimize
│
├── gui/                         # UI only — no math, no I/O
│   ├── __init__.py
│   ├── app.py                   # ProfileGeneratorGUI (slim coordinator)
│   ├── plot_panel.py            # Matplotlib canvas + refresh
│   └── dialogs/
│       ├── __init__.py
│       ├── dxf_wizard.py        # DXF config dialog
│       ├── femm_wizard.py       # FEMM export config dialog
│       └── optimize_wizard.py   # Optimization wizard dialog
│
└── assets/
    └── icon.png
```

---

## Dependency Flow (target)

```
main.py
  ├── gui/app.py
  │     ├── gui/plot_panel.py       → core/assembly
  │     ├── gui/dialogs/*           → core/optimizer, exporters/*
  │     │
  │     ├── core/profiles           → numpy (only)
  │     ├── core/assembly           → core/profiles
  │     ├── core/contour            → math (only)
  │     └── core/optimizer          → core/assembly, core/contour, simulation/femm_simulator
  │
  ├── exporters/dxf_exporter       → ezdxf
  ├── exporters/femm_exporter      → simulation/femm_model, core/contour
  │
  └── simulation/femm_model        → (abstract)
        ├── simulation/femm_simulator  → pyfemm (optional)
        └── exporters/femm_exporter    → (Lua backend)
```

**Key rule:** Arrows point downward only. `core/` never imports from `gui/` or `exporters/`. `exporters/` never imports from `gui/`.

---

## Refactoring Phases

### Phase 1 — Extract `core/assembly.py`

**What moves out of `gui.py`:**
- `_build_assembly_curves()` → free function `build_assembly_curves(x, y, gap, plate_length, is_axi=False)`
- `_build_curves_from_points()` → free function `build_curves_from_points(x, y, gap, plate_length)`

**Why first:** These are pure-math functions with zero tkinter dependency. Moving them unblocks all later phases.

### Phase 2 — Extract `core/optimizer.py`

**What moves out of `gui.py`:**
- `_evaluate()` (~25 lines)
- `_run_optimization()` golden-section search (~70 lines)

**New class:** `ProfileOptimizer` with a `callback` parameter replacing `wiz.after()` calls.

### Phase 3 — Unify FEMM model-building into `simulation/femm_model.py`

**Eliminate duplication** between `femm_simulator.py` and `femm_exporter.py` via a backend strategy pattern:
- `FEMMModelBuilder.build(curves, config)` — shared logic
- `ComBackend` — emits pyfemm COM calls
- `LuaBackend` — collects Lua script lines

### Phase 4 — Extract exporters into `exporters/` package

- `csv_exporter.py` — pure `export_csv(curves, path)` function
- `png_exporter.py` — pure `export_png(fig, path)` function
- Move `dxf_exporter.py` and `femm_exporter.py` (cleaned up)

### Phase 5 — Split `gui.py` into `gui/` package

- `gui/app.py` — slim coordinator
- `gui/plot_panel.py` — matplotlib canvas + refresh
- `gui/dialogs/dxf_wizard.py` — DXF config dialog
- `gui/dialogs/femm_wizard.py` — FEMM export config dialog
- `gui/dialogs/optimize_wizard.py` — optimization wizard UI shell

### Phase 6 — Cleanup & hygiene

- Move `InputValidator.py` → `core/validation.py`, fix docstring
- Move `profiles.py` → `core/profiles.py`
- Move `contour.py` → `core/contour.py`
- Remove legacy methods from `dxf_exporter.py`
- Update `main.py` imports
- Add `__init__.py` files

---

## Execution Status

All six phases have been implemented:

| Phase | Status |
|---|---|
| Extract `core/assembly.py` | ✅ Complete |
| Extract `core/optimizer.py` | ✅ Complete |
| Unify FEMM model builder | ✅ Complete (`simulation/femm_model.py` with `ComBackend` / `LuaBackend`) |
| Extract exporters | ✅ Complete (`exporters/csv_exporter.py`, `png_exporter.py`, `dxf_exporter.py`, `femm_exporter.py`) |
| Split `gui.py` → `gui/` package | ✅ Complete (`gui/app.py` + `gui/dialogs/*`) |
| Cleanup & hygiene | ✅ Complete (renamed + fixed docstring, removed legacy methods, updated imports) |

### Line counts after refactoring

| Module | Lines | Role |
|---|---|---|
| `gui/app.py` | 474 | UI coordinator (was 912) |
| `gui/dialogs/optimize_wizard.py` | 227 | Optimization dialog |
| `simulation/femm_model.py` | 225 | Shared FEMM model builder (NEW — replaces duplication) |
| `core/validation.py` | 191 | Input validation (fixed docstring) |
| `core/profiles.py` | 191 | Profile math (unchanged) |
| `simulation/femm_simulator.py` | 110 | Live FEMM driver (was 180 — model building extracted) |
| `core/optimizer.py` | 107 | Golden-section optimizer (extracted from GUI) |
| `gui/dialogs/femm_wizard.py` | 88 | FEMM export dialog |
| `main.py` | 84 | Entry point |
| `exporters/femm_exporter.py` | 74 | Lua script gen (was 188 — model building extracted) |
| `core/contour.py` | 71 | Contour building |
| `exporters/dxf_exporter.py` | 63 | DXF export (cleaned — was 172) |
| `gui/dialogs/dxf_wizard.py` | 57 | DXF export dialog |
| `core/assembly.py` | 43 | Electrode geometry (extracted from GUI) |
| `exporters/csv_exporter.py` | 14 | CSV export (extracted from GUI) |
| `version.py` | 11 | Metadata |
| `exporters/png_exporter.py` | 9 | PNG export (extracted from GUI) |
