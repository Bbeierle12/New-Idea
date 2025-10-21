# Gemma Background Worker Guide

GlyphX now supports **Gemma 300M** as a lightweight background worker for fast, local AI-powered features. This guide explains how to set up and use these features.

---

## 🎯 What Does Gemma Do?

Gemma runs **locally** via Ollama and handles quick, focused tasks without using your main LLM (GPT-4, Claude, etc.):

1. **Auto-Tagging** - Suggests tags for glyphs based on command content
2. **Description Generation** - Creates human-readable descriptions for commands
3. **Session Summaries** - Summarizes your recent terminal activity
4. **Command Classification** - Routes commands to the right handler
5. **Intent Parsing** - Extracts structured data from natural language

---

## 🚀 Setup Instructions

### 1. Install Ollama

**Windows:**
```powershell
# Download from https://ollama.com/download
# Or use winget
winget install Ollama.Ollama
```

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the Gemma Model

```powershell
ollama pull gemma:300m
```

### 3. Start Ollama Server

```powershell
ollama serve
```

Leave this running in the background.

### 4. Enable Gemma in GlyphX

1. Open GlyphX
2. Go to **⚙️ Settings**
3. Scroll to **🤖 Gemma Background Worker**
4. Check **"Enable Gemma..."**
5. Verify settings:
   - **Gemma Base URL**: `http://localhost:11434/v1`
   - **Gemma Model**: `gemma:300m`
6. Click **Save**
7. **Restart GlyphX** for changes to take effect

---

## 📚 Feature Guide

### Auto-Tagging Glyphs

When creating or editing a glyph:

1. Enter your command (e.g., `docker build -t myapp .`)
2. Click **🤖 Suggest** next to the Tags field
3. Gemma will suggest relevant tags like `docker`, `build`, `container`
4. Tags are automatically added to your existing tags

**Example:**
```
Command: kubectl apply -f deployment.yaml
Suggested Tags: kubernetes, deploy, yaml
```

---

### Session Summaries

Summarize what you've been doing in the terminal:

1. Go to **💻 Terminal** panel
2. Run some commands
3. Click **📝 Summarize** in the header
4. Get a plain-English summary of your recent activity

**Example Summary:**
> "The user performed several Git operations: checking repository status, staging all changes, and committing updates to documentation files. They also ran a build command and tested the application."

---

### Smart Glyph Search (Coming Soon)

Future update will add natural language search:
- "find python scripts" → filters by keyword and language
- "show docker commands" → finds docker-related glyphs
- "deployment scripts tagged prod" → structured filtering

---

## ⚙️ Advanced Configuration

### Using a Different Model

You can use any small Ollama model instead of Gemma:

```powershell
# Try other models
ollama pull phi3:mini       # Microsoft's Phi-3 (3.8B)
ollama pull qwen2.5:1.5b   # Qwen 1.5B
ollama pull tinyllama      # 1.1B parameters
```

Update in Settings → Gemma Model to your chosen model.

### Performance Tuning

**Fast Response (< 1 second):**
- `gemma:300m` - Best balance of speed and quality
- `tinyllama` - Fastest, less accurate

**Better Quality (2-3 seconds):**
- `phi3:mini` - More accurate for technical content
- `qwen2.5:1.5b` - Better at structured output

### Multiple Models

You can run **both** a main LLM and Gemma simultaneously:

- **Main LLM** (Settings → Model): `gpt-4o-mini` or `llama3.2:3b`
  - Used for: Chat, Agent, complex tool-calling
  
- **Gemma** (Settings → Gemma Model): `gemma:300m`
  - Used for: Quick classification, tagging, summaries

---

## 🔍 Troubleshooting

### "No tags suggested" or "No summary available"

**Check Ollama is running:**
```powershell
ollama list
```

You should see `gemma:300m` in the list.

**Test Gemma directly:**
```powershell
ollama run gemma:300m "Suggest 3 tags for: docker build -t app ."
```

### Slow responses

- Gemma should respond in < 1 second
- If slow, check CPU usage (Ollama uses CPU by default)
- Consider using a smaller model like `tinyllama`

### "Import could not be resolved" errors

These are harmless lint errors. The `openai` package is already in your dependencies. To suppress:

```powershell
pip install openai
```

---

## 🎓 Best Practices

### When to Use Gemma vs Main LLM

**Use Gemma for:**
- Quick, repetitive tasks (tagging, classification)
- Structured output (JSON, lists)
- Background processing
- No internet required

**Use Main LLM for:**
- Complex reasoning
- Multi-step planning
- Tool calling with context
- Conversational responses

### Offline Development

Gemma works **100% offline** once pulled:
- No API keys needed
- No rate limits
- No costs
- Private and secure

---

## 📊 API Reference

### AutoTagger

```python
from glyphx.app.services.auto_tagger import AutoTagger

tagger = AutoTagger()
tags = tagger.suggest_tags("docker build -t app .", max_tags=3)
# Returns: ['docker', 'build', 'container']
```

### SessionSummarizer

```python
from glyphx.app.services.session_summarizer import SessionSummarizer

summarizer = SessionSummarizer()
summary = summarizer.summarize_recent(command_history, limit=10)
# Returns: "The user performed Git operations and ran tests."
```

### CommandClassifier

```python
from glyphx.app.services.classifier import CommandClassifier

classifier = CommandClassifier()
cmd_type = classifier.classify("git status")
# Returns: 'shell'
```

---

## 🔮 Future Features

Planned enhancements:

- **Smart Glyph Search** - Natural language filtering
- **Command Suggestions** - Auto-complete based on history
- **Error Explanations** - Plain-English error messages
- **Workflow Detection** - Identify command patterns
- **Auto-Documentation** - Generate README from glyphs

---

## 🛠️ Development

### Testing Gemma Services

Run tests (requires Ollama running):

```powershell
pytest glyphx/tests/test_auto_tagger.py -v
pytest glyphx/tests/test_session_summarizer.py -v
pytest glyphx/tests/test_classifier.py -v
```

Most tests are skipped by default (require Ollama). Remove `@pytest.mark.skip` to run them.

### Custom Services

Create your own Gemma-powered service:

```python
from openai import OpenAI

class MyCustomService:
    def __init__(self):
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="not-needed"
        )
        self.model = "gemma:300m"
    
    def my_task(self, input_text: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": input_text}],
            temperature=0.2,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
```

---

## 📝 License

Gemma integration is part of GlyphX and follows the same license. Gemma model is provided by Google under Apache 2.0.

---

**Questions?** Open an issue on GitHub or check the [main docs](docs/USER_GUIDE.md).
