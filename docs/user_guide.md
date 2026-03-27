# Electrode Profile Generator - User Guide

**Version 1.7.0** - Pau Bas Calopa - 2026

---

## Table of Contents

1.  [Introduction](#introduction)
    - [What This Tool Does](#what-this-tool-does)
    - [Who It Is For](#who-it-is-for)
2.  [Background - Why Electrode Shaping Matters](#background---why-electrode-shaping-matters)
    - [The Parallel Plate Ideal](#the-parallel-plate-ideal)
    - [Edge Effects and Field Enhancement](#edge-effects-and-field-enhancement)
    - [The Delta-E Percent Metric](#the-delta-e-percent-metric)
    - [Conformal Mapping - The Mathematical Foundation](#conformal-mapping---the-mathematical-foundation)
3.  [The Four Profile Types](#the-four-profile-types)
    - [Rogowski](#rogowski)
    - [Chang](#chang)
    - [Ernst](#ernst)
    - [Bruce](#bruce)
    - [Profile Comparison Guide](#profile-comparison-guide)
4.  [Installation](#installation)
5.  [GUI Interface](#gui-interface)
    - [Profile Selection and Parameters](#profile-selection-and-parameters)
    - [Electrode Assembly](#electrode-assembly)
    - [Planar vs Axisymmetric Geometry](#planar-vs-axisymmetric-geometry)
    - [Ernst Auto k0](#ernst-auto-k0)
6.  [Exporting](#exporting)
    - [CSV Export](#csv-export)
    - [PNG Export](#png-export)
    - [DXF Export](#dxf-export)
    - [FEMM Lua Export](#femm-lua-export)
7.  [Using with SolidWorks](#using-with-solidworks)
8.  [Using with FEMM 4.2](#using-with-femm-42)
9.  [Live Simulation](#live-simulation)
    - [What Happens Under the Hood](#what-happens-under-the-hood)
    - [The Measuring Contour](#the-measuring-contour)
    - [Interpreting the E-Field Plot](#interpreting-the-e-field-plot)
10. [Profile Optimizer](#profile-optimizer)
    - [Concepts - What the Optimizer Does](#concepts---what-the-optimizer-does)
    - [Optimizable Parameters](#optimizable-parameters)
    - [Golden-Section Search](#golden-section-search)
    - [Differential Evolution](#differential-evolution)
    - [NSGA-II - Multi-Objective Pareto Optimisation](#nsga-ii---multi-objective-pareto-optimisation)
    - [Objectives in Detail](#objectives-in-detail)
    - [Choosing the Right Algorithm](#choosing-the-right-algorithm)
    - [Controls and Workflow](#controls-and-workflow)
11. [Parameter Sweep](#parameter-sweep)
12. [CLI Mode](#cli-mode)
13. [Building the Executable](#building-the-executable)
14. [Profile Equations Reference](#profile-equations-reference)
    - [Rogowski Equations](#rogowski-equations)
    - [Chang Equations](#chang-equations)
    - [Ernst Equations](#ernst-equations)
    - [Bruce Equations](#bruce-equations)
15. [Glossary](#glossary)

---

## Introduction

### What This Tool Does

The Electrode Profile Generator is a desktop application for designing the edge profiles of parallel plate electrodes. It generates mathematically precise curves based on conformal mapping theory, visualises the complete electrode assembly in real time, and provides direct export to CAD (SolidWorks, AutoCAD via DXF) and finite-element simulation (FEMM 4.2).

Beyond geometry generation the tool includes a built-in electrostatic simulator (via FEMM), a profile optimiser with three algorithms (golden-section, Differential Evolution, NSGA-II), and a parameter sweep facility, allowing a complete design-simulate-optimise workflow without leaving the application.

### Who It Is For

- **High-voltage engineers** designing Rogowski, Chang, Ernst or Bruce electrodes for breakdown test gaps, Kerr cells, or electro-optic modulators.
- **Researchers** studying field uniformity between parallel plates.
- **Students** learning about conformal mapping, electrode design and electrostatic field simulation.

---

## Background - Why Electrode Shaping Matters

### The Parallel Plate Ideal

Two infinite, perfectly flat parallel plates separated by a gap *s* and held at voltages *V+* and *V-* produce a perfectly **uniform** electric field in the gap:

```
E_uniform = |V+ - V-| / s
```

This is the simplest and most desirable field configuration for many experiments: every point between the plates experiences exactly the same field strength. It is the starting assumption behind Paschen's law, Kerr effect measurements, and many standardised breakdown test procedures.

### Edge Effects and Field Enhancement

Real electrodes are not infinite. Where the flat plate ends, the electric field lines crowd together and the local field becomes **stronger than the uniform value**. This is called *field enhancement* (or *edge effect*) and it causes two problems:

1. **Premature breakdown** - the gap sparks at the electrode edge long before the uniform-field region reaches the intended breakdown voltage. This invalidates any measurement that assumes a known, uniform applied field.
2. **Measurement errors** - if the experiment assumes a uniform field (e.g. a Kerr-effect measurement) the actual field is unknown because the enhancement depends on the exact edge geometry.

The solution is to **shape the electrode edges** with a mathematically defined profile that forces the field to remain at or below the uniform value everywhere. The field-enhancement factor (FEF) is defined as:

```
FEF = E_max / E_uniform
```

A perfect electrode has FEF = 1.0 (no enhancement). In practice, values below 1.01 (dE < 1 %) are considered excellent.

### The Delta-E Percent Metric

Throughout this application the primary quality metric is **dE %**, defined as:

```
dE % = (E_99 / E_uniform - 1) x 100
```

where *E_99* is the 99th-percentile field strength measured along a contour that follows the electrode surface. The 99th percentile is used (rather than the absolute maximum) to provide a robust statistic that is less sensitive to mesh singularities at sharp geometric transitions.

**Interpretation:**

| dE %   | Quality              | Typical use case                    |
|--------|----------------------|-------------------------------------|
| < 0.5  | Excellent            | Precision Kerr cells, calibration   |
| 0.5-2  | Very good            | Standard breakdown test gaps        |
| 2-5    | Acceptable           | Approximate uniform-field regions   |
| > 5    | Poor - redesign      | Significant edge enhancement        |

The reference field *E_uniform* is computed analytically from the applied voltages and the electrode gap:

```
E_uniform = |V_top - V_bottom| / s
```

This analytical reference is independent of mesh resolution, contour placement, or simulation parameters, making dE % a reliable and reproducible quality metric across different simulation runs.

### Conformal Mapping - The Mathematical Foundation

All four profile types are derived (directly or indirectly) from **conformal mappings** - complex-variable transformations that preserve angles and, crucially, Laplace's equation.

The idea is:

1. Start with the *w-plane* where the solution is known analytically (typically a semi-infinite parallel plate capacitor with a perfectly uniform field between the plates).
2. Apply an analytic function *z = f(w)* that maps the straight-edged boundary into a curved profile in the *z-plane* (physical space).
3. Because the mapping is conformal it preserves the harmonic structure of the potential - the resulting electrode shape automatically produces a field that matches the uniform-field solution inside the gap.

Different choices of *f(w)* produce different profile shapes, each with its own trade-offs between field quality, compactness, and manufacturability.

The key mathematical property at work is that **Laplace's equation is invariant under conformal transformation**. If phi(w) satisfies nabla-squared phi = 0 in the w-plane, then phi(z) = phi(f-inverse(z)) still satisfies nabla-squared phi = 0 in the z-plane. The boundary conditions (fixed voltages on the electrode surfaces) are preserved as well.

---

## The Four Profile Types

### Rogowski

The **Rogowski profile** (H. Rogowski, 1923) is the oldest and most well-known electrode shape for uniform-field generation. It comes directly from the Schwarz-Christoffel mapping of a semi-infinite parallel plate capacitor:

```
z = (s/pi) * (w + 1 + e^w)        w = u + j*pi/2
```

**Key properties:**

- The gap between two mirrored Rogowski electrodes is **exactly** *s* (the gap parameter also sets the profile scale).
- The profile extends to infinity in the radial direction - in practice it must be truncated. The parameter *u_end* controls where the truncation occurs.
- Very low field enhancement (< 0.1 % dE) when sufficient radial extent is provided.
- **Trade-off:** large physical size for a given gap. The electrode diameter grows rapidly with the required field quality.

**When to use:** classic reference design; when physical space is not a constraint and the highest field uniformity is required.

### Chang

The **Chang profile** (T.Y. Chang, 1973) extends the conformal mapping with a **compactness factor** *k*:

```
X = u + cos(v) * sinh(u)
Y = v + k * sin(v) * cosh(u)        v = pi/2
```

When *k* = 1 the Chang profile is equivalent to the Rogowski shape. Reducing *k* below 1 compresses the profile vertically, producing a **more compact electrode** at the cost of slightly higher field enhancement.

**Key properties:**

- The parameter *k* gives continuous control over the compactness-uniformity trade-off.
- *u_end* controls the radial extent (electrode width).
- More compact than Rogowski for the same gap, at the expense of a few percent higher dE.

**When to use:** when the electrode must fit inside a constrained radial envelope (e.g. a cylindrical vacuum chamber) and a small amount of field enhancement is acceptable.

### Ernst

The **Ernst profile** (K.A. Ernst, 1968) adds a second-order correction term to the Chang mapping:

```
X = u + k0*cos(v)*sinh(u) + k1*cos(2v)*sinh(2u)
Y = v + k0*sin(v)*cosh(u) + k1*sin(2v)*cosh(2u)
v = pi/2,   k1 = k0^2/8
```

The additional harmonic term cancels out the leading-order field disturbance at the plate-profile junction, achieving **near-zero edge effect** while remaining more compact than Rogowski.

**Key properties:**

- Two shape constants: *k0* (primary) and *k1 = k0^2/8* (auto-calculated).
- An analytic relationship gives the optimal *k0* for a given gap: `k0 = 1.72 * e^(-3.5*s)` (valid for *s* < 3).
- The **Auto k0** button in the GUI computes this value for the current gap.
- Often achieves dE < 0.5 % in a much smaller footprint than Rogowski.

**When to use:** the recommended default for most applications. Provides the best balance of field uniformity, compactness, and manufacturability.

### Bruce

The **Bruce profile** (E. Bruce, 1947) uses a **piecewise construction** rather than a single conformal mapping:

1. **Sinusoidal transition zone** - smoothly connects the flat plate to the rounding.
2. **Circular termination** - a quarter-circle cap of radius *R_e*.

The two regions are joined with matched position, slope, and curvature so the transition is C1-continuous. The single parameter **alpha_0** (characteristic angle) controls the shape.

**Key properties:**

- Conceptually simple and easy to manufacture (arcs + sine curves).
- Fewer degrees of freedom (just *alpha_0* and the gap *s*).
- Typically produces higher dE than conformal-mapping profiles of similar size, because the construction is approximate rather than derived from an exact conformal map.

**When to use:** when manufacturing simplicity is paramount (the profile can be produced on a lathe using standard tooling) and moderate field enhancement is acceptable.

### Profile Comparison Guide

| Property              | Rogowski     | Chang         | Ernst         | Bruce         |
|-----------------------|:------------:|:-------------:|:-------------:|:-------------:|
| **dE % (typical)**    | < 0.1 %     | 0.5 - 3 %    | < 0.5 %      | 1 - 5 %      |
| **Compactness**       | Poor         | Good          | Very good     | Good          |
| **Adjustable params** | u range      | k, u range    | k0, u range   | alpha_0       |
| **Manufacturability** | Moderate     | Moderate      | Moderate      | Excellent     |
| **Theory**            | Exact S-C    | 1-term conf.  | 2-term conf.  | Piecewise     |
| **Best for**          | Reference    | Size-limited  | General use   | Simple fab    |

> **Recommendation for first-time users:** start with **Ernst** using the **Auto k0** button. If the electrode is too large, reduce *u_end* and re-optimise with the built-in optimiser.

---

## Installation

### Requirements

- Python 3.9 or later
- Dependencies: `numpy`, `matplotlib`, `ezdxf`
- Optional (for simulation and optimisation): `pyfemm` + FEMM 4.2

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

- **Left panel** - profile selection, parameters, electrode assembly settings, and export/simulate/optimise buttons.
- **Right panel** - live matplotlib plot showing the current profile or full electrode assembly.

### Profile Selection and Parameters

Use the **Profile Type** dropdown at the top to switch between Rogowski, Chang, Ernst and Bruce. When you change the profile the parameter controls update automatically.

Each profile exposes its own set of parameters:

- **Sliders** - drag for quick adjustment.
- **Entry boxes** - type exact values and press Enter. Both `.` and `,` are accepted as decimal separators (European format support).
- **Extended range** - if you type a value beyond the slider limits the slider auto-extends to accommodate it.

The **Points** slider (below the assembly controls) sets the number of discrete points used to represent the profile curve. Higher values produce smoother curves at the cost of slightly larger export files and longer simulation meshing. The default of 100 is suitable for most workflows.

### Electrode Assembly

The **Electrode Assembly** section controls the physical construction of the complete electrode pair:

| Parameter | Description |
|-----------|-------------|
| **s** (gap) | Distance between the two parallel electrode plates (in profile units) |
| **d** (plate length) | Length of the flat plate portion extending inward from the profile |
| **Points** | Number of curve discretisation points (shared across profile and plate) |
| **Build electrode assembly** | When checked, displays the full mirrored assembly with closing arcs |

The assembly consists of:

1. **Profile curves** - the mathematically defined edge shape (top-right and top-left, mirrored for the bottom electrode).
2. **Flat plates** - horizontal segments connecting the left and right profile tips through the centre.
3. **Closing arcs** - tangent arcs that smoothly close the electrode boundary:
   - *Planar mode* - a tangent arc connects the rightmost profile tip back around to the opposite side.
   - *Axisymmetric mode* - the arc runs from the profile tip inward to the symmetry axis (r = 0), arriving perpendicular to the axis.

### Planar vs Axisymmetric Geometry

| Aspect | Planar | Axisymmetric |
|--------|--------|--------------|
| **Geometry** | 2D cross-section, extruded in depth | 2D cross-section revolved around r = 0 |
| **Physical equivalent** | Strip electrodes (infinite or finite depth) | Circular disk electrodes |
| **FEMM depth parameter** | Required (in mm) | Ignored |
| **Closing arc** | Tangent arc at the outer edge | Arc to the symmetry axis |
| **Typical use** | Rectangular electrode assemblies | Cylindrical test gaps, Kerr cells |

Most high-voltage test gaps use **axisymmetric** electrodes (circular discs machined on a lathe). The axisymmetric setting is the default in the simulation and optimisation wizards.

### Ernst Auto k0

When using the Ernst profile, the **Auto k0 (no edge effect)** button calculates the optimal *k0* value that eliminates edge effects for the current gap *s*:

```
k0 = 1.72 * e^(-3.5*s)
```

This relationship comes from matching the second-order term in the conformal mapping to cancel the field disturbance at the plate-profile junction. It is valid for *s* < 3. At *s* around 3 the required profile width becomes impractically large and a warning is shown.

---

## Exporting

All exports use a default filename of `ProfileType_YYYYMMDD_HHMMSS.ext`.

### CSV Export

Exports all visible curves as a table with columns: `curve`, `x`, `y`. Useful for post-processing in MATLAB, Python, or spreadsheets.

### PNG Export

Saves the current plot as a 150 DPI PNG image.

### DXF Export

Click **Export DXF** to open the DXF wizard:

| Option | Values | Default | Notes |
|--------|--------|---------|-------|
| **DXF version** | R12, R2000, R2004, R2007, R2010, R2013, R2018 | R2000 | R12 for FEMM; R2000+ for SolidWorks/AutoCAD |
| **Curve entity type** | Spline, Polyline | Spline | Spline = smooth CAD curves; Polyline = segmented lines |
| **Merge into one layer** | checkbox | off | When on, all curves go to a single `PROFILE` layer |

**Notes:**

- **R12** is required for FEMM 4.2 DXF import. When R12 is selected the curve type is automatically set to Polyline (R12 does not support splines).
- **Spline** entities are recommended for SolidWorks: they import as editable sketch splines.
- Structural curves (plates, caps) are always exported as polylines.

### FEMM Lua Export

Click **Export FEMM Lua** to open the FEMM simulation wizard:

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Problem type** | axi | `planar` or `axi` (axisymmetric) |
| **Units** | millimeters | Must match your electrode dimensions |
| **Depth** | 1.0 | Depth for planar problems (ignored in axi) |
| **Top electrode voltage** | 1000 V | Fixed potential on the top electrode surface |
| **Bottom electrode voltage** | 0 V | Fixed potential on the bottom electrode |
| **Relative permittivity (er)** | 1.0 | Permittivity of the gap dielectric (1.0 = vacuum/air) |
| **Mesh size** | 0 (auto) | Global element size; 0 lets FEMM auto-mesh |
| **Electrode mesh size** | 0 (auto) | Element size on electrode surfaces (finer = more accurate E-field) |
| **Use symmetry** | on | Model only half the gap with a symmetry boundary at the midplane |

---

## Using with SolidWorks

1. Configure your profile and electrode assembly.
2. Click **Export DXF** with settings: **R2000** + **Spline**.
3. In SolidWorks: **File > Open** and select the `.dxf` file.
4. The sketch imports as editable splines. Use for revolve (axi) or extrude (planar) operations.

**Tip:** for axisymmetric electrodes, revolve the top-half profile sketch 360 degrees around the axis to produce the full 3D electrode.

---

## Using with FEMM 4.2

### Method 1: Lua Script (recommended)

1. Configure your profile and assembly parameters.
2. Click **Export FEMM Lua**, fill in simulation parameters, and save.
3. In FEMM: **File > Open Lua Script**, load and run.
4. The script creates the complete model: geometry, materials, boundaries, mesh, and optionally solves automatically.

### Method 2: DXF Import (geometry only)

1. Click **Export DXF** with settings: **R12** + **Polyline**, and save.
2. In FEMM: **File > Import DXF**.
3. Manually assign materials and boundary conditions.

### Method 3: Live Simulation

Use **Run FEMM Simulation** to drive FEMM directly from the GUI. See [Live Simulation](#live-simulation).

---

## Live Simulation

Click **Run FEMM Simulation** to open the simulation wizard. This requires `pyfemm` (install with `pip install pyfemm`) and FEMM 4.2 installed on the system.

### What Happens Under the Hood

1. **Model creation** - FEMM opens (hidden), a new electrostatic problem is created, and the complete electrode geometry is drawn (profile curves, flat plates, closing arcs).
2. **Materials and boundaries** - the gap dielectric is assigned (air or custom er), electrode surfaces receive fixed-voltage (Dirichlet) boundary conditions, and the outer boundary uses a zero-charge (Neumann) condition or the built-in "open" boundary.
3. **Meshing** - FEMM generates a triangular finite-element mesh. If you specified electrode mesh sizes these are applied to the electrode contours; otherwise FEMM auto-meshes.
4. **Solve** - the electrostatic Laplace equation (nabla-squared phi = 0) is solved for the potential phi everywhere in the domain, subject to the Dirichlet (fixed voltage) and Neumann (zero flux) boundary conditions.
5. **Post-processing** - a measuring contour is placed along the top electrode surface (offset slightly into the gap to avoid mesh-edge artifacts) and the electric field **E** = -grad(phi) is sampled at evenly spaced points.

### The Measuring Contour

The E-field is extracted along a contour that follows the **top electrode surface** with a small offset (typically 1 % of the gap) into the gap interior. This avoids sampling exactly on element boundaries where field values can be noisy.

- In **axisymmetric** mode the contour starts at the symmetry axis (r = 0) and follows the profile outward.
- In **planar** mode the contour follows the full profile from left to right.

The offset direction is always normal to the electrode surface pointing into the gap. Because the field is nearly uniform in the central plateau region the offset has negligible effect on the measured E-field there; at the profile edge the offset ensures the sampling point is inside the mesh domain rather than on a boundary node.

### Interpreting the E-Field Plot

After the simulation completes, a plot of **|E|** (electric field magnitude, in V/m) vs. distance along the contour is displayed.

What you should see on a well-designed electrode:

- The **flat plateau** in the centre corresponds to the uniform-field region between the flat plates. Its value should match the theoretical *E_uniform = dV / s* (converted to V/m using the configured units).
- **Small rises near the edges** indicate field enhancement: the profile is not fully suppressing edge effects. The magnitude of the rise relative to the plateau is the field enhancement.
- The **dE %** value printed on the plot tells you how much the 99th-percentile field exceeds the uniform value. Lower is better.

A good design shows a flat line across most of the contour with only a small uptick (or none) at the very tip of the profile. If you see a large spike at the edge, consider:

- Increasing *u_end* (giving the profile more radial extent).
- Using the **Auto k0** function (Ernst profile).
- Running the **Optimizer** to find better parameter values automatically.

---

## Profile Optimizer

Click **Optimize** to open the optimisation wizard. The optimiser adjusts electrode parameters automatically to minimise field enhancement (or to explore multi-objective trade-offs) by running FEMM simulations in a loop.

### Concepts - What the Optimizer Does

The optimiser is a **simulation-in-the-loop** tool. For each candidate set of parameter values it:

1. Builds the complete electrode geometry from the candidate parameters.
2. Runs a full FEMM electrostatic solve (mesh + solve + post-process).
3. Extracts the E-field along the measuring contour.
4. Computes the objective value(s) (dE %, width, height, CV(E) %).
5. Uses the result to decide which parameter values to try next.

This is computationally expensive (each evaluation takes a few seconds depending on mesh density) but it accounts for the full physics including geometry details that analytical formulas cannot capture, such as the effect of the closing arc, the plate length, and the exact profile truncation point.

**Why not just use the analytic formulas?** The analytic relationships (e.g. Ernst's `k0 = 1.72*e^(-3.5*s)`) assume idealised conditions: semi-infinite plates, no closing arc, and specific truncation. In a real electrode assembly the plate length, arc geometry, and boundary conditions all affect the field. The optimiser uses FEMM to evaluate the *actual* field for each candidate, accounting for all of these effects.

### Optimizable Parameters

You can select **any combination** of the following parameters for optimisation:

- **Profile parameters** - the shape constants specific to the current profile type (e.g. *k0* for Ernst, *k* for Chang, *alpha_0* for Bruce, *u_start*/*u_end* for Rogowski).
- **s (gap)** - the electrode spacing.
- **d (plate length)** - the flat plate extension.

The **Points** slider (curve resolution) is intentionally excluded from optimisation: it affects discretisation accuracy, not the physical electrode shape.

For each selected parameter you must set **min** and **max** bounds. These define the search space. Bounds that are too wide waste evaluations; bounds that are too narrow may exclude the optimum. A quick **Sweep** run (see below) can help identify reasonable bounds.

### Golden-Section Search

A fast **1-D** line search based on the golden ratio. At each step the search interval is reduced by a factor of phi = 1.618, requiring only one new FEMM evaluation per step (the other interior point is reused from the previous iteration).

**Parameters:**

| Setting | Description | Typical value |
|---------|-------------|---------------|
| **Tolerance** | Stop when the parameter range is narrower than this | 0.001 |
| **Max iterations** | Upper limit on evaluations per parameter | 20 |

**Parameter details:**

- **Tolerance** controls how precisely the optimum is located. A tolerance of 0.001 means the algorithm stops when it has narrowed the search range to within 0.001 of the optimum. Smaller values give a more precise result but require more evaluations. For most electrode parameters (k0, u_end, alpha_0) a tolerance of 0.001 is sufficient. For the gap *s* or plate length *d* you may want a larger tolerance (e.g. 0.01) since those parameters have dimensions in millimetres.

- **Max iterations** is a safety limit. Golden-section converges geometrically: after *n* iterations the range is reduced by a factor of phi^n. With a range of [0, 3] and tolerance 0.001, convergence takes about 17 iterations, so 20 is a safe default. Increasing this beyond 30 rarely helps — if the algorithm hasn't converged by then, the landscape is likely multi-modal and you should switch to Differential Evolution.

When **multiple parameters** are selected they are optimised **sequentially** - one at a time, in the order listed. The result of each single-parameter optimisation is carried forward as the starting point for the next.

**Strengths:** very fast (10-20 evaluations per parameter), guaranteed convergence for unimodal (single-minimum) landscapes.

**Limitations:** cannot capture interactions between parameters; may miss the global optimum if the landscape has multiple local minima.

### Differential Evolution

A **population-based global optimiser** that evolves a set of candidate solutions over many generations using the DE/rand/1/bin strategy. All selected parameters are optimised **simultaneously**, so parameter interactions are captured naturally.

**Parameters:**

| Setting | Description | Typical value |
|---------|-------------|---------------|
| **Population size** | Number of candidate solutions per generation | 16-30 |
| **Generations** | How many evolution cycles to run | 20-50 |
| **F (Mutation)** | Scale factor applied to the donor vector | 0.5-1.0 |
| **CR (Crossover)** | Probability of gene exchange between parent and donor | 0.5-0.9 |

**Parameter details:**

- **Population size** determines how many candidate solutions are evaluated each generation. Larger populations explore the search space more thoroughly but require proportionally more FEMM evaluations per generation. A rule of thumb: use at least 5-10 times the number of optimised parameters. For example, optimising 3 parameters (k0, u_end, s) should use a population of at least 15-30. Very small populations (< 10) risk premature convergence to a local minimum.

- **Generations** controls how many rounds of evolution are performed. Each generation evaluates up to *population size* new candidates. Total FEMM evaluations = population x generations (worst case). Start with 20-30 generations. If the progress log shows the best dE % is still improving in the final generations, increase this number. If it converged early, you can reduce it next time.

- **F (Mutation factor)** scales the perturbation applied to candidate solutions. It controls how "bold" the mutations are:
  - **F = 0.5**: conservative mutations, fine-grained search, slower exploration.
  - **F = 0.8** (default): good balance between exploration and exploitation.
  - **F = 1.0**: aggressive mutations, larger jumps, better for very rugged landscapes.
  - **F > 1.0**: rarely useful; mutations overshoot and the algorithm becomes unstable.

  Technically, for each candidate *x*, three random others *a*, *b*, *c* are chosen and a donor vector is computed as: `donor = a + F * (b - c)`. The factor F scales how far the donor strays from the base vector *a*.

- **CR (Crossover probability)** controls how many parameters are inherited from the mutated donor vs. kept from the current candidate:
  - **CR = 0.5**: each parameter has a 50/50 chance of coming from the donor or staying as-is. Conservative: preserves more of the current solution.
  - **CR = 0.7** (default): moderate mixing.
  - **CR = 0.9**: aggressive mixing; almost all parameters come from the donor. Better for highly coupled parameters where changing one without the others makes things worse.
  - **CR = 1.0**: the trial vector is entirely from the donor (except one guaranteed random gene from the parent).

  **Guideline:** if the parameters are relatively independent (e.g. k0 and plate_length), a lower CR (0.5-0.7) works well. If they are tightly coupled (e.g. k0 and u_end in Ernst), use a higher CR (0.7-0.9).

**How it works (simplified):**

1. A random initial population of candidate solutions is spread across the parameter bounds. Each candidate is a vector of parameter values (e.g. [k0, u_end, s, d]).
2. For each candidate *x*, three random others *a*, *b*, *c* are picked. A *donor* vector is created: `donor = a + F * (b - c)`.
3. The donor is mixed with *x* via binomial crossover (each gene has probability CR of coming from the donor) to produce a *trial* vector.
4. The trial is evaluated via a full FEMM simulation. If its dE % is better than the current candidate, it replaces it; otherwise the current candidate survives.
5. Repeat for the specified number of generations.

**Strengths:** global search that handles rugged landscapes and multi-parameter interactions well.

**Limitations:** requires many more evaluations (population x generations); single-objective only (minimises dE %).

**Tuning tips:**

- If the algorithm converges too early (best dE % stops improving after a few generations), **increase F** or **increase population size** to promote exploration.
- If the algorithm wanders without converging, **decrease F** or **increase generations** to give it more time to refine.
- Total budget: a typical run with population=20, generations=30 uses 600 FEMM evaluations. At ~2 seconds each that is ~20 minutes. Plan accordingly.

### NSGA-II - Multi-Objective Pareto Optimisation

The **Non-dominated Sorting Genetic Algorithm II** (NSGA-II) extends the evolutionary approach to **multiple objectives simultaneously**. Instead of a single "best" result it returns a **Pareto front** - a set of solutions where no solution is better than another on *all* objectives at once.

This is the **default algorithm** in the optimiser.

**Parameters:**

| Setting | Description | Typical value |
|---------|-------------|---------------|
| **Population size** | Number of candidates per generation | 20-40 |
| **Generations** | Number of evolution cycles | 20-50 |
| **F (Mutation)** | Scale factor for donor vectors | 0.5-1.0 |
| **CR (Crossover)** | Gene exchange probability | 0.5-0.9 |

**Parameter details:**

NSGA-II uses the same mutation (F) and crossover (CR) operators as Differential Evolution (see above for detailed explanations of each). The key differences are in how population size and generations affect the results:

- **Population size** has a dual role in NSGA-II. Besides controlling exploration thoroughness (as in DE), it also determines the **maximum number of Pareto front solutions** that can be returned. The algorithm can return at most *population size* non-dominated solutions. If you want a dense, well-resolved Pareto front with many trade-off options, use a larger population (30-50). If you just want a rough idea of the trade-off, 15-20 is enough.

- **Generations** determines how many rounds of evolution are run to refine the Pareto front. In the early generations the front is rough and incomplete. As generations increase, solutions spread out along the front and move closer to the true optimum. More objectives generally require more generations to converge. Start with 20-30 and look at the progress log: if the front is still changing significantly in the last few generations, increase this number.

- **F (Mutation)** and **CR (Crossover)** work exactly as in DE. The same tuning guidelines apply:
  - F = 0.8, CR = 0.7 is a good starting point.
  - Increase F for more exploration (wider spread along the Pareto front).
  - Increase CR if parameters are tightly coupled.

- **Objectives** (at least 2 must be selected): these are the quantities that NSGA-II tries to minimise simultaneously. Each additional objective makes the problem harder and typically requires a larger population and more generations to produce a well-distributed front. For 2 objectives, population=20, generations=30 is usually sufficient. For 3-4 objectives, consider population=40, generations=50.

**How it works (simplified):**

1. A random initial population is created and evaluated on all selected objectives (e.g. dE % and Width simultaneously).
2. The population is sorted into **non-dominated fronts** (Pareto layers):
   - *Front 0* contains solutions that are not dominated by any other solution - the current best trade-offs.
   - *Front 1* contains solutions dominated only by front 0.
   - And so on.
3. Within each front, **crowding distance** is computed to favour solutions that are spread out along the front (preserving diversity so the user gets a range of trade-offs, not all clustered together).
4. New candidates are generated using DE-style mutation and crossover (same operators as Differential Evolution).
5. Parents + offspring are merged, re-sorted, and the best *N* survive to the next generation (elitist selection).
6. After all generations, front 0 is returned as the **Pareto front**.

You must select **at least two** objectives (see below). After the run a **Pareto Front table** appears in the wizard. Each row is a different trade-off solution. Select a row and click **Apply to Profile** to use those parameter values.

**Understanding the Pareto front:** every solution on the front is optimal in the sense that you cannot improve one objective without making another worse. For example, one solution might have dE = 0.5 % but Width = 50 mm, while another has dE = 2 % but Width = 30 mm. Neither dominates the other: the choice depends on your design priorities.

**Tuning tips:**

- Start with population=20, generations=30, F=0.8, CR=0.7 for a first exploration.
- If the Pareto front has gaps (missing regions of the trade-off curve), increase population size so there are more solutions to fill in the gaps.
- If solutions on the front are clustered together rather than spread out, the crowding distance mechanism may need more generations to separate them. Increase generations or try slightly higher F to promote diversity.
- If all solutions on the front have similar objective values, your parameter bounds may be too narrow. Widen them and re-run.
- For a quick exploratory run (5-10 min), try population=12, generations=15. For a thorough search (30-60 min), try population=30, generations=50.

### Objectives in Detail

| Objective | Formula | What it measures | Lower means |
|-----------|---------|------------------|-------------|
| **dE %** | (E_99 / E_uniform - 1) x 100 | 99th-percentile field enhancement at the electrode edge | More uniform field; less risk of premature breakdown |
| **Width** | max(x) - min(x) of the profile curve | Radial extent of the profile | More compact electrode; easier to fit in a vacuum chamber |
| **CV(E) %** | 100 x sigma(E) / mu(E) along the contour | Coefficient of variation of the E-field | Flatter, more homogeneous field distribution |
| **Height** | max(y) - min(y) of the profile curve | Vertical extent of the profile | Thinner electrode; less material, lighter assembly |

**Common objective pairs and when to use them:**

- **dE % + Width** - *"I want the most compact electrode that still has acceptable field uniformity."* This is the most frequently used combination. The Pareto front shows the fundamental compactness-uniformity trade-off for the selected profile type.
- **dE % + Height** - useful when electrode thickness is constrained (e.g. stacked multi-gap assemblies, compact Kerr cells).
- **dE % + CV(E) %** - when not just the peak field but the overall field homogeneity matters (e.g. Kerr effect measurements where the optical path integrates through the entire field between the plates).
- **All four** - exploratory runs to understand the full design space. The 4D Pareto front will have more solutions but gives the most complete picture of the trade-offs.

### Choosing the Right Algorithm

| Situation | Recommended algorithm | Why |
|-----------|----------------------|-----|
| One parameter, quick check | Golden-section | Fast, around 15 evals total |
| 2+ params, single objective (dE %) | Differential Evolution | Captures parameter interactions |
| 2+ params, 2+ objectives | **NSGA-II** (default) | Returns full trade-off front |
| Unknown landscape, first exploration | NSGA-II with dE % + Width | Reveals compactness-uniformity trade-off |
| Fine-tuning a known good design | Golden-section per parameter | Precise, minimal evaluations |

### Controls and Workflow

A typical optimisation workflow:

1. **Select parameters** - tick the checkboxes next to the parameters you want to optimise and set appropriate min/max bounds for each.
2. **Choose algorithm** - the dropdown defaults to NSGA-II.
3. **Configure algorithm settings** - population size, generations, F, CR (or tolerance and max iterations for golden-section).
4. **Set simulation options** - problem type (axi recommended), voltages, mesh sizes. Finer electrode mesh gives more accurate results but slower evaluations.
5. Click **Start** - the button changes to **Stop** while running. The progress log shows each evaluation in real time.
6. **Stop early** - click **Stop** at any time. The best result (or best Pareto front) found so far is kept and can still be applied.
7. **Apply** - for golden-section / DE, click **Apply to Profile** to send the optimal values back to the main window. For NSGA-II, select a row in the Pareto table first, then click Apply.

Each evaluation runs a full FEMM simulation. If a candidate produces an invalid geometry (for example the domain crosses r < 0 in axisymmetric mode, or curves self-intersect) it is automatically assigned an infinite cost and skipped. The optimiser continues with the remaining candidates.

The optimiser wizard is **non-modal**: it stays open while you interact with the main window. This means you can apply a result, run a FEMM simulation from the main window to visualise the field, and then return to the wizard to try a different Pareto solution without restarting the optimisation.

**Exporting results:** click **Export CSV** to save the results to a CSV file. For NSGA-II this exports the entire Pareto front table (objective values + parameter values). For DE and golden-section it exports the best parameter values and dE %. The export is available as soon as the optimisation completes.

---

## Parameter Sweep

Click **Sweep** to open the parameter sweep wizard. A sweep evaluates **dE %** at evenly spaced values across a parameter range, producing a landscape view that shows how the objective varies with the parameter.

| Setting | Description |
|---------|-------------|
| **Parameter(s)** | Select one or more profile parameters, s, or d |
| **Range** | Min / max bounds for the sweep |
| **Steps** | Number of evaluation points (more = finer resolution) |

- **Single parameter** - produces a clear view of dE % vs. the swept parameter. Useful for understanding whether the landscape is smooth (golden-section will work well) or has multiple minima (use DE or NSGA-II instead).
- **Multiple parameters** - runs sequential one-at-a-time sweeps sharing the same FEMM session. Each parameter is swept independently while the others are held at their current values.

The sweep logs each evaluation in the progress window and highlights the best value found. Solver errors (invalid geometries) are skipped automatically with a log message. Click **Export CSV** to save all sweep data (parameter values and corresponding dE %) to a CSV file for external analysis or plotting.

**When to use:** before running a full optimisation, a quick sweep gives you intuition about the parameter landscape. Key questions a sweep can answer:

- Is the landscape **smooth** or **rugged** (multiple local minima)?
- Where is the approximate **optimum region**?
- Are the current **bounds reasonable**, or should they be widened/narrowed?

This information helps you choose the right algorithm and set appropriate bounds and population sizes for the full optimisation run.

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

This creates `dist\ProfileGenerator.exe`, a single-file executable that includes all dependencies. The build script:

1. Creates/activates the `.venv` virtual environment.
2. Installs dependencies from `requirements.txt`.
3. Runs PyInstaller with all hidden imports and the `assets/` folder bundled.

---

## Profile Equations Reference

### Rogowski Equations

Derived from the Schwarz-Christoffel mapping of a semi-infinite parallel plate capacitor. The profile curve is the image of the upper plate edge under the conformal map:

```
X = (s/pi) * (u + 1 + e^u * cos(v))
Y = (s/pi) * (v + e^u * sin(v))
v = pi/2 (constant)
```

| Symbol | Meaning | Range |
|--------|---------|-------|
| *s* | Electrode gap (scales the entire profile) | > 0 |
| *u* | Conformal parameter | u in [u_start, u_end] |
| *v* | Fixed at pi/2 (selects the upper plate boundary) | fixed |

As u approaches negative infinity, Y approaches s/2. The natural gap between two mirrored Rogowski curves is exactly *s*, which is why the gap parameter simultaneously defines both the spacing and the profile size.

**Physical interpretation:** the mapping takes the straight edge of the semi-infinite plate in the *w*-plane and bends it into a smooth curve in the *z*-plane. Points far from the edge (large |u|) remain essentially flat; points near the edge (u near 0) are the most curved part of the profile.

### Chang Equations

A generalisation of the Rogowski mapping with an additional degree of freedom:

```
X = u + cos(v) * sinh(u)
Y = v + k * sin(v) * cosh(u)
v = pi/2 (constant)
```

| Symbol | Meaning | Range |
|--------|---------|-------|
| *k* | Compactness factor | 0 < k <= 2 (default 0.85) |
| *u* | Conformal parameter | u in [0, u_end] |

When *k* = 1 this reduces to the Rogowski shape (without gap scaling). Decreasing *k* compresses the profile vertically, making the electrode more compact but increasing field enhancement at the edge. The compactness factor works by scaling the vertical component of the mapping: the cosh(u) term grows exponentially, so even small changes in *k* produce significant differences in the outer part of the profile.

### Ernst Equations

A two-term extension of the Chang mapping that includes a second-harmonic correction:

```
X = u + k0 * cos(v) * sinh(u) + k1 * cos(2v) * sinh(2u)
Y = v + k0 * sin(v) * cosh(u) + k1 * sin(2v) * cosh(2u)
v = pi/2 (constant)
k1 = k0^2 / 8  (auto-calculated)
```

| Symbol | Meaning | Range |
|--------|---------|-------|
| *k0* | Primary shape constant | 0.001 - 1.72 |
| *k1* | Secondary constant (= k0^2/8) | Derived |
| *u* | Conformal parameter | u in [0, u_end] |

**Optimal k0 for edge-free design:**

| Formula | Description |
|---------|-------------|
| k0 = 1.72 * e^(-h) | k0 as function of profile width *h* |
| h = 3.5 * s | Required profile width for zero edge effect |
| k0 = 1.72 * e^(-3.5*s) | Combined: optimal k0 from electrode spacing |

The second-harmonic term (k1) is what distinguishes Ernst from Chang. The cos(2v) and sin(2v) functions at v = pi/2 evaluate to -1 and 0 respectively, so the correction adds a purely radial (X-direction) perturbation that compensates for the field disturbance at the plate-profile junction. The relationship k1 = k0^2/8 is chosen specifically to cancel the first-order residual enhancement.

Edge effects become significant when *s* is around 3 (the required profile width exceeds practical manufacturing limits).

### Bruce Equations

A piecewise construction with two analytically defined regions:

**Region 1 - Sinusoidal transition (alpha_0 <= alpha <= pi/2):**

```
X_br = (s/2) * sin(alpha)
Y_br = (s/2) * (pi/2 - alpha + sin(alpha)*cos(alpha)) / sin^2(alpha_0)
```

**Region 2 - Circular termination (0 <= alpha <= alpha_0):**

```
X_br = R0 - R0*cos(alpha) + X(alpha_0)
Y_br = R0 * sin(alpha)
R0  = (s/2) / sin^2(alpha_0)
```

| Symbol | Meaning | Range |
|--------|---------|-------|
| *alpha_0* | Characteristic angle | 1 deg - 45 deg (default 10 deg) |
| *s* | Electrode gap | > 0 |
| *R0* | Circular termination radius (derived from alpha_0 and s) | derived |

The sinusoidal region provides a smooth transition from the flat plate (where the field must be uniform) to the circular cap (which closes the electrode). Larger *alpha_0* produces a more abrupt transition with higher field enhancement; smaller *alpha_0* gives a gentler transition but a larger electrode. The trade-off is similar to changing *k* in the Chang profile: more compactness costs more field enhancement.

---

## Glossary

| Term | Definition |
|------|------------|
| **Axisymmetric** | A geometry that is rotationally symmetric about a central axis. A 2D cross-section is revolved 360 degrees to produce the 3D shape. |
| **Closing arc** | The curve that connects the outermost tip of the profile back to the electrode body or symmetry axis, closing the boundary for simulation. |
| **Conformal mapping** | A complex-variable transformation that preserves angles. Used to derive electrode shapes that maintain field uniformity because Laplace's equation is invariant under conformal maps. |
| **Crowding distance** | (NSGA-II) A measure of how isolated a solution is within its Pareto front. Higher crowding distance means more diversity is preserved in the next generation. |
| **CV(E) %** | Coefficient of variation of the electric field: 100 x sigma / mu. Measures overall field homogeneity along the electrode surface (lower = flatter field). |
| **DE (Differential Evolution)** | A population-based evolutionary optimisation algorithm that uses vector differences for mutation. Good for global search in rugged landscapes. |
| **Dirichlet boundary** | A boundary condition that fixes the potential (voltage) on a surface. Applied to electrode surfaces in FEMM simulations. |
| **dE %** | Percentage field enhancement: how much the 99th-percentile field exceeds the theoretical uniform value. The primary quality metric in this application. |
| **E_uniform** | The theoretical uniform electric field between infinite parallel plates: E = dV / s. Used as the reference for computing dE %. |
| **FEF** | Field Enhancement Factor: E_max / E_uniform. A perfect electrode has FEF = 1.0. Related to dE % by: dE % = (FEF - 1) x 100. |
| **FEMM** | Finite Element Method Magnetics - the open-source 2D FEA solver used for electrostatic simulation in this application. |
| **Golden ratio (phi)** | (1 + sqrt(5)) / 2 = 1.618. Used by the golden-section search to divide the parameter interval optimally, guaranteeing that each step reuses one evaluation from the previous step. |
| **Laplace's equation** | nabla-squared phi = 0. The governing equation for electrostatic potential in charge-free regions. All electrode simulations solve this equation. |
| **Neumann boundary** | A boundary condition that specifies the normal derivative of the potential (e.g. zero flux = no field component normal to the boundary). |
| **Non-dominated front** | (NSGA-II) A set of solutions where no solution is better than another on all objectives simultaneously. Front 0 is the Pareto front; front 1 is dominated only by front 0; etc. |
| **NSGA-II** | Non-dominated Sorting Genetic Algorithm II. A multi-objective evolutionary optimiser that returns a Pareto front of trade-off solutions. |
| **Pareto front** | The set of optimal trade-off solutions in a multi-objective problem. No solution on the front can be improved in one objective without worsening another. |
| **Planar** | A 2D geometry that is extruded uniformly in the out-of-plane direction (finite or infinite depth). Used for strip-electrode configurations. |
| **Profile** | The mathematically defined curve that shapes the electrode edge to control field uniformity. Four types: Rogowski, Chang, Ernst, Bruce. |
| **pyfemm** | Python bindings for FEMM 4.2. Installs via `pip install pyfemm` but imports as `import femm` in code. |
| **Schwarz-Christoffel mapping** | A specific conformal mapping that transforms the upper half-plane to the interior of a polygon. The Rogowski profile is derived from one such mapping applied to a semi-infinite plate. |
| **Symmetry boundary** | A modelling technique where only half the geometry is simulated; the other half is implied by a symmetry condition at the midplane. Halves computation time and mesh size. |
