# Terminal AI Assistant Guide

GlyphX now includes an **AI Assistant** mode in the Terminal panel, allowing you to interact with your terminal using natural language powered by your configured LLM.

---

## 🎯 What Can It Do?

The Terminal AI Assistant can:

1. **Translate natural language to commands**
   - "list all Python files" → `Get-ChildItem -Filter *.py -Recurse`
   - "what's my IP address?" → `ipconfig`
   
2. **Explain terminal concepts**
   - "how do I find large files?"
   - "what does this error mean?"

3. **Suggest commands based on context**
   - Knows your current working directory
   - Remembers your recent commands
   - Adapts to your shell (PowerShell, Bash, etc.)

4. **Provide help and tips**
   - "how do I commit in git?"
   - "show me docker commands"

---

## 🚀 Quick Start

### Enable AI Mode

1. Go to **💻 Terminal** panel
2. Click the **🤖 AI Assistant** checkbox
3. Start asking questions!

### Example Usage

```
🤖 list all Python files
💡 Suggested command: Get-ChildItem -Filter *.py -Recurse
Press Enter to run it, or edit first.
```

---

## 💡 Use Cases

### File Operations
- "find large files"
- "compress this folder"
- "delete old logs"

### Git Commands
- "commit with message X"
- "push to main"
- "show branches"

### System Info
- "check disk space"
- "what's my Python version?"
- "show running processes"

### DevOps
- "list docker containers"
- "restart nginx"
- "deploy to prod"

---

**Full guide:** See [docs/TERMINAL_AI_GUIDE.md](TERMINAL_AI_GUIDE.md) for detailed examples and troubleshooting.
