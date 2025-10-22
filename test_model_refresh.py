"""Quick test script to verify model fetching from different providers."""

from openai import OpenAI
import requests
import re


def test_ollama_models():
    """Test fetching models from Ollama."""
    print("Testing Ollama model fetch...")
    base_url = "http://localhost:11434/v1"
    
    try:
        # Method 1: Direct API
        ollama_base = re.sub(r'/v1/?$', '', base_url)
        response = requests.get(f"{ollama_base}/api/tags", timeout=5.0)
        response.raise_for_status()
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        
        print(f"✅ Found {len(models)} Ollama models:")
        for model in sorted(models):
            print(f"  - {model}")
        return True
    except Exception as exc:
        print(f"❌ Ollama error: {exc}")
        return False


def test_openai_models():
    """Test fetching models from OpenAI (requires API key)."""
    print("\nTesting OpenAI model fetch...")
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("⚠️  Skipped: OPENAI_API_KEY not set")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.models.list()
        models = [model.id for model in response.data]
        
        # Filter to common chat models
        chat_models = [m for m in models if any(x in m for x in ['gpt-4', 'gpt-3.5'])]
        
        print(f"✅ Found {len(chat_models)} OpenAI chat models:")
        for model in sorted(chat_models)[:10]:  # Show first 10
            print(f"  - {model}")
        return True
    except Exception as exc:
        print(f"❌ OpenAI error: {exc}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Model Provider Integration\n")
    print("=" * 50)
    
    ollama_ok = test_ollama_models()
    openai_ok = test_openai_models()
    
    print("\n" + "=" * 50)
    print("\nResults:")
    print(f"  Ollama: {'✅ Working' if ollama_ok else '❌ Failed (is Ollama running?)'}")
    print(f"  OpenAI: {'✅ Working' if openai_ok else '⚠️  Skipped or Failed'}")
    
    if ollama_ok:
        print("\n💡 Try the model dropdown in GlyphX Settings!")
        print("   Settings → Click '🔄 Refresh' next to Model field")
