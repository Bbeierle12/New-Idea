"""Extract structured intent from natural language using Gemma."""

from __future__ import annotations

import json
import re

from openai import OpenAI


class IntentParser:
    """Parse user intent into structured actions."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma:300m",
    ) -> None:
        """Initialize intent parser.

        Args:
            base_url: Ollama API endpoint
            model: Model name (default: gemma:300m)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    def parse_glyph_search(self, query: str, timeout: float = 5.0) -> dict[str, str]:
        """Extract search criteria from natural language.

        Example:
            "find python scripts tagged docker" -> {"keyword": "python", "tag": "docker"}

        Args:
            query: Natural language search query
            timeout: Request timeout in seconds

        Returns:
            Dictionary with optional keys: keyword, tag, command_contains
        """
        prompt = f"""Extract search parameters from this query as JSON.
Return ONLY valid JSON with these optional keys: keyword, tag, command_contains

Query: {query}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100,
                timeout=timeout,
            )
            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except Exception:
            return {}

    def parse_file_path(self, query: str, timeout: float = 5.0) -> str | None:
        """Extract file path from request like 'read config.json'.

        Args:
            query: Natural language request with file path
            timeout: Request timeout in seconds

        Returns:
            Extracted file path or None
        """
        prompt = f"""Extract ONLY the file path from this request. Return just the path, nothing else.

Request: {query}

Path:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=50,
                timeout=timeout,
            )
            path = response.choices[0].message.content.strip().strip('"\'')
            if path and not path.lower().startswith("no "):
                return path
        except Exception:
            pass
        return None

    def parse_command_intent(
        self, query: str, timeout: float = 5.0
    ) -> dict[str, str]:
        """Extract action and target from a command request.

        Example:
            "list all python files" -> {"action": "list", "target": "python files"}

        Args:
            query: Natural language command
            timeout: Request timeout in seconds

        Returns:
            Dictionary with action and target keys
        """
        prompt = f"""Extract the action and target from this command as JSON.
Return ONLY valid JSON with keys: action, target

Command: {query}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=80,
                timeout=timeout,
            )
            content = response.choices[0].message.content.strip()

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except Exception:
            return {}
