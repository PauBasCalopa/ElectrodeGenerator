# Electrode Profile Generator

Interactive tool for generating and visualizing electrode profiles (Rogowski, Chang, Ernst) for parallel plate electrode design. Exports to CSV, PNG, and DXF.

## Features

- **Three profile types** — Rogowski, Chang, Ernst
- **Live preview** — sliders + entry boxes update the plot in real time
- **Electrode assembly** — toggle to see full parallel plate construction (4 curves + 2 plates)
- **Ernst edge-effect** — Auto k₀ button calculates optimal k₀ for edge-free design
- **European input** — accepts both `.` and `,` as decimal separator
- **Export** — CSV, PNG (plot), DXF (CAD-ready with named layers)

## Quick Start

### GUI (recommended)

```bash
pip install -r requirements.txt
cd src
python gui.py
```

### CLI

```bash
cd src
python main.py
python main.py --profile chang
python main.py --profile ernst
```

### Build distributable exe

```bash
build.bat
```

Output: `dist\ProfileGenerator.exe` (single file, no Python required on target).

## Project Structure

```
ProfileGenerator/
├── src/
│   ├── gui.py              — GUI application (Tkinter + matplotlib)
│   ├── main.py             — CLI entry point
│   ├── profiles.py         — Profile base class + Rogowski, Chang, Ernst
│   ├── dxf_exporter.py     — DXF export (ezdxf)
│   ├── InputValidator.py   — Input validation (European decimals, etc.)
│   └── version.py          — App metadata (name, version, author)
├── assets/
│   └── icon.png            — Application icon
├── docs/
│   └── implementation_plan.md
├── build.bat               — PyInstaller build script
├── requirements.txt        — Python dependencies
├── README.md
└── LICENSE.txt
```

## Profile Equations

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
