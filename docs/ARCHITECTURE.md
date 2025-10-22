# GlyphX Architecture Overview

## Layers

1. **UI Layer (Tkinter)** – `glyphx/app/gui.py`
   - `GlyphsPanel`: CRUD and execution for saved glyphs.
   - `AIPanel`: Unified chat and agent interface with mode toggle. OpenAI-compatible chat with tool-calling, streaming transcripts, and one-shot agent execution.
   - `TerminalPanel`: Interactive shell with command history and AI assistant mode.
   - `ConsolePanel`: Structured log viewer.

2. **Services (`glyphx/app/services/`)**
   - `registry.py`: JSON-backed glyph persistence.
   - `export.py`: OS-specific launcher generation (.bat/.command/.desktop).
   - `settings.py`: API/auth configuration storage.
   - `llm.py`: OpenAI-compatible REST client with tool-call scaffolding.
   - `tools.py`: ToolBridge exposing glyph/shell/file helpers.

3. **Infrastructure (`glyphx/app/infra/`)**
   - `worker.py`: Single-thread task queue to keep the UI responsive.
   - `logger.py`: Structured logging with optional sinks for console/files.
   - `paths.py`: Platform-aware config directory resolution.
   - `chat_history.py`: Append-only JSONL transcript logger.
   - `history.py`: Command history store (JSONL) surfaced in the UI.
   - `diagnostics.py`: Crash reporter and update-check stubs.

## Threading Model

All blocking operations (subprocesses, HTTP requests, heavy file I/O) run on the `Worker` background thread. UI widgets are mutated via `Tk.after`, keeping Tkinter on the main thread.

## Tool Loop

The AIPanel (both chat and agent modes) relies on `_run_tool_loop`, which:
1. Calls the LLM with the current conversation + tool schemas.
2. Executes tool calls through `ToolsBridge`, logging command history where relevant.
3. Streams tool results and assistant replies back into the transcript.
4. Retries HTTP failures with exponential backoff and stops when the assistant returns a final message or the step budget is exhausted.

## Data Storage

- Registry/settings/chat logs live under the platform config directory returned by `ensure_app_paths`.
- Chat history is stored as JSON Lines (`chat_history.jsonl`) for easy tailing and archival.

## Packaging Pipeline

PyInstaller bundles (`bundle-win`, `bundle-mac`, `bundle-linux`) are triggered by Makefile targets and mirrored in CI workflows for release/nightly automation.
