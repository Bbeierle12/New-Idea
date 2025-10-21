"""Entry point for GlyphX desktop application."""

from __future__ import annotations

from .gui import Application


def main() -> None:
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
