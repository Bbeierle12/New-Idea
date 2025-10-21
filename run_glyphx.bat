@echo off
REM GlyphX Launcher for Windows
echo Starting GlyphX...
python -m glyphx.app
if errorlevel 1 (
    echo.
    echo Error: GlyphX failed to start.
    echo Make sure you have installed the package: pip install -e .
    pause
)
