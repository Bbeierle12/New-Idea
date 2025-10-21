"""Summarize command history sessions using Gemma."""

from __future__ import annotations

from openai import OpenAI

from ..infra.history import CommandHistory


class SessionSummarizer:
    """Summarize what user accomplished in a session."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma:300m",
    ) -> None:
        """Initialize session summarizer.

        Args:
            base_url: Ollama API endpoint
            model: Model name (default: gemma:300m)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    def summarize_recent(
        self, history: CommandHistory, limit: int = 10, timeout: float = 8.0
    ) -> str:
        """Summarize recent commands in plain English.

        Args:
            history: Command history object
            limit: Number of recent commands to summarize
            timeout: Request timeout in seconds

        Returns:
            Plain English summary of the session
        """
        records = history.tail(limit)
        if not records:
            return "No commands executed yet."

        commands = "\n".join(f"- {r.command}" for r in records)

        prompt = f"""Summarize what the user did based on these commands. One paragraph only.

Commands:
{commands}

Summary:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "No summary available"

    def summarize_specific_commands(
        self, commands: list[str], timeout: float = 8.0
    ) -> str:
        """Summarize a specific list of commands.

        Args:
            commands: List of command strings
            timeout: Request timeout in seconds

        Returns:
            Plain English summary
        """
        if not commands:
            return "No commands to summarize."

        cmd_list = "\n".join(f"- {cmd}" for cmd in commands)

        prompt = f"""Summarize what these commands accomplish. One paragraph only.

Commands:
{cmd_list}

Summary:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "No summary available"

    def generate_session_title(
        self, history: CommandHistory, limit: int = 5, timeout: float = 5.0
    ) -> str:
        """Generate a short title for a command session.

        Args:
            history: Command history object
            limit: Number of recent commands to consider
            timeout: Request timeout in seconds

        Returns:
            Short title (3-5 words)
        """
        records = history.tail(limit)
        if not records:
            return "New Session"

        commands = "\n".join(f"- {r.command}" for r in records)

        prompt = f"""Generate a 3-5 word title for this command session.

Commands:
{commands}

Title:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "Command Session"
