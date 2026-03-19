@echo off
REM ============================================================
REM  Build distributable exe using PyInstaller (single file)
REM  Requires: .venv with dependencies installed
REM ============================================================

echo ============================================================
echo  Building Electrode Profile Generator
echo ============================================================

REM Create venv if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install/update dependencies
pip install -r requirements.txt --quiet

REM Clean previous build artifacts
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "*.spec" del /q *.spec

REM Build single-file exe
pyinstaller --onefile --windowed ^
    --name "ProfileGenerator" ^
    --icon "assets\icon.png" ^
    --paths "src" ^
    --hidden-import "ezdxf" ^
    --hidden-import "core" ^
    --hidden-import "core.profiles" ^
    --hidden-import "core.assembly" ^
    --hidden-import "core.contour" ^
    --hidden-import "core.optimizer" ^
    --hidden-import "core.validation" ^
    --hidden-import "exporters" ^
    --hidden-import "exporters.csv_exporter" ^
    --hidden-import "exporters.dxf_exporter" ^
    --hidden-import "exporters.png_exporter" ^
    --hidden-import "exporters.femm_exporter" ^
    --hidden-import "simulation" ^
    --hidden-import "simulation.femm_model" ^
    --hidden-import "simulation.femm_simulator" ^
    --hidden-import "gui" ^
    --hidden-import "gui.app" ^
    --hidden-import "gui.dialogs" ^
    --hidden-import "gui.dialogs.dxf_wizard" ^
    --hidden-import "gui.dialogs.femm_wizard" ^
    --hidden-import "gui.dialogs.optimize_wizard" ^
    --hidden-import "version" ^
    --add-data "assets;assets" ^
    src\main.py

echo.

REM Clean build junk, keep only dist/
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q *.spec

if exist "dist\ProfileGenerator.exe" (
    echo ============================================================
    echo  Build successful!
    echo  Output: dist\ProfileGenerator.exe
    echo ============================================================
) else (
    echo ============================================================
    echo  Build FAILED.
    echo ============================================================
)
pause
