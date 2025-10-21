# Terminal Panel Guide

## Overview

The **Terminal Panel** is a built-in interactive terminal emulator that allows you to execute shell commands directly within GlyphX. It provides a convenient way to interact with your PC's command line without leaving the application.

## Features

### 🖥️ Interactive Command Execution
- Execute any shell command directly from the GlyphX interface
- See real-time output with color-coded results
- Track command history across sessions

### 📂 Working Directory Management
- Set and change the working directory for commands
- Browse for directories using the GUI file picker
- Commands execute in the specified working directory

### 📜 Command History
- Navigate through previous commands using **Up/Down arrow keys**
- History is shared across Terminal, Chat, and Agent panels
- Persistent history across application sessions

### 🎨 Color-Coded Output
- **Blue**: Command prompt showing current directory
- **Cyan**: Commands you type
- **White**: Standard output (stdout)
- **Red/Orange**: Error messages and stderr
- **Exit codes** displayed for non-zero returns

### ⚡ Built-in Commands
- `clear` or `cls` - Clear the terminal output
- `cd <directory>` - Change working directory (built-in navigation)

## How to Use

### 1. Access the Terminal
- Click on **💻 Terminal** in the left sidebar
- The terminal panel will open with a command prompt

### 2. Execute Commands
- Type your command in the input field at the bottom
- Press **Enter** or click **Run** to execute
- Wait for the command to complete

### 3. Navigate Directories
You can change the working directory in two ways:

**Option A: Use the GUI**
- Click the **Browse…** button
- Select a directory from the file picker
- Commands will execute in that directory

**Option B: Use cd command**
```bash
cd C:\Users\YourName\Documents
cd ..
cd subfolder
```

### 4. View Command History
- Press **Up Arrow** to scroll through previous commands
- Press **Down Arrow** to navigate forward in history
- History includes commands from Terminal, Chat, and Agent

### 5. Clear Output
- Click the **Clear** button to clear the terminal display
- Or type `clear` (or `cls`) and press Enter

## Examples

### Basic Commands
```bash
# List files in current directory
dir

# Show current directory
cd

# Create a new directory
mkdir my_project

# Navigate to directory
cd my_project

# View file contents
type file.txt

# Run Python scripts
python script.py

# Check Python version
python --version
```

### PowerShell Commands
```powershell
# List files with details
Get-ChildItem

# Get system information
Get-ComputerInfo

# Show running processes
Get-Process

# Network information
ipconfig
```

### Git Commands
```bash
# Check git status
git status

# View commit history
git log --oneline

# Show branches
git branch

# Pull latest changes
git pull
```

### Advanced Usage
```bash
# Run commands with output
python -c "print('Hello from GlyphX Terminal')"

# Chain commands (PowerShell)
cd C:\Projects ; dir

# Pipe output
dir | findstr ".py"
```

## Tips & Best Practices

### ✅ Do's
- Use the working directory picker for complex paths
- Save frequently-used commands as **Glyphs** for quick access
- Check the **Console** panel for detailed execution logs
- Use command history to repeat or modify previous commands

### ⚠️ Don'ts
- Avoid running interactive programs (they require input)
- Don't run long-running services directly (use Glyphs with background mode)
- Be careful with destructive commands (rm, del, format, etc.)

## Integration with Other Features

### 🏷️ Glyphs
Save your frequently-used terminal commands as Glyphs:
1. Go to the **Glyphs** panel
2. Click **Add**
3. Enter command and working directory
4. Run it anytime with one click

### 💬 Chat & 🤖 Agent
The LLM can execute shell commands through the same backend:
- Commands run in Chat/Agent are logged to history
- You can see and reuse them in the Terminal
- Working directory is shared

### 📊 Console
All terminal command executions are logged to the Console panel:
- View execution timestamps
- See command parameters and results
- Debug command failures

## Troubleshooting

### Command Not Found
**Problem**: Command isn't recognized
**Solution**: Ensure the program is in your PATH or use full path

### Permission Denied
**Problem**: Insufficient permissions
**Solution**: Run GlyphX as administrator for privileged commands

### Command Hangs
**Problem**: Command appears stuck
**Solution**: 
- Check if command requires user input (not supported)
- Use timeout settings in Settings panel
- Restart GlyphX if needed

### Wrong Directory
**Problem**: Command runs in wrong location
**Solution**: 
- Check working directory field
- Use `cd` command to navigate
- Browse to correct directory

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Execute command |
| `Up Arrow` | Previous command |
| `Down Arrow` | Next command |
| `Ctrl+C` | (In terminal - copy, not stop) |

## Security Considerations

⚠️ **Important Security Notes:**
- Commands execute with your user permissions
- Be cautious with commands that modify files
- Review commands before execution
- Sensitive output is visible in the terminal
- Command history is stored locally in plain text

## Technical Details

### Command Execution
- Commands run asynchronously via worker thread
- Timeout configurable in Settings (default: 600 seconds)
- Output limited to 128KB per stream
- Both stdout and stderr are captured

### Shell Environment
- Windows: Uses PowerShell/cmd depending on system
- Commands execute with `shell=True` for full shell features
- Environment variables from parent process are inherited
- Working directory is per-command, not persistent shell

### History Storage
- Stored in: `~/.glyphx/command_history.jsonl`
- Format: JSON Lines with timestamp and source
- Shared across Terminal, Chat, and Agent
- Persists across application restarts

## Future Enhancements

Potential future features (not yet implemented):
- Tab completion
- Multi-line commands
- Process interruption (Ctrl+C)
- Background process management
- Terminal splitting/multiple terminals
- Command output search/filter
- Export terminal session

## Need Help?

- Check the **Console** panel for error details
- Review logs in `~/.glyphx/logs/`
- See **QUICK_REFERENCE.md** for overall GlyphX usage
- Refer to **USER_GUIDE.md** for comprehensive documentation
