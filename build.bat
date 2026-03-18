@echo off
REM ============================================================
REM  Build distributable exe using PyInstaller (single file)
REM  Requires: pip install pyinstaller
REM ============================================================

echo ============================================================
echo  Building Electrode Profile Generator
echo ============================================================

REM Install PyInstaller if missing
pip install pyinstaller --quiet

REM Clean previous build artifacts
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "*.spec" del /q *.spec

REM Build single-file exe
pyinstaller --onefile --windowed ^
    --name "ProfileGenerator" ^
    --icon "assets\icon.png" ^
    --add-data "src\version.py;." ^
    --add-data "src\profiles.py;." ^
    --add-data "src\dxf_exporter.py;." ^
    --add-data "src\InputValidator.py;." ^
    --add-data "assets;assets" ^
    src\gui.py

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
