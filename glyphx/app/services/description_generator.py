"""Generate human-readable descriptions for commands using Gemma."""

from __future__ import annotations

from openai import OpenAI


class DescriptionGenerator:
    """Create descriptions for glyphs."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma:300m",
    ) -> None:
        """Initialize description generator.

        Args:
            base_url: Ollama API endpoint
            model: Model name (default: gemma:300m)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    def generate(self, command: str, timeout: float = 5.0) -> str:
        """Generate a one-sentence description of what the command does.

        Args:
            command: Shell command to describe
            timeout: Request timeout in seconds

        Returns:
            Human-readable description string
        """
        prompt = f"""Write a one-sentence description of what this command does. Be concise.

Command: {command}

Description:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=50,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""

    def generate_from_name_and_command(
        self, name: str, command: str, timeout: float = 5.0
    ) -> str:
        """Generate description considering both name and command.

        Args:
            name: Glyph name
            command: Shell command
            timeout: Request timeout in seconds

        Returns:
            Human-readable description string
        """
        prompt = f"""Write a one-sentence description for this glyph. Be concise.

Name: {name}
Command: {command}

Description:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=50,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""

    def improve_description(
        self, current_description: str, timeout: float = 5.0
    ) -> str:
        """Improve an existing description.

        Args:
            current_description: Current description text
            timeout: Request timeout in seconds

        Returns:
            Improved description string
        """
        prompt = f"""Improve this description to be more clear and concise. One sentence only.

Current: {current_description}

Improved:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50,
                timeout=timeout,
            )
            improved = response.choices[0].message.content.strip()
            return improved if improved else current_description
        except Exception:
            return current_description
