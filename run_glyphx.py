#!/usr/bin/env python
"""GlyphX Launcher - Convenient executable to start the application."""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch GlyphX application."""
    print("🚀 Starting GlyphX...")
    
    # Get the project root directory
    root_dir = Path(__file__).parent
    
    try:
        # Run the application
        result = subprocess.run(
            [sys.executable, "-m", "glyphx.app"],
            cwd=root_dir,
            check=False
        )
        
        if result.returncode != 0:
            print("\n❌ GlyphX exited with an error.")
            print("Make sure you have installed the package: pip install -e .")
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        print("\n👋 GlyphX stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting GlyphX: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
