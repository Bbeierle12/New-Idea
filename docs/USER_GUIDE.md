# GlyphX User Guide

## Installation

1. Install Python 3.10 or newer.
2. Clone the repository and create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate   # macOS/Linux
   pip install -e .
   ```
3. Launch the application:
   ```bash
   python -m glyphx.app
   ```

## First Run

1. Open Config > Settings and provide your API key, model name, base URL, and (optionally) a custom agent prompt.
2. The console tab will display structured logs as actions occur.

## Managing Glyphs

- **Add** – Ctrl+N or the Add button. Provide a name, command, optional emoji, optional tags (comma separated), and working directory.
- **Edit** – Select a glyph and click Edit.
- **Remove** – Select a glyph and press Delete or the Remove button.
- **Run** – Double-click a glyph, use Ctrl+R, or press Run. Output and status can be seen in the Console tab. The command history panel records recent runs.
- **Search** – Use the search box above the list to filter by name, command, or tags. Use the Import... button to load glyphs from an exported JSON file.

## Chatting with the LLM

1. Switch to the Chat tab.
2. Type a message and press Ctrl+Enter or click Send. Responses stream into the transcript.
3. Tool calls appear prefixed with [tool:*] in the transcript; results are recorded in chat_history.jsonl, and shell/glyph invocations land in the command history.
4. Usage statistics (prompt/completion/total tokens) are appended after each exchange. Use Clear to reset the conversation.

### Supported Tools

- list_glyphs
- run_glyph
- run_shell
- read_file
- write_file
- list_files

## Running Agent Tasks

1. Open the Agent tab.
2. Enter a concise goal (for example, "List glyphs and write them to glyphs.txt"). The agent uses the system prompt configured in Settings.
3. Press Run. Each step is logged with the tool payload and results.
4. A summary is provided once the loop finishes or hits the step limit.

## Exporting Launchers

1. Choose File > Export...
2. Select a destination folder. GlyphX will create OS-specific launchers (.bat / .command / .desktop).
3. Review the confirmation dialog for the list of generated files.

## Logs & History

- Registry: <config_dir>/registry.json
- Settings: <config_dir>/config.json
- Chat history: <config_dir>/chat_history.jsonl
- Command history: <config_dir>/command_history.jsonl
- App logs: <config_dir>/logs/app.log (automatically rotated); crash dumps: <config_dir>/logs/crash.jsonl

<config_dir> resolves to %APPDATA%\glyphx\ on Windows, ~/Library/Application Support/glyphx/ on macOS, and $XDG_CONFIG_HOME/glyphx or ~/.config/glyphx on Linux.

## Troubleshooting

- Ensure your API key is valid and has access to the specified model.
- Check the Console tab and logs/app.log for detailed error messages.
- If PyInstaller bundles fail, run make clean-bundles before building again.

## Additional Resources

- [Architecture Overview](ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Primary README](../README.md)