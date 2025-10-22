# GlyphX

GlyphX is a cross-platform desktop companion for managing and sharing your favorite shell commands (glyphs). The desktop app ships with a Tkinter UI, background task worker, Windows/macOS/Linux exporters, and an OpenAI-compatible chat experience that can call local tools (run glyphs, execute shell commands, read/write files). A one-shot agent loop can take a goal and iterate through tool calls to finish small tasks while logging every step.

## Features (v0.1.0)

![Main Window](docs/screenshots/main-window.png)

- **Glyphs panel**: add/edit/remove glyphs, double-click or press `Ctrl+R` to run, inspect command/cwd previews, search by name/tags/cmd, and import/export as JSON.
- **Exporters**: generate Windows `.bat`, macOS `.command`, and Linux `.desktop` launchers with safe filenames and executable bits.
- **Terminal panel**: interactive terminal emulator with command history, working directory management, color-coded output, and full shell command support—access your PC terminal directly within GlyphX. Now includes **🤖 AI Assistant** mode for natural language command suggestions. [Learn more](docs/TERMINAL_AI_GUIDE.md)
- **AI Chat panel**: unified chat and agent interface (similar to VS Code Copilot) with mode toggle. Configure API key/model/base URL, chat with the LLM (streamed responses), or run one-shot agent goals. Both modes support tool calling and inspect tool invocations (`[tool:*]`). View token usage per exchange.
- **Command history**: persistent log of the last 50 glyph/shell commands, visible alongside the glyph list.
- **Worker + logging infra**: a dedicated background worker keeps the UI responsive, while structured logs accumulate in both the console pane and JSONL files (with automatic rotation).
- **🤖 Gemma Background Worker**: Optional local AI assistant for auto-tagging glyphs, generating descriptions, summarizing terminal sessions, and more—all running offline via Ollama. [Learn more](docs/GEMMA_GUIDE.md)
- **🔄 Model Dropdown**: Automatically fetch and select from available models for OpenAI, Ollama, or any OpenAI-compatible provider. [Learn more](docs/MODEL_DROPDOWN_GUIDE.md)

## Quick Start

### Installation
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate # macOS/Linux
pip install -e .[dev]
```

### Running GlyphX

**Option 1: Using the launcher scripts (easiest)**
```bash
# Windows
run_glyphx.bat

# macOS/Linux
./run_glyphx.sh
# or
python run_glyphx.py
```

**Option 2: Direct command**
```bash
python -m glyphx.app
```

**Option 3: VS Code Task (if using VS Code)**
- Press `Ctrl+Shift+B` or
- Press `Ctrl+Shift+P` → "Run Task" → "▶️ Run GlyphX"

1. Open **Config > Settings...** (or press `Ctrl+,`) to enter your API key, preferred model, and base URL.
2. Use the **Glyphs** panel (`Ctrl+N` to add) to define commands and double-click (or `Ctrl+R`) to run. Output is streamed to the Console tab.
3. Switch to **Terminal** to execute shell commands interactively with full command history and working directory control.
4. Switch to **AI Chat** to interact with the LLM:
   - Select **💬 Chat** mode for multi-turn conversations, tool calling, and streaming responses
   - Select **🤖 Agent** mode for one-shot goal execution (e.g., "List glyphs and write them to glyphs.txt")
   - Tool invocations are logged with a `[tool]` prefix in both modes
5. Choose **File > Export...** to create OS-native launchers for your glyph library.

Config, registry, logs, and chat history live in `%APPDATA%\glyphx\` on Windows (and the standard config directory on macOS/Linux).

## Development

- `make lint` — run Black, isort, Ruff, and mypy over the `glyphx` package.
- `make test` — execute the pytest suite, including property tests powered by Hypothesis.

Advanced configuration lives in Settings (LLM timeout, rate limit per minute, shell timeout, agent prompt). Logs rotate automatically and crash dumps write to `logs/crash.jsonl`.

Additional helpers:

- `pytest -k tools` to focus on the tool bridge.
- `pytest --maxfail=1 -vv` for faster iteration on failing cases.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Terminal Guide](docs/TERMINAL_GUIDE.md) — Complete guide to the built-in terminal feature
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Contributing Guide](docs/CONTRIBUTING.md)

## Packaging

The Makefile exposes cross-platform PyInstaller targets (plus a cleanup helper):

```bash
make bundle-win   # Windows executable
make bundle-mac   # macOS app bundle
make bundle-linux # Linux CLI binary
make clean-bundles
```

Each target produces bundles under `dist/` that match the OS-specific GitHub Actions jobs.

## Continuous Integration & Releases

- `.github/workflows/ci.yml` runs lint/tests with coverage on Windows, macOS, and Linux, uploads `coverage.xml`, pushes results to Codecov (optional token), and builds PyInstaller artifacts for each OS.
- `.github/workflows/nightly.yml` triggers at 03:00 UTC (and manually) to produce nightly bundles and attach them as workflow artifacts.
- `.github/workflows/release.yml` builds platform bundles whenever a `v*` tag is pushed (or `workflow_dispatch`) and publishes them to the GitHub release automatically.

Configure a `CODECOV_TOKEN` secret for private repos to enable coverage uploads.

## Project Layout

```
glyphx/
 ├─ app/
 │   ├─ gui.py                 # Tkinter UI, chat, agent, menus
 │   ├─ services/              # registry, exporters, tools, settings, llm client
 │   └─ infra/                 # worker, logger, chat history, paths
 ├─ tests/                     # pytest + hypothesis suites
 └─ pyproject.toml             # packaging + dev extras
```

## License

GlyphX is released under the MIT License. See `LICENSE` for details.