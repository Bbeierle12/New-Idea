"""Auto-generate tags for glyphs using Gemma."""

from __future__ import annotations

from openai import OpenAI


class AutoTagger:
    """Suggest tags based on glyph command."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma:300m",
    ) -> None:
        """Initialize auto-tagger.

        Args:
            base_url: Ollama API endpoint
            model: Model name (default: gemma:300m)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    def suggest_tags(
        self, command: str, max_tags: int = 3, timeout: float = 5.0
    ) -> list[str]:
        """Generate tag suggestions from command text.

        Args:
            command: Shell command or glyph command
            max_tags: Maximum number of tags to suggest
            timeout: Request timeout in seconds

        Returns:
            List of suggested tag strings
        """
        prompt = f"""Suggest {max_tags} short tags for this command. Return comma-separated list only.

Command: {command}

Tags:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=30,
                timeout=timeout,
            )
            tags_str = response.choices[0].message.content.strip()
            tags = [
                t.strip().lower() for t in tags_str.split(",") if t.strip()
            ]
            return tags[:max_tags]
        except Exception:
            return []

    def suggest_from_name_and_command(
        self, name: str, command: str, max_tags: int = 3, timeout: float = 5.0
    ) -> list[str]:
        """Generate tags from both name and command.

        Args:
            name: Glyph name
            command: Shell command
            max_tags: Maximum number of tags
            timeout: Request timeout in seconds

        Returns:
            List of suggested tag strings
        """
        prompt = f"""Suggest {max_tags} short tags for this glyph. Return comma-separated list only.

Name: {name}
Command: {command}

Tags:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=30,
                timeout=timeout,
            )
            tags_str = response.choices[0].message.content.strip()
            tags = [
                t.strip().lower() for t in tags_str.split(",") if t.strip()
            ]
            return tags[:max_tags]
        except Exception:
            return []
