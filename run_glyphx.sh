#!/bin/bash
# GlyphX Launcher for Linux/macOS
echo "🚀 Starting GlyphX..."
python -m glyphx.app
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: GlyphX failed to start."
    echo "Make sure you have installed the package: pip install -e ."
    exit 1
fi
