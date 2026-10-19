from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .nlp_fallback import NaturalLanguageIntentEngine
from .prompts import BAIZO_SYSTEM_PROMPT, TOOL_DEFINITIONS
from .tools import AGENT_TOOL_REGISTRY


class LLMClient:
    """Client for connecting Baizo to local or remote LLM endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("BAIZO_LLM_URL")
            or os.environ.get("VOLT_API_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or "http://localhost:11434/v1"
        )
        self.api_key = api_key or os.environ.get("BAIZO_LLM_KEY") or os.environ.get("OPENAI_API_KEY") or "none"
        self.model = model or os.environ.get("BAIZO_LLM_MODEL") or "llama3.2"
        self.fallback_engine = NaturalLanguageIntentEngine()

    def is_endpoint_reachable(self, timeout: float = 0.8) -> bool:
        """Quick health check to see if local LLM server is answering."""
        try:
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def query_with_tools(self, user_message: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Execute a user query, invoking tools if an LLM is active or falling back to local NLP."""
        if not self.is_endpoint_reachable():
            # Graceful local heuristic fallback
            reply, _ = self.fallback_engine.process(user_message)
            return reply

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": BAIZO_SYSTEM_PROMPT}
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
        }

        try:
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            choice = data["choices"][0]["message"]
            tool_calls = choice.get("tool_calls")

            if not tool_calls:
                return choice.get("content", "No response generated.")

            # Process tool calls
            messages.append(choice)
            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                args_str = tool_call["function"]["arguments"]
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}

                tool_func = AGENT_TOOL_REGISTRY.get(fn_name)
                if tool_func:
                    result = tool_func(**args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": json.dumps(result),
                    }
                )

            # Second turn to format final response
            payload["messages"] = messages
            payload.pop("tools", None)
            payload.pop("tool_choice", None)

            req2 = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req2, timeout=30.0) as resp2:
                data2 = json.loads(resp2.read().decode("utf-8"))
            return data2["choices"][0]["message"].get("content", "Done.")

        except Exception as exc:
            # If API call encounters an error, fall back to offline heuristic parser
            reply, _ = self.fallback_engine.process(user_message)
            return reply
