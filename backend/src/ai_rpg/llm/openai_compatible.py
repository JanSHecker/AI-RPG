from __future__ import annotations

import json
from typing import Any

import httpx

from ai_rpg.core.config import Settings


class OpenAICompatibleClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_completion(self, *, system_prompt: str, user_payload: dict) -> dict:
        if not self.settings.api_key:
            raise RuntimeError("Missing API key for OpenAI-compatible provider.")
        response = httpx.post(
            f"{self.settings.api_base.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.model,
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, default=str),
                    },
                ],
            },
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    def create_tool_call(self, *, system_prompt: str, user_payload: dict, tools: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.api_key:
            raise RuntimeError("Missing API key for OpenAI-compatible provider.")
        response = httpx.post(
            f"{self.settings.api_base.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, default=str),
                    },
                ],
                "tools": tools,
                "tool_choice": "required",
            },
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            call = tool_calls[0]
            return {
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"]["arguments"]),
            }

        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = str(content).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        if "name" in parsed and "arguments" in parsed:
            return parsed
        raise RuntimeError("Model response did not include a tool call.")
