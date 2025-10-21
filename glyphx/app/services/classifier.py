"""Lightweight command classifier using Gemma 300M for fast routing."""

from __future__ import annotations

from typing import Literal

from openai import OpenAI

CommandType = Literal["glyph", "shell", "file_operation", "chat", "unclear"]


class CommandClassifier:
    """Fast classification of user commands using a small local model."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma:300m",
    ) -> None:
        """Initialize classifier with Gemma model.

        Args:
            base_url: Ollama API endpoint
            model: Model name (default: gemma:300m)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    def classify(self, command: str, timeout: float = 5.0) -> CommandType:
        """Classify command type without expensive LLM call.

        Args:
            command: User's input text
            timeout: Request timeout in seconds

        Returns:
            Command type category
        """
        prompt = f"""Classify this command into ONE category:
- glyph: Running a saved command/script
- shell: Direct terminal command (ls, cd, git, etc)
- file_operation: Reading/writing files
- chat: Conversational question
- unclear: Ambiguous/needs clarification

Command: {command}

Respond with ONLY the category name, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10,
                timeout=timeout,
            )
            result = response.choices[0].message.content.strip().lower()

            if result in ("glyph", "shell", "file_operation", "chat", "unclear"):
                return result  # type: ignore

            return "unclear"
        except Exception:
            return "unclear"

    def is_available(self) -> bool:
        """Check if Gemma model is available.

        Returns:
            True if model responds, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                timeout=3.0,
            )
            return bool(response.choices)
        except Exception:
            return False
