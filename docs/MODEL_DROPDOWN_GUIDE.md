# Model Dropdown Feature Guide

GlyphX now includes a **model dropdown** feature that automatically fetches available models from your chosen provider (OpenAI, Ollama, or any OpenAI-compatible API).

---

## 🎯 How It Works

When you configure GlyphX settings, you can:

1. Enter your **Base URL** (e.g., `http://localhost:11434/v1` for Ollama)
2. Click the **🔄 Refresh** button next to the Model field
3. GlyphX will query the provider and populate the dropdown with available models
4. Select your preferred model from the list

---

## 📋 Supported Providers

### Ollama (Local Models)

**Configuration:**
- Base URL: `http://localhost:11434/v1`
- API Key: (leave empty)
- Click **🔄 Refresh**

**What happens:**
- Queries Ollama's `/api/tags` endpoint
- Lists all locally installed models
- Example models: `llama3.2`, `gemma:300m`, `qwen2.5:7b`

**Requirements:**
```powershell
# Make sure Ollama is running
ollama serve

# Install models
ollama pull llama3.2
ollama pull gemma:300m
ollama pull qwen2.5:7b
```

---

### OpenAI (Cloud)

**Configuration:**
- Base URL: `https://api.openai.com/v1`
- API Key: `sk-your-api-key-here`
- Click **🔄 Refresh**

**What happens:**
- Queries OpenAI's `/v1/models` endpoint
- Lists all available models for your account
- Example models: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`

---

### Azure OpenAI

**Configuration:**
- Base URL: `https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/v1`
- API Key: Your Azure OpenAI API key
- Click **🔄 Refresh**

**Note:** Azure uses deployment names, not model IDs. You may need to enter the deployment name manually.

---

### Other OpenAI-Compatible APIs

Works with any service that implements the OpenAI `/v1/models` endpoint:

- **LM Studio**: `http://localhost:1234/v1`
- **LocalAI**: `http://localhost:8080/v1`
- **vLLM**: `http://your-server:8000/v1`
- **Text-generation-webui**: `http://localhost:5000/v1`

---

## 🚀 Usage Examples

### Example 1: Using Ollama with Multiple Models

1. **Start Ollama and pull models:**
   ```powershell
   ollama serve
   ollama pull llama3.2:3b
   ollama pull qwen2.5:7b
   ollama pull mistral:7b
   ```

2. **In GlyphX Settings:**
   - Preset: Click **🦙 Ollama**
   - Click **🔄 Refresh** next to Model
   - Dropdown shows: `llama3.2:3b`, `mistral:7b`, `qwen2.5:7b`
   - Select `qwen2.5:7b` (great for tool calling)
   - Click **Save**

---

### Example 2: Using OpenAI

1. **In GlyphX Settings:**
   - Preset: Click **🤖 OpenAI**
   - Enter API Key: `sk-...`
   - Click **🔄 Refresh**
   - Dropdown shows: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, etc.
   - Select `gpt-4o-mini` (fast and affordable)
   - Click **Save**

---

### Example 3: Gemma Background Worker

The Gemma section also has its own dropdown!

1. **Enable Gemma:**
   - Check ✅ **"Enable Gemma..."**
   - Gemma Base URL: `http://localhost:11434/v1`
   - Click **🔄** next to Gemma Model

2. **Select Model:**
   - Dropdown shows all Ollama models
   - Gemma models are prioritized (e.g., `gemma:300m`, `gemma:2b`)
   - Choose `gemma:300m` for fast tagging/summarization

---

## 🔧 Troubleshooting

### "No models found"

**For Ollama:**
```powershell
# Check if Ollama is running
ollama list

# If no models, pull some
ollama pull llama3.2
ollama pull gemma:300m
```

**For OpenAI:**
- Verify API key is correct
- Check internet connection
- Ensure API key has proper permissions

---

### "Failed to fetch models"

**Check Base URL format:**
- ✅ Correct: `http://localhost:11434/v1`
- ❌ Wrong: `http://localhost:11434` (missing `/v1`)
- ✅ Correct: `https://api.openai.com/v1`
- ❌ Wrong: `https://api.openai.com` (missing `/v1`)

**Check connectivity:**
```powershell
# For Ollama
curl http://localhost:11434/api/tags

# For OpenAI
curl https://api.openai.com/v1/models -H "Authorization: Bearer sk-..."
```

---

### Dropdown shows no models but service is running

**Solution 1: Manual entry**
- You can still type the model name directly in the dropdown
- Example: Type `llama3.2` even if refresh failed

**Solution 2: Check logs**
- Error messages will show in a popup
- Common issues: firewall, wrong URL, missing API key

---

## 💡 Tips & Best Practices

### 1. Use Refresh After Changes

Always click **🔄 Refresh** after:
- Changing the Base URL
- Adding a new API key
- Installing new Ollama models
- Switching providers

### 2. Model Selection Strategies

**For Chat/Agent (Main LLM):**
- Ollama: `qwen2.5:7b` (best tool calling)
- OpenAI: `gpt-4o-mini` (fast and cheap)
- Local: `llama3.2:3b` (good balance)

**For Gemma (Background Worker):**
- Ollama: `gemma:300m` (fastest)
- Alternative: `tinyllama` (smaller)
- Better quality: `phi3:mini` (3.8B)

### 3. Keyboard Shortcuts

- Type to search in dropdown
- Arrow keys to navigate
- Enter to select

---

## 🎓 Advanced Features

### Custom Model Names

If a model isn't in the dropdown, you can still type it manually:
- Example: Type `gpt-4o` if you have beta access
- Example: Type custom deployment name for Azure

### Multiple Providers

You can quickly switch between providers:
1. Click **🦙 Ollama** → Select local model
2. Work offline
3. Click **🤖 OpenAI** → Select cloud model
4. Use cloud for complex tasks

### Model Aliases

Ollama supports tags:
- `llama3.2:latest` (default)
- `llama3.2:3b` (specific size)
- `llama3.2:3b-instruct-q4_0` (quantization level)

All variants will appear in the dropdown.

---

## 📊 Technical Details

### API Endpoints Used

**Ollama:**
```
GET http://localhost:11434/api/tags
Response: { "models": [{ "name": "llama3.2", ... }] }
```

**OpenAI:**
```
GET https://api.openai.com/v1/models
Response: { "data": [{ "id": "gpt-4o-mini", ... }] }
```

### Timeout

Model refresh has a **5 second timeout**. If your provider is slow:
- Local Ollama: Should be instant
- Cloud API: Usually < 2 seconds
- Slow connection: May timeout (can still type model name manually)

---

## 🔮 Future Enhancements

Planned features:
- **Model info tooltips** - Show model size, context length
- **Favorite models** - Pin frequently used models
- **Model search** - Filter large model lists
- **Auto-refresh** - Check for new models on startup
- **Model validation** - Test model before saving

---

**Questions?** Check the main [User Guide](USER_GUIDE.md) or [Gemma Guide](GEMMA_GUIDE.md).
