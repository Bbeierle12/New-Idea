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

1. Open Config > Settings (or press Ctrl+,) and configure your LLM provider:
   - **🤖 LLM Tab**: API key, model name, base URL, timeouts, and agent prompt
   - **🛡️ Safety Tab**: Tool output limits, truncation settings, and default mode
2. The console tab will display structured logs as actions occur.

### Configuring Safety Settings

The Settings dialog includes a **🛡️ Safety** tab with the following options:

**Tool Output Max Bytes**:
- Controls the maximum size of tool outputs
- Default: 8,000 bytes (8 KB)
- Range: 1,000 - 100,000 bytes
- Increase for large file operations
- Decrease for memory-constrained systems

**Context Truncation Enabled**:
- When enabled, tool outputs exceeding the limit are automatically truncated
- Truncation markers clearly indicate when content is shortened
- Keep enabled unless you have a specific need for full outputs

**Default Mode**:
- Sets the mode GlyphX starts in
- `chat`: Safe Mode (tools disabled) - recommended
- `agent`: Agent Mode (tools enabled)

**Reset to Defaults**:
- Click this button to restore safe default values
- Useful if you're experiencing issues or unsure about your configuration

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

### Safety Modes

GlyphX includes two safety modes to protect your system:

**🛡️ Chat Mode (Safe Mode)**:
- Tools are disabled
- Safe for general conversations
- Recommended for most interactions
- No file system or command access

**⚡ Agent Mode**:
- Tools are enabled with validation
- Commands are validated before execution
- File operations restricted to workspace
- Output size limits prevent memory issues
- User confirmation required for dangerous operations

**Mode Indicator**:
- Look for the colored badge in the top area (e.g., "🛡️ Safe Mode" in green or "⚡ Agent Mode" in yellow)
- Click the indicator for detailed information about the current mode
- Hover over it for a quick tooltip

**Switching Modes**:
1. Use the mode selector dropdown in the top-right area
2. Choose "🛡️ Safe Chat" or "⚡ Agent Mode"
3. The mode indicator updates immediately

**Best Practice**: Start in Chat Mode and switch to Agent Mode only when you need tool execution.

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
- [Safety Guide](SAFETY_GUIDE.md) - Comprehensive guide to safety features and best practices
- [Quick Reference](../QUICK_REFERENCE.md) - Feature summaries and tips
- [Primary README](../README.md)