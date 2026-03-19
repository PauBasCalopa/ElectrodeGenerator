# Electrode Profile Generator

Desktop application for designing parallel plate electrodes with mathematically defined edge profiles. Based on conformal mapping theory, it generates Rogowski, Chang, and Ernst profiles — the three classic geometries used in high-voltage engineering to control electric field uniformity between parallel plates.

The tool provides a real-time interactive GUI, full electrode assembly visualization, and direct export to CAD (DXF), simulation (FEMM 4.2 Lua), and data formats (CSV, PNG).

## Screenshots

| Profile editor | FEMM simulation | Electric field plot |
|:-:|:-:|:-:|
| ![Profile editor](assets/Captura.JPG) | ![Electrode assembly](assets/Captura2.JPG) | ![FEMM simulation](assets/Captura3.JPG) |

## Why This Tool?

Parallel plate electrodes need carefully shaped edges to avoid field enhancement at the plate boundaries. The profile geometry is derived from conformal mappings and is not trivial to compute by hand. This tool lets you:

- **Explore** different profile types and parameters interactively
- **Visualize** the complete electrode assembly (top + bottom electrodes with flat plates)
- **Export** directly to SolidWorks/AutoCAD (DXF) or FEMM 4.2 (Lua script)
- **Simulate** electrostatic fields in FEMM without manual model setup
- **Optimize** electrode geometry via built-in golden-section search

## Features

| Feature | Description |
|---------|-------------|
| **3 profile types** | Rogowski, Chang, Ernst — selectable from a dropdown |
| **Live preview** | Sliders + text entry update the plot in real time |
| **Electrode assembly** | Toggle full mirrored construction (4 curves + 2 flat plates) |
| **Ernst Auto k₀** | One-click calculation of optimal k₀ for edge-free design |
| **DXF export wizard** | R12–R2018, Spline or Polyline, layer control |
| **FEMM Lua wizard** | Complete simulation setup: voltages, εᵣ, mesh, boundary conditions |
| **FEMM live simulation** | Run FEMM directly from the GUI (requires pyfemm) |
| **Profile optimizer** | Golden-section search to minimize field non-uniformity |
| **European input** | Accepts both `.` and `,` as decimal separator |

## Quick Start

```bash
git clone https://github.com/PauBasCalopa/ElectrodeGenerator.git
cd ElectrodeGenerator
pip install -r requirements.txt
cd src
python main.py
```

CLI mode: `python main.py --cli` · Build exe: `build.bat` → `dist\ProfileGenerator.exe`

## Project Structure

```
src/
├── main.py                  — Entry point (GUI default, --cli for CLI)
├── version.py               — App metadata
├── core/                    — Pure logic (no UI)
│   ├── profiles.py          — Rogowski, Chang, Ernst generators
│   ├── assembly.py          — Electrode assembly builder
│   ├── contour.py           — Contour utilities
│   ├── optimizer.py         — Golden-section optimizer
│   └── validation.py        — Input validation
├── exporters/               — File output
│   ├── csv_exporter.py      — CSV export
│   ├── png_exporter.py      — PNG export
│   ├── dxf_exporter.py      — DXF export (R12–R2018)
│   └── femm_exporter.py     — FEMM Lua script generator
├── simulation/              — FEMM integration
│   ├── femm_model.py        — Shared model builder
│   └── femm_simulator.py    — Live FEMM COM driver
└── gui/                     — Tkinter GUI
    ├── app.py               — Main application window
    └── dialogs/             — DXF, FEMM, and optimizer wizards
```

## Profile Equations

Based on: *Espino-Cortes, F. et al. (2000). "Numerical study of the profile of parallel plate electrodes." Proceedings of the Universities Power Engineering Conference.*

| Profile | Equations | Key parameter |
|---------|-----------|---------------|
| **Rogowski** | X = (s/π)(u + 1 + eᵘ cos v) · Y = (s/π)(v + eᵘ sin v) | s (gap) scales the profile |
| **Chang** | X = u + cos(v)·sinh(u) · Y = v + k·sin(v)·cosh(u) | k controls compactness |
| **Ernst** | X = u + k₀·cos(v)·sinh(u) + k₁·cos(2v)·sinh(2u) · Y = … | k₁ = k₀²/8, Auto k₀ = 1.72·e⁻³·⁵ˢ |

Where v = π/2 (constant) in all profiles.

## Dependencies

- **numpy** · **matplotlib** · **ezdxf** — core dependencies
- **pyfemm** — optional, for live FEMM simulation
- **pyinstaller** — optional, for building the standalone exe

## License

MIT
