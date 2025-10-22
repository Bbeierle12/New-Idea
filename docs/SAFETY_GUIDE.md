# 🛡️ GlyphX Safety Guide

## Table of Contents
- [Overview](#overview)
- [Safety Modes](#safety-modes)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

GlyphX includes a comprehensive safety system designed to protect your system from:
- **Resource Exhaustion**: Prevents excessive memory usage from large tool outputs
- **Dangerous Commands**: Validates and blocks potentially harmful shell commands
- **File System Access**: Restricts file operations to your workspace directory
- **Unintended Actions**: Requires confirmation for destructive operations

The safety system operates in two modes: **Chat Mode** (tools disabled) and **Agent Mode** (tools enabled with validation).

### Key Features
✅ Command validation and filtering
✅ File path jailing (workspace-only access)
✅ Configurable output size limits
✅ Automatic context truncation
✅ Interactive mode indicator
✅ Real-time safety status

---

## Safety Modes

### 🛡️ Chat Mode (Safe Mode)

**Status**: Tools completely disabled

**Use Cases**:
- General conversations
- Asking questions about code
- Brainstorming ideas
- Learning new concepts
- Discussing architecture

**Protection Level**: Maximum
- No file system access
- No shell command execution
- No network operations
- No tool calls

**Visual Indicator**:
```
🛡️ Safe Mode
Background: Light green (#d4edda)
Foreground: Dark green (#155724)
```

**When to Use**:
- Default mode for most interactions
- When you don't need file or command execution
- When multiple users have access
- During initial exploration of the assistant

### ⚡ Agent Mode

**Status**: Tools enabled with safety validation

**Use Cases**:
- Code generation and file creation
- Running tests and builds
- Analyzing existing files
- Executing shell commands
- Complex multi-step tasks

**Protection Level**: High
- Command safety validation
- File path restrictions
- Output size limits
- Confirmation prompts for dangerous operations

**Visual Indicator**:
```
⚡ Agent Mode
Background: Light yellow (#fff3cd)
Foreground: Dark yellow/brown (#856404)
```

**When to Use**:
- When you need tool execution
- For code generation tasks
- When running tests or builds
- For file analysis and manipulation
- Advanced automation tasks

### Switching Modes

**In the GUI**:
1. Locate the mode selector dropdown (top-right area)
2. Click to expand options
3. Select "🛡️ Safe Chat" or "⚡ Agent Mode"
4. Mode indicator updates immediately

**Mode Persistence**:
- Mode selection persists within the current session
- Default mode (configured in Settings) applies on restart
- Each conversation can use different modes

---

## Configuration

### Opening Settings

**Method 1**: Keyboard shortcut
```
Press: Ctrl+, (Windows/Linux) or Cmd+, (macOS)
```

**Method 2**: Menu
```
Config → Settings…
```

### Safety Tab Options

#### 1. Tool Output Max Bytes

**Purpose**: Limits the size of individual tool outputs to prevent memory issues

**Default**: 8,000 bytes (8 KB)

**Range**: 1,000 - 100,000 bytes (1 KB - 100 KB)

**Configuration**:
- Use the spinbox to set the exact value
- Real-time display shows KB conversion
- Changes take effect immediately (no restart required)

**Recommendations**:
- **Small Projects**: 8,000 bytes (default)
- **Medium Projects**: 16,000 bytes
- **Large Projects**: 32,000 bytes
- **Very Large Files**: 64,000 - 100,000 bytes

**Examples**:
```
 8,000 bytes =  8 KB  → Typical code files
16,000 bytes = 16 KB  → Larger source files
32,000 bytes = 32 KB  → Documentation files
64,000 bytes = 64 KB  → Very large files
```

#### 2. Context Truncation Enabled

**Purpose**: Automatically truncates tool outputs that exceed the size limit

**Default**: Enabled (✓)

**Behavior**:
- **When Enabled**: Outputs exceeding the limit are truncated with clear markers
- **When Disabled**: Full outputs are sent to the LLM (may cause memory/context issues)

**Truncation Marker Example**:
```
[Content truncated: showing first 8000 of 25000 bytes. 
Original content exceeded safe size limit for context management.]
```

**When to Disable**:
- ⚠️ Rarely recommended
- Only if you understand the memory implications
- When you have a specific need for full outputs
- With very high `tool_output_max_bytes` settings

#### 3. Default Mode

**Purpose**: Sets the initial mode when GlyphX starts

**Default**: `chat` (Safe Mode)

**Options**:
- `chat`: Start in Safe Mode (tools disabled)
- `agent`: Start in Agent Mode (tools enabled)

**Recommendations**:
- **Keep as `chat`**: Safest option, switch to agent mode as needed
- **Use `agent`**: Only if you frequently need tools immediately

### Resetting to Defaults

**When to Reset**:
- You're experiencing issues with custom settings
- You're unsure about your current configuration
- You want to restore the safest settings

**How to Reset**:
1. Open Settings → 🛡️ Safety tab
2. Click "Reset to Defaults" button
3. Confirm the reset

**Default Values**:
```
Tool Output Max Bytes: 8,000
Context Truncation Enabled: ✓ Yes
Default Mode: chat
```

---

## Best Practices

### For Beginners

1. **Start in Chat Mode**
   - Use Safe Mode until you need tools
   - Switch to Agent Mode only when required
   - Switch back to Chat Mode after tool tasks

2. **Use Default Settings**
   - Keep the default 8 KB output limit
   - Keep truncation enabled
   - Keep default mode as `chat`

3. **Monitor Truncation**
   - Watch for truncation markers in tool outputs
   - Increase limit if needed for specific tasks
   - Return to lower limit after task completion

4. **Click to Learn**
   - Click the mode indicator for detailed information
   - Hover for quick tooltips
   - Understand what's enabled in each mode

### For Advanced Users

1. **Dynamic Mode Switching**
   - Switch to Agent Mode for specific tasks
   - Return to Chat Mode for general discussion
   - Use mode indicator as a constant reminder

2. **Optimize Output Limits**
   - Increase limits for large file operations
   - Keep limits reasonable to avoid context bloat
   - Monitor truncation frequency

3. **Understand Validations**
   - Know which commands are allowed/blocked
   - Understand file path restrictions
   - Review confirmation prompts carefully

4. **Leverage Safety Features**
   - Use truncation for context management
   - Rely on command validation for protection
   - Configure limits based on project needs

### For Teams

1. **Standardize Settings**
   - Document recommended settings for your team
   - Share safe configurations
   - Establish mode usage guidelines

2. **Default to Safe**
   - Keep default mode as `chat`
   - Require explicit agent mode activation
   - Review agent mode usage regularly

3. **Monitor and Adjust**
   - Track truncation frequency
   - Adjust limits based on project types
   - Update guidelines as needed

---

## Technical Details

### Safety Validation System

#### Command Validation

**Allowed Commands** (Whitelist):
```python
ALLOWED_COMMANDS = {
    'ls', 'dir', 'pwd', 'cd', 'cat', 'head', 'tail', 'grep',
    'find', 'echo', 'which', 'whoami', 'hostname', 'date',
    'python', 'python3', 'pip', 'pip3', 'node', 'npm', 'yarn',
    'git', 'make', 'cmake', 'cargo', 'go', 'rustc',
    'gcc', 'g++', 'clang', 'javac', 'java', 'mvn', 'gradle'
}
```

**Denied Patterns** (Blacklist):
```python
DENIED_PATTERNS = [
    r'\brm\s+-rf\b',      # Recursive force delete
    r'\bsudo\b',          # Privilege escalation
    r'\bsu\b',            # Switch user
    r'\bchmod\s+777\b',   # Insecure permissions
    r'\bcurl.*\|\s*bash', # Pipe to shell
    r'\bwget.*\|\s*bash', # Pipe to shell
    r'\bdd\b',            # Disk operations
    r'\bmkfs\b',          # Format filesystem
    r'\bformat\b',        # Format disk
    r'\bdel\s+/[SF]\b',   # Windows force delete
]
```

#### File Path Validation

**Restrictions**:
1. **Path Jailing**: All file operations restricted to workspace directory
2. **Denied Extensions**: `.env`, `.key`, `.pem`, `.p12`, `.pfx`, credential files
3. **Size Limits**: Files > 10 MB require user confirmation

**Example Validations**:
```python
# ✅ Allowed
"/workspace/src/main.py"           # Inside workspace
"/workspace/docs/README.md"        # Inside workspace

# ❌ Blocked
"/etc/passwd"                      # System file
"~/.ssh/id_rsa"                    # Sensitive file
"/workspace/../etc/passwd"         # Path traversal attempt
"/workspace/.env"                  # Sensitive extension
```

#### Output Truncation

**Algorithm**:
1. Check output size against `tool_output_max_bytes`
2. If exceeded and truncation enabled:
   - Try to parse as JSON and truncate fields
   - If not JSON, truncate at byte limit
   - Add clear truncation marker
3. If truncation disabled, send full output (may cause issues)

**Truncation Marker**:
```
[Content truncated: showing first {current_size} of {original_size} bytes. 
Original content exceeded safe size limit for context management.]
```

### Architecture Components

#### SafetyValidator (`glyphx/app/infra/safety.py`)
- Command validation
- File path validation
- Output truncation
- Configuration management

#### ToolsBridge (`glyphx/app/services/tools.py`)
- Integrates SafetyValidator
- Executes validated commands
- Manages user confirmations
- Handles truncation

#### SettingsService (`glyphx/app/services/settings.py`)
- Persists safety configuration
- Validates setting ranges
- Provides defaults
- Thread-safe updates

#### AIPanel (`glyphx/app/gui.py`)
- Mode selector UI
- Interactive mode indicator
- Settings dialog with Safety tab
- Real-time updates

---

## Troubleshooting

### Problem: Tool outputs are being truncated

**Symptoms**:
- See truncation markers in responses
- Missing parts of file contents
- Incomplete command outputs

**Solutions**:
1. Increase "Max output size" in Settings → 🛡️ Safety
2. Reasonable values: 16,000 bytes (16 KB) for medium files
3. Keep under 100,000 bytes to avoid context issues

**Example**:
```
Settings → 🛡️ Safety → Max output size: 16000
```

### Problem: Commands won't execute in Agent Mode

**Symptoms**:
- Commands are blocked
- See "command denied" in console
- Tool execution fails

**Solutions**:
1. Check if command is in allowed list (see Technical Details)
2. Review console output for specific denial reason
3. Use alternative allowed commands if possible
4. Contact admin if command should be allowed

**Example Console Output**:
```
[error] Command denied: 'sudo apt install' - contains blocked pattern
```

### Problem: Can't access files outside workspace

**Symptoms**:
- File operations fail
- "Path outside workspace" errors
- Can't read system files

**Solutions**:
1. **This is intentional** - safety feature working correctly
2. Copy files into workspace if needed
3. Use allowed commands that can view system info (e.g., `which`, `whoami`)

**Note**: This is a security feature, not a bug.

### Problem: Mode indicator not updating

**Symptoms**:
- Mode selector changes but indicator doesn't update
- Wrong color showing

**Solutions**:
1. This should not happen - file a bug report
2. Restart GlyphX as a temporary workaround
3. Check console for errors

### Problem: Settings not persisting

**Symptoms**:
- Settings reset after restart
- Changes don't save

**Solutions**:
1. Ensure you clicked "Save" in Settings dialog
2. Check file permissions on settings directory
3. Review console for save errors

---

## FAQ

### Why can't I disable safety features?

Safety features are designed to protect your system and data. While you can adjust limits, core features like command validation and path jailing cannot be disabled. This prevents accidental damage from AI-generated commands.

### Can I add commands to the allowed list?

Currently, the allowed command list is hardcoded for security. If you need a specific command whitelisted, please open an issue with your use case.

### What happens if I set output size to maximum (100 KB)?

Large outputs can:
- Consume significant context window space
- Reduce the AI's ability to track conversation
- Increase API costs (more tokens)
- Slow down responses

We recommend keeping limits reasonable (8-32 KB) unless you have a specific need.

### Why is default mode "chat" instead of "agent"?

Chat mode is safer and appropriate for most interactions. You only need Agent mode when executing tools. Starting in Chat mode and explicitly switching to Agent mode creates better awareness of when tools are enabled.

### Does Chat mode make the assistant less capable?

No. Chat mode only disables tool execution. The assistant can still:
- Answer questions about code
- Explain concepts
- Provide code examples
- Discuss architecture
- Suggest solutions

You just can't execute those solutions automatically until you switch to Agent mode.

### How do I know if truncation is happening too often?

Watch for truncation markers in responses. If you see them frequently and they're affecting functionality:
1. Increase `tool_output_max_bytes`
2. Consider whether you need full outputs
3. Break tasks into smaller operations

### Can different conversations use different modes?

Yes! Each conversation maintains its own mode. The default mode (from Settings) only applies when starting a new conversation or restarting GlyphX.

### What's the performance impact of safety features?

Minimal. Command validation and path checking are fast operations. Output truncation only activates when needed. You won't notice any performance degradation.

### Are safety features tested?

Yes! The safety system includes:
- 10 unit tests for SafetyValidator
- 15 integration tests for ToolsBridge safety
- 18 tests for context management
- 11 tests for configurable settings
- **Total: 54 tests with 100% pass rate**

### How do I report a safety issue?

If you find a way to bypass safety features or discover a vulnerability:
1. **Do not** disclose publicly
2. Open a private security advisory on GitHub
3. Or email the maintainers directly
4. We take security seriously and will respond promptly

---

## Additional Resources

- **Quick Reference**: See `QUICK_REFERENCE.md` for feature summaries
- **Architecture**: See `docs/ARCHITECTURE.md` for system design
- **User Guide**: See `docs/USER_GUIDE.md` for general usage
- **Step 1 Implementation**: See `STEP1_SAFETY_IMPLEMENTATION.md` for validator details
- **Step 2 Integration**: See `STEP2_SAFETY_INTEGRATION.md` for tools integration
- **Step 3 Context**: See `STEP3_IMPLEMENTATION.md` for context management
- **Step 4 UX**: See `STEP4_USER_EXPERIENCE.md` for settings and UI

---

**Stay Safe! 🛡️** The safety system is here to protect you. Use it wisely, configure it appropriately, and enjoy a secure AI assistant experience.
