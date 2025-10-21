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
```
API Key: [your-openai-key]
Model: gpt-4o-mini
Base URL: https://api.openai.com/v1
LLM timeout (seconds): 60.0
LLM rate limit per minute: 10        # NEW!
Shell timeout (seconds): 600.0
Agent system prompt: [custom prompt]
```

### Recommended Settings
**For OpenAI Free Tier**:
```
LLM rate limit per minute: 3
LLM timeout (seconds): 60.0
```

**For OpenAI Paid Tier**:
```
LLM rate limit per minute: 60
LLM timeout (seconds): 30.0
```

**For Local Models**:
```
Base URL: http://localhost:11434/v1
LLM rate limit per minute: (empty)
LLM timeout (seconds): 120.0
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
- ✅ Comprehensive test coverage
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

---

## 📚 Additional Resources

- **Architecture**: See `docs/ARCHITECTURE.md`
- **Contributing**: See `docs/CONTRIBUTING.md`
- **User Guide**: See `docs/USER_GUIDE.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

---

**Need Help?** Check the logs in the Console panel or open an issue on GitHub!
