# Electrode Profile Generator — User Guide

**Version 1.4.0** · Pau Bas Calopa · 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [GUI Interface](#gui-interface)
   - [Profile Selection](#profile-selection)
   - [Parameters](#parameters)
   - [Electrode Assembly](#electrode-assembly)
   - [Ernst Auto k₀](#ernst-auto-k₀)
4. [Exporting](#exporting)
   - [CSV Export](#csv-export)
   - [PNG Export](#png-export)
   - [DXF Export](#dxf-export)
   - [FEMM Lua Export](#femm-lua-export)
5. [Using with SolidWorks](#using-with-solidworks)
6. [Using with FEMM 4.2](#using-with-femm-42)
7. [CLI Mode](#cli-mode)
8. [Building the Executable](#building-the-executable)
9. [Profile Equations Reference](#profile-equations-reference)

---

## Overview

The Electrode Profile Generator is a desktop tool for designing parallel plate electrodes with mathematically defined edge profiles. It supports three profile types (Rogowski, Chang, Ernst), provides a live interactive preview, and exports geometry for CAD (SolidWorks, AutoCAD) and FEM simulation (FEMM 4.2).

---

## Installation

### Requirements

- Python 3.9 or later
- Dependencies: `numpy`, `matplotlib`, `ezdxf`

### Setup

```bash
git clone https://github.com/PauBasCalopa/ElectrodeGenerator.git
cd ElectrodeGenerator
pip install -r requirements.txt
```

### Launch

```bash
cd src
python main.py
```

---

## GUI Interface

The main window is divided into two areas:

- **Left panel** — profile selection, parameters, electrode assembly settings, and export buttons
- **Right panel** — live matplotlib plot showing the current profile or electrode assembly

### Profile Selection

Use the **Profile Type** dropdown at the top to switch between:

| Profile    | Description |
|------------|-------------|
| **Rogowski** | Classic Rogowski profile, scaled by electrode gap `s` |
| **Chang**    | Parametric profile with compactness factor `k` |
| **Ernst**    | Two-term profile with auto-calculated k₁ = k₀²/8 |

When you change the profile, the parameter sliders update automatically.

### Parameters

Each profile exposes its own set of parameters as sliders with text entry boxes:

- **Sliders** — drag for quick adjustment
- **Entry boxes** — type exact values and press Enter; accepts both `.` and `,` as decimal separator (European format)
- **Extended range** — if you type a value beyond the slider range, the slider auto-extends

### Electrode Assembly

The **Electrode Assembly** section controls the physical electrode construction:

| Parameter | Description |
|-----------|-------------|
| **s** (gap) | Distance between the two parallel electrodes (default: 1.0, range: 0.1–10) |
| **d** (plate length) | Length of the flat plate portion of each electrode (default: 5.0, range: 0.5–30) |
| **Build electrode assembly** | When checked, displays the full mirrored assembly (top + bottom electrodes with flat plates) |

The gap parameter `s` is always passed to the profile equations — for Rogowski it scales the entire profile, for Chang and Ernst it's available for edge-effect calculations.

### Ernst Auto k₀

When using the Ernst profile, the **Auto k₀ (no edge effect)** button calculates the optimal k₀ value that eliminates edge effects for the current gap `s`:

```
k₀ = 1.72 · e^(-3.5·s)
```

This relationship is valid for s < 3. At s ≈ 3, edge effects become significant and a warning is shown in the info area.

---

## Exporting

All exports use a default filename of `ProfileType_YYYYMMDD_HHMMSS.ext`.

### CSV Export

Exports all visible curves as a table with columns: `curve`, `x`, `y`.

Each curve (e.g. Top-Right, Top-Left, Top Plate, Bot-Right, Bot-Left, Bot Plate) is labelled in the `curve` column.

### PNG Export

Saves the current plot as a 150 DPI PNG image.

### DXF Export

Click **Export DXF…** to open the DXF wizard:

| Option | Values | Default | Notes |
|--------|--------|---------|-------|
| **DXF version** | R12, R2000, R2004, R2007, R2010, R2013, R2018 | R2000 | R12 for FEMM; R2000 for SolidWorks/AutoCAD |
| **Curve entity type** | Spline, Polyline | Spline | Spline = smooth CAD curves; Polyline = segmented lines |
| **Merge into one layer** | checkbox | off | When on, all curves go to a single `PROFILE` layer |

**Notes:**

- **R12** is required for FEMM 4.2 DXF import (ASCII R12 format). When R12 is selected, the curve type is automatically set to Polyline (R12 does not support SPLINE entities).
- **Spline** entities are recommended for SolidWorks — they import as editable sketch splines rather than segmented polylines.
- Flat plates are always exported as polylines regardless of the curve type setting (they are straight lines).
- When "Merge into one layer" is off, each curve gets its own named layer (e.g. `TOP_RIGHT`, `BOT_PLATE`).

### FEMM Lua Export

Click **Export FEMM Lua…** to open the FEMM simulation wizard:

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Problem type** | planar | `planar` or `axisymmetric` |
| **Units** | millimeters | Must match your electrode dimensions |
| **Depth** | 1.0 | Depth for planar problems (ignored in axi) |
| **Top electrode voltage** | 1000 V | Fixed voltage on the top electrode |
| **Bottom electrode voltage** | 0 V | Fixed voltage on the bottom electrode |
| **Relative permittivity (εr)** | 1.0 | Permittivity of the gap dielectric (1.0 = vacuum/air) |
| **Mesh size** | 0 (auto) | Element size; 0 lets FEMM auto-mesh |
| **Auto-solve** | off | When checked, the script runs `ei_analyze()` + `ei_loadsolution()` |

**What the generated Lua script does:**

1. Creates a new electrostatic document (`newdocument(1)`)
2. Defines the problem (units, type, precision)
3. Adds a dielectric material with the specified εr
4. Defines boundary conditions (top voltage, bottom voltage, outer Neumann boundary)
5. Builds the full electrode assembly geometry as nodes + segments
6. Assigns voltage boundary conditions to electrode segments
7. Creates an outer boundary rectangle with padding
8. Places a dielectric block label in the gap region
9. Optionally runs the solver

**Axisymmetric mode:** Only the right half of the assembly is exported (r ≥ 0). The left boundary at r = 0 is the axis of symmetry, which FEMM handles automatically.

---

## Using with SolidWorks

1. In the GUI, configure your profile and electrode assembly
2. Click **Export DXF…**
3. Settings: **R2000** + **Spline** (defaults)
4. In SolidWorks: **File → Open** → select the `.dxf` file
5. SolidWorks imports the splines as editable sketch entities
6. Use the sketch for revolve, extrude, or loft operations to build the 3D electrode

**Tip:** Use "Merge into one layer" if you want to select all geometry at once in SolidWorks.

---

## Using with FEMM 4.2

### Method 1: Lua Script (recommended)

1. In the GUI, configure your profile and assembly parameters (gap, plate length)
2. Click **Export FEMM Lua…**
3. Fill in the simulation parameters (voltages, permittivity, etc.)
4. Save the `.lua` file
5. Open **FEMM 4.2**
6. Go to **File → Open Lua Script** (or press the Lua console button)
7. Load and run the script — the geometry, materials, and boundary conditions are created automatically
8. If auto-solve was checked, the results are ready immediately

### Method 2: DXF Import (geometry only)

1. Click **Export DXF…**
2. Settings: **R12** + **Polyline** (auto-set when R12 is chosen)
3. Save the `.dxf` file
4. In FEMM: **File → Import DXF**
5. You will need to manually assign materials and boundary conditions

The Lua script method is strongly recommended — it sets up the complete simulation in one step.

---

## CLI Mode

For headless or scripted use:

```bash
cd src
python main.py --cli                      # Rogowski (default)
python main.py --cli --profile chang      # Chang profile
python main.py --cli --profile ernst      # Ernst profile
```

The CLI prompts for each parameter interactively and exports both a PNG plot and a DXF file with timestamped filenames.

---

## Building the Executable

To build a standalone `.exe` (no Python installation needed):

```bash
build.bat
```

This creates `dist\ProfileGenerator.exe` — a single-file executable that includes all dependencies. The build script:

1. Creates/activates the `.venv` virtual environment
2. Installs dependencies from `requirements.txt`
3. Runs PyInstaller with all hidden imports and the `assets/` folder bundled

---

## Profile Equations Reference

### Rogowski

```
X = (s/π) · (u + 1 + eᵘ · cos(v))
Y = (s/π) · (v + eᵘ · sin(v))
v = π/2 (constant)
```

- `s` = electrode gap (scales the entire profile)
- `u` = parameter variable
- As u → −∞, Y → s/2 (the natural gap between two mirrored Rogowski curves is exactly `s`)

### Chang

```
X = u + cos(v) · sinh(u)
Y = v + k · sin(v) · cosh(u)
v = π/2 (constant)
```

- `k` > 0 controls profile compactness (default: 0.85)
- `u` ∈ [0, u_max] where u_max defines the electrode width

### Ernst

```
X = u + k₀ · cos(v) · sinh(u) + k₁ · cos(2v) · sinh(2u)
Y = v + k₀ · sin(v) · cosh(u) + k₁ · sin(2v) · cosh(2u)
v = π/2 (constant)
k₁ = k₀² / 8 (auto-calculated)
```

- `k₀` = primary shape constant
- `k₁` = secondary constant, derived from k₀
- `u` ∈ [0, u_max]

**Edge-effect relationships:**

| Formula | Description |
|---------|-------------|
| k₀ = 1.72 · e⁻ʰ | k₀ as function of profile width h |
| h = 3.5 · s | Profile width for edge-free design (valid for s < 3) |
| k₀ = 1.72 · e⁻³·⁵ˢ | Combined: optimal k₀ from electrode distance |

Edge effects become considerable at s ≈ 3.
