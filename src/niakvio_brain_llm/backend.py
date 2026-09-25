from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError
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
    temperature: float = 0.0
    max_tokens: int = 1024

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
            "max_tokens": max(128, int(self.max_tokens)),
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

        def invoke(body: dict[str, Any]) -> dict[str, Any]:
            request = Request(
                self.base_url.rstrip("/") + "/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            value = invoke(payload)
        except HTTPError as exc:
            # llama.cpp versions differ in the JSON-Schema subset accepted by
            # response_format. Production safety does not depend on that server
            # feature: BrainPlanner reparses and validates the proposal, causal
            # prior, mutation policy and mutation guards locally. Retry only
            # schema-rejection (HTTP 400), never transport/auth/server failures.
            if exc.code != 400 or not response_schema:
                raise
            fallback = dict(payload)
            fallback.pop("response_format", None)
            value = invoke(fallback)
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
