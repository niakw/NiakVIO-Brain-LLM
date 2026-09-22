from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen

class ModelBackend(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str: ...

@dataclass(slots=True)
class LocalOpenAICompatibleBackend:
    """Local llama.cpp-style endpoint. No cloud API required."""

    base_url: str = "http://127.0.0.1:8080"
    model: str = "niakvio-local"
    timeout_seconds: int = 120
    temperature: float = 0.1

    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_schema:
            payload["response_format"] = {
                "type": "json_object",
                "schema": response_schema,
            }

        request = Request(
            self.base_url.rstrip("/") + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            value = json.loads(response.read().decode("utf-8"))
        return str(value["choices"][0]["message"]["content"])

@dataclass(slots=True)
class StaticBackend:
    response: str

    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        return self.response
