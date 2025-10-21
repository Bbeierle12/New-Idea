"""OpenAI-compatible REST client with tool-call scaffolding."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests

from ..infra.logger import Logger
from .settings import SettingsService


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Return the OpenAI-compatible payload for this message."""
        payload: Dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.name:
            payload["name"] = self.name
        if self.tool_call_id:
            payload["tool_call_id"] = self.tool_call_id
        if self.metadata:
            payload.update(self.metadata)
        return payload

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dictionary used for chat history snapshots."""
        data = {
            "role": self.role,
            "content": self.content,
            "name": self.name,
            "tool_call_id": self.tool_call_id,
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "ChatMessage":
        """Build a message from a serialized snapshot."""
        return ChatMessage(
            role=str(payload.get("role", "assistant")),
            content=payload.get("content"),
            name=payload.get("name"),
            tool_call_id=payload.get("tool_call_id"),
            metadata=payload.get("metadata", {}) or {},
        )


class LLMClient:
    """Minimal OpenAI-compatible client."""

    def __init__(
        self,
        settings: SettingsService,
        logger: Logger,
        session: Optional[requests.Session] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        backoff: float = 1.0,
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._session = session or requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff = backoff
        self._call_timestamps: deque[float] = deque()

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request to the configured endpoint."""
        config = self._settings.get()
        
        # API key is optional for local models (e.g., Ollama)
        # Only check if base_url suggests it's a remote service
        if not config.api_key and "localhost" not in config.base_url and "127.0.0.1" not in config.base_url:
            raise RuntimeError("API key is not configured yet.")

        # Enforce rate limiting before making the request
        self._enforce_rate_limit(config.llm_rate_limit_per_minute)

        payload: Dict[str, Any] = {
            "model": config.model,
            "messages": [message.to_payload() for message in messages],
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        
        # Only add Authorization header if API key is provided
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        backoff = self._backoff
        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                self._logger.info("llm_request", url=url, model=config.model, attempt=str(attempt))
                response = self._session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                data = response.json()
                self._logger.info("llm_response", id=str(data.get("id", "unknown")))
                
                # Record successful call timestamp for rate limiting
                self._call_timestamps.append(time.time())
                
                return data
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                self._logger.warning(
                    "llm_retry",
                    error=f"{type(exc).__name__}: {exc}",
                    attempt=str(attempt),
                )
                if attempt == self._max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
        if last_error:
            raise last_error
        raise RuntimeError("LLM request failed unexpectedly")

    def chat_stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Send a streaming chat completion request.
        
        Args:
            messages: Chat messages to send
            tools: Available tools
            tool_choice: Tool selection strategy
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            on_token: Callback invoked for each content token received
            
        Returns:
            Complete response dict with aggregated content and tool calls
        """
        config = self._settings.get()
        
        # API key is optional for local models (e.g., Ollama)
        if not config.api_key and "localhost" not in config.base_url and "127.0.0.1" not in config.base_url:
            raise RuntimeError("API key is not configured yet.")

        # Enforce rate limiting before making the request
        self._enforce_rate_limit(config.llm_rate_limit_per_minute)

        payload: Dict[str, Any] = {
            "model": config.model,
            "messages": [message.to_payload() for message in messages],
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        
        # Only add Authorization header if API key is provided
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        self._logger.info("llm_stream_request", url=url, model=config.model)
        
        try:
            response = self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
                stream=True,
            )
            response.raise_for_status()
            
            # Record successful call timestamp for rate limiting
            self._call_timestamps.append(time.time())
            
            # Aggregate the streaming response
            aggregated_content = ""
            aggregated_tool_calls: List[Dict[str, Any]] = []
            tool_calls_buffer: Dict[int, Dict[str, Any]] = {}
            response_id = None
            finish_reason = None
            usage_data = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line_str = line.decode("utf-8")
                if not line_str.startswith("data: "):
                    continue
                    
                data_str = line_str[6:]  # Remove "data: " prefix
                if data_str.strip() == "[DONE]":
                    break
                    
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                
                if not response_id:
                    response_id = chunk.get("id")
                
                choices = chunk.get("choices", [])
                if not choices:
                    # Check for usage data in final chunk
                    if "usage" in chunk:
                        usage_data = chunk["usage"]
                    continue
                    
                delta = choices[0].get("delta", {})
                finish_reason = choices[0].get("finish_reason")
                
                # Handle content tokens
                if "content" in delta and delta["content"]:
                    token = delta["content"]
                    aggregated_content += token
                    if on_token:
                        on_token(token)
                
                # Handle tool calls
                if "tool_calls" in delta:
                    for tc_delta in delta["tool_calls"]:
                        index = tc_delta.get("index", 0)
                        if index not in tool_calls_buffer:
                            tool_calls_buffer[index] = {
                                "id": tc_delta.get("id", ""),
                                "type": tc_delta.get("type", "function"),
                                "function": {
                                    "name": "",
                                    "arguments": "",
                                },
                            }
                        
                        # Accumulate function data
                        if "function" in tc_delta:
                            fn_delta = tc_delta["function"]
                            if "name" in fn_delta:
                                tool_calls_buffer[index]["function"]["name"] += fn_delta["name"]
                            if "arguments" in fn_delta:
                                tool_calls_buffer[index]["function"]["arguments"] += fn_delta["arguments"]
                        
                        # Update ID if present
                        if "id" in tc_delta and tc_delta["id"]:
                            tool_calls_buffer[index]["id"] = tc_delta["id"]
            
            # Convert tool calls buffer to list
            if tool_calls_buffer:
                aggregated_tool_calls = [
                    tool_calls_buffer[i] for i in sorted(tool_calls_buffer.keys())
                ]
            
            # Build final response matching OpenAI format
            result: Dict[str, Any] = {
                "id": response_id or "unknown",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": config.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": aggregated_content or None,
                        },
                        "finish_reason": finish_reason or "stop",
                    }
                ],
            }
            
            if aggregated_tool_calls:
                result["choices"][0]["message"]["tool_calls"] = aggregated_tool_calls
            
            if usage_data:
                result["usage"] = usage_data
            
            self._logger.info("llm_stream_complete", id=response_id or "unknown")
            return result
            
        except (requests.RequestException, ValueError) as exc:
            self._logger.error(
                "llm_stream_error",
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    def _enforce_rate_limit(self, limit: Optional[int]) -> None:
        """Enforce rate limiting using a sliding window algorithm.
        
        Args:
            limit: Maximum number of requests allowed per minute. If None, no limit is enforced.
        """
        if not limit:
            return
        
        now = time.time()
        window = 60.0  # 60 seconds = 1 minute
        
        # Remove timestamps outside the current window
        while self._call_timestamps and now - self._call_timestamps[0] >= window:
            self._call_timestamps.popleft()
        
        # If we've hit the limit, wait until the oldest call falls out of the window
        if len(self._call_timestamps) >= limit:
            sleep_time = window - (now - self._call_timestamps[0])
            if sleep_time > 0:
                self._logger.info(
                    "rate_limit_sleep",
                    seconds=f"{sleep_time:.2f}",
                    limit=str(limit),
                )
                time.sleep(sleep_time)
                # Clean up timestamps again after sleeping
                now = time.time()
                while self._call_timestamps and now - self._call_timestamps[0] >= window:
                    self._call_timestamps.popleft()
