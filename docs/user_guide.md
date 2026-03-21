# Electrode Profile Generator — User Guide

**Version 1.6.0** · Pau Bas Calopa · 2026

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
7. [Live Simulation](#live-simulation)
8. [Profile Optimizer](#profile-optimizer)
9. [CLI Mode](#cli-mode)
10. [Building the Executable](#building-the-executable)
11. [Profile Equations Reference](#profile-equations-reference)

---

## Overview

The Electrode Profile Generator is a desktop tool for designing parallel plate electrodes with mathematically defined edge profiles. It supports four profile types (Rogowski, Chang, Ernst, Bruce), provides a live interactive preview with electrode closing arcs, and exports geometry for CAD (SolidWorks, AutoCAD) and FEM simulation (FEMM 4.2).

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
| **Rogowski** | Classic conformal-mapping profile, scaled by electrode gap `s` |
| **Chang**    | Parametric profile with compactness factor `k` |
| **Ernst**    | Two-term profile with auto-calculated k₁ = k₀²/8 |
| **Bruce**    | Piecewise profile: sinusoidal transition + circular termination |

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
| **s** (gap) | Distance between the two parallel electrodes |
| **d** (plate length) | Length of the flat plate portion of each electrode |
| **Build electrode assembly** | When checked, displays the full mirrored assembly with closing arcs |

The assembly consists of profiles, flat plates, and closing arcs. In planar mode, a tangent arc connects the right and left profile tips. In axisymmetric mode, the arc runs from the profile tip to the axis (r = 0), arriving perpendicular to the axis.

### Ernst Auto k₀

When using the Ernst profile, the **Auto k₀ (no edge effect)** button calculates the optimal k₀ value that eliminates edge effects for the current gap `s`:

```
k₀ = 1.72 · e^(-3.5·s)
```

This relationship is valid for s < 3. At s ≈ 3, edge effects become significant and a warning is shown.

---

## Exporting

All exports use a default filename of `ProfileType_YYYYMMDD_HHMMSS.ext`.

### CSV Export

Exports all visible curves as a table with columns: `curve`, `x`, `y`.

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

- **R12** is required for FEMM 4.2 DXF import. When R12 is selected, the curve type is automatically set to Polyline.
- **Spline** entities are recommended for SolidWorks — they import as editable sketch splines.
- Structural curves (plates, caps) are always exported as polylines.

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
| **Auto-solve** | off | When checked, the script runs the solver automatically |

---

## Using with SolidWorks

1. Configure your profile and electrode assembly
2. Click **Export DXF…** → settings: **R2000** + **Spline**
3. In SolidWorks: **File → Open** → select the `.dxf` file
4. Use the sketch for revolve, extrude, or loft operations

---

## Using with FEMM 4.2

### Method 1: Lua Script (recommended)

1. Configure your profile and assembly parameters
2. Click **Export FEMM Lua…** → fill in simulation parameters → save
3. In FEMM: **File → Open Lua Script** → load and run

### Method 2: DXF Import (geometry only)

1. Click **Export DXF…** → settings: **R12** + **Polyline** → save
2. In FEMM: **File → Import DXF**
3. Manually assign materials and boundary conditions

### Method 3: Live Simulation

Use **Run FEMM Simulation…** to drive FEMM directly from the GUI. See [Live Simulation](#live-simulation).

---

## Live Simulation

Click **Run FEMM Simulation…** to open the FEMM simulation wizard. This requires `pyfemm` and FEMM 4.2 installed.

The simulation:

1. Opens FEMM (hidden)
2. Builds the complete model (geometry, materials, boundaries)
3. Meshes and solves
4. Selects a measuring contour along the top electrode (with an offset into the gap)
5. Extracts the electric field along the contour
6. Displays an E-field plot

In axisymmetric mode, the measuring contour starts from the axis (r = 0) and follows the top electrode profile outward.

---

## Profile Optimizer

Click **Optimize…** to open the optimization wizard. It performs a golden-section search over a selected profile parameter to minimize field enhancement (ΔE%):

| Setting | Description |
|---------|-------------|
| **Parameter** | Which profile parameter to vary |
| **Range** | Min/max search bounds |
| **Tolerance** | Convergence threshold |
| **Max iterations** | Limit on evaluations |

Each iteration runs a full FEMM simulation. Progress is displayed in real time. Click **Cancel** to stop the optimization at any time. When complete, click **Apply to Profile** to use the optimal value.

---
## CLI Mode

For headless or scripted use:

```bash
cd src
python main.py --cli                      # Rogowski (default)
python main.py --cli --profile chang      # Chang profile
python main.py --cli --profile ernst      # Ernst profile
python main.py --cli --profile bruce      # Bruce profile
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

The Rogowski profile is derived from conformal mapping and scaled by electrode gap `s`:

```
X = (s/π) · (u + 1 + eᵘ · cos(v))
Y = (s/π) · (v + eᵘ · sin(v))
v = π/2 (constant)
```

- `s` = electrode gap (scales the entire profile)
- `u` = parameter variable (u ∈ [u_min, 0])
- As u → −∞, Y → s/2 (the natural gap between two mirrored Rogowski curves is exactly `s`)

### Chang

The Chang profile uses a parametric conformal mapping with a compactness factor:

```
X = u + cos(v) · sinh(u)
Y = v + k · sin(v) · cosh(u)
v = π/2 (constant)
```

- `k` > 0 controls profile compactness (default: 0.85)
- `u` ∈ [0, u_max] where u_max defines the electrode width

### Ernst

The Ernst profile adds a second-order correction term to the Chang mapping:

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

### Bruce

The Bruce profile is a piecewise construction with a sinusoidal transition zone followed by a circular termination:

```
Region 1 — Sinusoidal (α₀ ≤ α ≤ π/2):
  Xbr = (s/2) · sin(α)
  Ybr = (s/2) · (π/2 − α + sin(α)·cos(α)) / sin²(α₀)

Region 2 — Circular (0 ≤ α ≤ α₀):
  Xbr = R₀ − R₀·cos(α) + X(α₀)
  Ybr = R₀·sin(α)
  R₀  = (s/2) / sin²(α₀)
```

- `α₀` = characteristic angle that defines the transition between sinusoidal and circular regions
- `s` = electrode gap
- The profile endpoints are rotated into the standard electrode coordinate frame
