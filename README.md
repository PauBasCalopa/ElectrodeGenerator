# Electrode Profile Generator

Interactive tool for generating and visualizing electrode profiles (Rogowski, Chang, Ernst) for parallel plate electrode design. Exports to CSV, PNG, DXF, and FEMM 4.2 Lua scripts.

## Features

- **Three profile types** — Rogowski, Chang, Ernst
- **Live preview** — sliders + entry boxes update the plot in real time
- **Electrode assembly** — toggle to see full parallel plate construction (4 curves + 2 plates)
- **Ernst edge-effect** — Auto k₀ button calculates optimal k₀ for edge-free design
- **European input** — accepts both `.` and `,` as decimal separator
- **DXF export wizard** — choose DXF version (R12–R2018), entity type (Spline or Polyline), layer options
- **FEMM 4.2 export** — Lua script wizard with voltage, permittivity, mesh, and problem type settings
- **Export** — CSV, PNG, DXF (CAD-ready), FEMM Lua (simulation-ready)

## Quick Start

### GUI (recommended)

```bash
pip install -r requirements.txt
cd src
python main.py
```

### CLI

```bash
cd src
python main.py --cli
python main.py --cli --profile chang
python main.py --cli --profile ernst
```

### Build distributable exe

```bash
build.bat
```

Output: `dist\ProfileGenerator.exe` (single file, no Python required on target).

## Project Structure

```
ElectrodeGenerator/
├── src/
│   ├── main.py             — Single entry point (GUI default, --cli for CLI)
│   ├── gui.py              — GUI application (Tkinter + matplotlib)
│   ├── profiles.py         — Profile base class + Rogowski, Chang, Ernst
│   ├── dxf_exporter.py     — DXF export (ezdxf, R12–R2018)
│   ├── femm_exporter.py    — FEMM 4.2 Lua script generator
│   ├── InputValidator.py   — Input validation (European decimals, etc.)
│   └── version.py          — App metadata (name, version, author)
├── assets/
│   └── icon.png            — Application icon
├── docs/
│   └── user_guide.md       — User guide and documentation
├── build.bat               — PyInstaller build script
├── pyproject.toml          — Project metadata & packaging
├── requirements.txt        — Python dependencies
├── README.md
└── LICENSE
```

## Profile Equations
based on:
"Espino-Cortes, Fermín & Escarela-Perez, R & Calva-Chavarria, P & Campero-Littlewood, Eduardo. (2000). Numerical study of the profile of parallel plate electrodes. Proceedings of the Universities Power Engineering Conference". 

| Profile  | Equations |
|----------|-----------|
| Rogowski | X = (s/π)(u + 1 + eᵘ cos v), Y = (s/π)(v + eᵘ sin v) |
| Chang    | X = u + cos(v)·sinh(u), Y = v + k·sin(v)·cosh(u) |
| Ernst    | X = u + k₀·cos(v)·sinh(u) + k₁·cos(2v)·sinh(2u), Y = v + k₀·sin(v)·cosh(u) + k₁·sin(2v)·cosh(2u) |

Where v = π/2 (constant), k₁ = k₀²/8 (Ernst).

## Dependencies

- **numpy** — numerical computation
- **matplotlib** — plotting and PNG export
- **ezdxf** — DXF file generation
- **pyinstaller** — exe build (optional, for distribution)
