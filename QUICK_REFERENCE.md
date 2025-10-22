# Quick Reference: New Features

## 🏷️ Tags Feature
**Status**: Already implemented and working!

### Usage
1. When creating/editing a glyph, add tags in the "Tags" field
2. Separate multiple tags with commas: `python, build, test`
3. Tags appear in the glyph list as: `🔨 Build Project [python, build]`
4. Search includes tags automatically - type any tag to filter

### Example
```
Name: Run Tests
Command: pytest -v
Tags: testing, ci, quality
```

---

## 📥 Import Glyphs
**New Feature**: Import glyphs from JSON files

### How to Use
1. Go to **File → Import Glyphs…**
2. Select a JSON file with glyph definitions
3. Review the import summary
4. Glyphs are added to your registry (duplicates skipped)

### JSON Format
```json
{
  "glyphs": [
    {
      "name": "Deploy to Production",
      "cmd": "make deploy-prod",
      "emoji": "🚀",
      "cwd": "/path/to/project",
      "tags": ["deploy", "production"]
    }
  ]
}
```

### Notes
- Duplicate glyphs (same name + command) are automatically skipped
- Import from exported registry files or create your own
- Supports both single glyph and bulk import

---

## ⏱️ Rate Limiting
**New Feature**: Prevent API rate limit errors

### Configuration
Open Settings (**Ctrl+,** or **Config → Settings…**):
```
LLM rate limit per minute: 10
```

### How It Works
- Uses sliding window algorithm
- Tracks requests over 60-second window
- Automatically waits when limit reached
- Logs delays: `[info] rate_limit_sleep seconds=5.23 limit=10`

### Examples
```python
# Allow 10 requests per minute
llm_rate_limit_per_minute: 10

# Allow 60 requests per minute (1 per second)
llm_rate_limit_per_minute: 60

# Disable rate limiting
llm_rate_limit_per_minute: (leave empty or set to 0)
```

### Tips
- OpenAI free tier: ~3 requests/minute recommended
- OpenAI paid tier: ~60 requests/minute safe
- Adjust based on your API plan
- Check logs if experiencing delays

---

## 🌊 Streaming Responses
**New Feature**: See assistant replies in real-time

### How It Works
- Tokens appear as they're generated
- No more waiting for complete response
- Better user experience for long responses
- Automatic fallback if streaming unavailable

### Visual Difference
**Before (without streaming)**:
```
You: Write a Python function
Assistant: [waiting....... 10 seconds......]
Assistant: Here's a Python function that...
```

**After (with streaming)**:
```
You: Write a Python function
Assistant: Here's █
Assistant: Here's a Python █
Assistant: Here's a Python function that█
Assistant: Here's a Python function that calculates...█
```

### Technical Details
- Uses Server-Sent Events (SSE)
- Compatible with OpenAI API
- Handles partial tool calls
- Thread-safe UI updates

### Keyboard Shortcuts
- **Ctrl+Return**: Send chat message
- Messages appear token-by-token in real-time

---

## 🛡️ Safety Features
**New Feature**: Comprehensive safety validation and resource protection

### Mode Indicator
The mode indicator shows the current safety mode with color coding:

| Mode | Indicator | Color | Tools |
|------|-----------|-------|-------|
| Chat | 🛡️ Safe Mode | Green | Disabled |
| Agent | ⚡ Agent Mode | Yellow | Enabled |

**Interactive Features**:
- **Click** the indicator for detailed mode information
- **Hover** over it for a quick tooltip
- Automatically updates when you switch modes

### Safety Modes

#### Chat Mode (Recommended)
- Tools are completely disabled
- Safe for casual conversations
- No file system or shell access
- Ideal for asking questions, getting help, or brainstorming

#### Agent Mode (Advanced)
- Tools are enabled with validation
- Command safety checks
- File path jailing (workspace only)
- Output size limits
- Requires user confirmation for dangerous operations

### Configurable Settings
Open Settings (**Ctrl+,**) and go to the **🛡️ Safety** tab:

#### Tool Output Max Bytes
- **Default**: 8,000 bytes (8 KB)
- **Range**: 1,000 - 100,000 bytes (1 KB - 100 KB)
- **Purpose**: Prevents excessive memory usage from tool outputs
- **Use Case**: Increase for large file operations, decrease for constrained systems

#### Context Truncation Enabled
- **Default**: Enabled (✓)
- **Purpose**: Automatically truncates tool outputs exceeding the limit
- **Behavior**: 
  - When enabled: Outputs are truncated with clear markers
  - When disabled: Full outputs are sent (may cause memory issues)

#### Default Mode
- **Default**: `chat` (Safe Mode)
- **Options**: `chat` or `agent`
- **Purpose**: Sets the initial mode when GlyphX starts
- **Recommendation**: Keep as `chat` for safety

### Safety Validation

When in Agent Mode, the following validations are applied:

**Shell Commands**:
- ✅ Allowed: `ls`, `cat`, `grep`, `python`, `pip`, `git`, etc.
- ❌ Blocked: `rm -rf`, `sudo`, `dd`, `mkfs`, destructive commands
- ⚠️ Confirmation Required: Potentially dangerous operations

**File Operations**:
- ✅ Allowed: Files within the workspace directory
- ❌ Blocked: System files, files outside workspace
- ❌ Blocked: Sensitive extensions (`.env`, `.key`, `.pem`)
- ✅ Size Limits: Files larger than 10 MB require confirmation

**Resource Protection**:
- Command timeouts (configurable)
- Output size limits (configurable)
- Rate limiting for API calls
- Memory-safe truncation

### Examples

#### Switching Modes
```
1. Use the mode selector dropdown in the top-right
2. Choose "🛡️ Safe Chat" or "⚡ Agent Mode"
3. Mode indicator updates immediately
4. Click indicator to learn more about current mode
```

#### Configuring Safety Settings
```
1. Open Settings (Ctrl+,)
2. Go to 🛡️ Safety tab
3. Adjust "Max output size" (e.g., 16000 for 16 KB)
4. Toggle "Enable automatic context truncation"
5. Set "Default mode" (chat recommended)
6. Click "Save"
```

#### Reset to Defaults
```
1. Open Settings → 🛡️ Safety tab
2. Click "Reset to Defaults" button
3. Restores:
   - Max output: 8,000 bytes
   - Truncation: Enabled
   - Default mode: chat
```

### Visual Indicators

**Truncation Markers**:
When context truncation occurs, you'll see:
```
[Content truncated: showing first 8000 of 25000 bytes. 
Original content exceeded safe size limit for context management.]
```

**Mode Indicator States**:
- 🛡️ Safe Mode (Green): Safe for all users
- ⚡ Agent Mode (Yellow): Advanced users, tools enabled

### Tips

1. **Start Safe**: Always begin in Chat Mode until you need tools
2. **Monitor Output**: Watch for truncation markers if processing large files
3. **Adjust as Needed**: Increase limits if working with large codebases
4. **Reset When Unsure**: Use "Reset to Defaults" to restore safe settings
5. **Click to Learn**: Click the mode indicator anytime to see what's enabled

### Troubleshooting

**Problem**: Tool outputs are being truncated unexpectedly
**Solution**: Increase "Max output size" in Settings → 🛡️ Safety

**Problem**: Agent Mode won't execute commands
**Solution**: Commands may be blocked for safety - check console for details

**Problem**: Want to disable safety features
**Solution**: Safety features are intentional - increase limits but keep truncation enabled

---

## 🚀 CI/CD Auto-Versioning
**New Feature**: Automated version management and releases

### Creating a Release
```bash
# Tag a new version
git tag v1.2.3
git push origin v1.2.3
```

This automatically:
1. Extracts version from tag (`v1.2.3` → `1.2.3`)
2. Updates `pyproject.toml`
3. Builds executables for Windows, macOS, Linux
4. Creates GitHub release with artifacts
5. Generates release notes

### Artifact Names
| Platform | Artifact Name | Location |
|----------|--------------|----------|
| Windows | glyphx-windows.exe | GitHub Release |
| macOS | glyphx-macos | GitHub Release |
| Linux | glyphx-linux | GitHub Release |

### CI Builds (Pull Requests)
- Artifacts include version: `glyphx-windows-v1.2.3-4-g1234abc`
- 30-day retention policy
- Available in GitHub Actions artifacts

### Manual Release
1. Go to GitHub Actions
2. Select "Release" workflow
3. Click "Run workflow"
4. Choose branch and run

---

## 🧪 Testing

### Run All Tests
```bash
python -m pytest glyphx/tests/ -v
```

### Run Specific Tests
```bash
# Rate limiting tests
python -m pytest glyphx/tests/test_rate_limiting.py -v

# GUI smoke test
python -m pytest glyphx/tests/test_gui_smoke.py -v
```

### Current Test Status
- ✅ 21 tests passing
- ✅ 3 tests skipped (platform-specific)
- ✅ 60% code coverage
- ✅ 2 new rate limiting tests

---

## 📊 Settings Overview

### Complete Settings List

#### 🤖 LLM Tab
```
API Key: [your-openai-key]
Model: gpt-4o-mini
Base URL: https://api.openai.com/v1
LLM timeout (seconds): 60.0
LLM rate limit per minute: 10
Shell timeout (seconds): 600.0
Agent system prompt: [custom prompt]
Gemma Background Worker: [optional]
```

#### 🛡️ Safety Tab (NEW!)
```
Max output size: 8,000 bytes (8 KB)
Context truncation enabled: ✓
Default mode: chat
```

### Recommended Settings
**For OpenAI Free Tier**:
```
# LLM Tab
LLM rate limit per minute: 3
LLM timeout (seconds): 60.0

# Safety Tab
Max output size: 8,000 bytes
Context truncation: Enabled
Default mode: chat
```

**For OpenAI Paid Tier**:
```
# LLM Tab
LLM rate limit per minute: 60
LLM timeout (seconds): 30.0

# Safety Tab
Max output size: 16,000 bytes
Context truncation: Enabled
Default mode: chat
```

**For Local Models**:
```
# LLM Tab
Base URL: http://localhost:11434/v1
LLM rate limit per minute: (empty)
LLM timeout (seconds): 120.0

# Safety Tab
Max output size: 16,000 bytes
Context truncation: Enabled
Default mode: chat
```

---

## 🔧 Troubleshooting

### Rate Limiting Issues
**Problem**: Seeing rate limit sleep messages too often
**Solution**: Increase `llm_rate_limit_per_minute` or check your API tier

**Problem**: Getting 429 errors from API
**Solution**: Decrease `llm_rate_limit_per_minute` to be more conservative

### Streaming Issues
**Problem**: Responses appear all at once instead of streaming
**Solution**: Check your API endpoint supports streaming (OpenAI does)

**Problem**: UI freezes during streaming
**Solution**: This shouldn't happen - file a bug report if it does

### Import Issues
**Problem**: Import doesn't add any glyphs
**Solution**: Check JSON format matches example above

**Problem**: Some glyphs skipped during import
**Solution**: These are duplicates (same name + command already exist)

---

## 📝 Changelog

### v0.1.0 (Current)
- ✅ Tags already integrated in UI
- ✅ Import Glyphs menu option added
- ✅ Rate limiting implemented
- ✅ Streaming responses enabled
- ✅ CI/CD auto-versioning configured
- ✅ Safety validation system (Steps 1-3)
- ✅ Configurable safety settings (Step 4)
- ✅ Interactive mode indicator with color coding
- ✅ Settings dialog with Safety tab
- ✅ Comprehensive test coverage (54 tests)
- ✅ Zero breaking changes

---

## 🎯 Next Steps

1. **Configure Rate Limiting**: Open settings and set appropriate limit
2. **Try Import**: Create a sample JSON and import it
3. **Test Streaming**: Send a chat message and watch it appear in real-time
4. **Create Release**: Tag a version and watch CI/CD build it
5. **Add Tags**: Update your glyphs with descriptive tags

---

## 💡 Pro Tips

1. **Combine Tags and Search**: Type partial tags to filter instantly
2. **Rate Limit Logging**: Check console panel for rate limit info
3. **Streaming Performance**: Works best with faster models like gpt-4o-mini
4. **Import Workflow**: Export → Edit JSON → Import to bulk update glyphs
5. **Version Tagging**: Use semantic versioning: `v{major}.{minor}.{patch}`
6. **Safety First**: Start in Chat Mode, switch to Agent Mode only when needed
7. **Mode Indicator**: Click the mode badge anytime to see what's enabled
8. **Adjust Limits**: Increase output size for large file operations, keep truncation on
9. **Settings Tabs**: Use 🤖 LLM tab for API config, 🛡️ Safety tab for resource limits
10. **Reset Safety**: Click "Reset to Defaults" if you're unsure about your safety settings

---

## 📚 Additional Resources

- **Architecture**: See `docs/ARCHITECTURE.md`
- **Contributing**: See `docs/CONTRIBUTING.md`
- **User Guide**: See `docs/USER_GUIDE.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

---

**Need Help?** Check the logs in the Console panel or open an issue on GitHub!
