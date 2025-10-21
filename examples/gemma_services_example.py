"""
Example: Using Gemma Background Worker Services

This script demonstrates how to use the Gemma-powered services
independently from the GUI.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from glyphx.app.services.auto_tagger import AutoTagger
from glyphx.app.services.description_generator import DescriptionGenerator
from glyphx.app.services.session_summarizer import SessionSummarizer
from glyphx.app.services.classifier import CommandClassifier
from glyphx.app.services.intent_parser import IntentParser
from glyphx.app.infra.history import CommandHistory, CommandRecord


def example_auto_tagger():
    """Example: Suggest tags for a command."""
    print("=== Auto-Tagger Example ===")
    
    tagger = AutoTagger()
    
    # Check if Gemma is available
    if not tagger.suggest_tags("test", timeout=2.0):
        print("❌ Gemma not available. Make sure Ollama is running:")
        print("   ollama serve")
        print("   ollama pull gemma:300m")
        return
    
    # Suggest tags for various commands
    commands = [
        "docker build -t myapp:latest .",
        "kubectl apply -f deployment.yaml",
        "pytest tests/ -v --cov",
        "git commit -m 'Add new feature'",
    ]
    
    for cmd in commands:
        tags = tagger.suggest_tags(cmd, max_tags=3)
        print(f"\nCommand: {cmd}")
        print(f"Tags: {', '.join(tags)}")


def example_description_generator():
    """Example: Generate descriptions for commands."""
    print("\n=== Description Generator Example ===")
    
    generator = DescriptionGenerator()
    
    commands = [
        "npm run build",
        "rsync -avz /src /dest",
        "find . -name '*.py' -type f",
    ]
    
    for cmd in commands:
        desc = generator.generate(cmd)
        print(f"\nCommand: {cmd}")
        print(f"Description: {desc}")


def example_session_summarizer():
    """Example: Summarize command history."""
    print("\n=== Session Summarizer Example ===")
    
    summarizer = SessionSummarizer()
    
    # Create temporary history
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.jsonl"
        history = CommandHistory(history_path)
        
        # Simulate a work session
        session_commands = [
            "git pull origin main",
            "npm install",
            "npm run test",
            "npm run build",
            "git add .",
            "git commit -m 'Update dependencies'",
            "git push origin main",
        ]
        
        for cmd in session_commands:
            history.append(CommandRecord(
                command=cmd,
                cwd="/home/user/project",
                source="terminal",
                exit_code=0
            ))
        
        # Generate summary
        summary = summarizer.summarize_recent(history, limit=10)
        print(f"\nSession Summary:\n{summary}")
        
        # Generate short title
        title = summarizer.generate_session_title(history, limit=5)
        print(f"\nSession Title: {title}")


def example_command_classifier():
    """Example: Classify different types of commands."""
    print("\n=== Command Classifier Example ===")
    
    classifier = CommandClassifier()
    
    test_inputs = [
        "ls -la",
        "run my deployment script",
        "read the config.json file",
        "what is the weather today?",
        "ambiguous input here",
    ]
    
    for input_text in test_inputs:
        cmd_type = classifier.classify(input_text)
        print(f"\nInput: {input_text}")
        print(f"Type: {cmd_type}")


def example_intent_parser():
    """Example: Parse structured intent from natural language."""
    print("\n=== Intent Parser Example ===")
    
    parser = IntentParser()
    
    # Parse search queries
    search_queries = [
        "find python scripts tagged docker",
        "show me all deployment commands",
        "glyphs with kubernetes in them",
    ]
    
    print("\nSearch Intent Parsing:")
    for query in search_queries:
        intent = parser.parse_glyph_search(query)
        print(f"\nQuery: {query}")
        print(f"Parsed: {intent}")
    
    # Parse file paths
    file_queries = [
        "read the config.json file",
        "open ~/.bashrc",
        "show me package.json",
    ]
    
    print("\n\nFile Path Extraction:")
    for query in file_queries:
        path = parser.parse_file_path(query)
        print(f"\nQuery: {query}")
        print(f"Path: {path}")


def main():
    """Run all examples."""
    print("🤖 Gemma Background Worker Examples")
    print("=" * 50)
    print("\nMake sure Ollama is running with gemma:300m:")
    print("  ollama serve")
    print("  ollama pull gemma:300m\n")
    
    try:
        example_auto_tagger()
        example_description_generator()
        example_session_summarizer()
        example_command_classifier()
        example_intent_parser()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed!")
        
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        print("\nMake sure Ollama is running and gemma:300m is available.")


if __name__ == "__main__":
    main()
