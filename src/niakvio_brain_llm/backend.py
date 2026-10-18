from __future__ import annotations

import json
import time
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
    prefill_prompt: bool = False

    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": max(128, int(self.max_tokens)),
            "cache_prompt": True,
            "messages": messages,
        }
        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "niakvio_force_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        deadline = time.monotonic() + max(1, int(self.timeout_seconds))

        def invoke(body: dict[str, Any]) -> dict[str, Any]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("local model request deadline exhausted")
            request = Request(
                self.base_url.rstrip("/") + "/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=max(1.0, remaining)) as response:
                return json.loads(response.read().decode("utf-8"))

        if self.prefill_prompt:
            # Evaluate/cache the exact chat prefix with one generated token, then
            # spend the remaining deadline on the real constrained generation.
            # The next identical request can reuse the same prefix if this call
            # times out after prefill, which is useful for bounded Force retries.
            invoke({
                "model": self.model,
                "temperature": 0.0,
                "max_tokens": 1,
                "cache_prompt": True,
                "messages": messages,
            })

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
            try:
                value = invoke(fallback)
            except HTTPError as fallback_exc:
                body = ""
                try:
                    body = fallback_exc.read(1600).decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                # Never expose prompt/private memory; only the bounded server
                # error payload is retained, with URL/credential shapes redacted.
                import re
                body = re.sub(r"https?://[^\\s\"']+", "<url>", body)
                body = re.sub(
                    r"(?i)(authorization|cookie|token|secret|password|api[_-]?key)[^,}]{0,180}",
                    r"\\1:<omitted>",
                    body,
                )
                raise RuntimeError(
                    f"llama.cpp fallback HTTP {fallback_exc.code}: {body[:1200]}"
                ) from fallback_exc
        choice = value["choices"][0]
        finish_reason = str(choice.get("finish_reason") or "").strip().casefold()
        if finish_reason in {"length", "max_tokens"}:
            raise RuntimeError("local model completion truncated by max_tokens")
        return str(choice["message"]["content"])

@dataclass(slots=True)
class HostedResponsesBackend:
    """Opt-in hosted model using the OpenAI Responses API.

    Never automatically selected from a public guidance trigger. Callers must
    explicitly provision an API key and enforce their private-data boundary.
    No server-side response retention or tools are requested.
    """

    api_key: str
    model: str = "gpt-6.1-sol"
    timeout_seconds: int = 120
    max_tokens: int = 2048
    reasoning_effort: str = "medium"

    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        if not self.api_key or not self.api_key.strip():
            raise RuntimeError("hosted backend requires an API key")
        if self.model not in {"gpt-6.1-sol", "gpt-6-astra"}:
            raise ValueError("unapproved hosted model identifier")
        if self.reasoning_effort not in {"low", "medium", "high"}:
            raise ValueError("unsupported bounded hosted reasoning effort")
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": system,
            "input": user,
            "store": False,
            "reasoning": {"effort": self.reasoning_effort},
            "max_output_tokens": max(1024, min(8192, int(self.max_tokens))),
        }
        if response_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "niakvio_force_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        # Fail closed: HTTP/auth/schema errors must not trigger an unguarded
        # provider-code fallback or include secret request headers in logs.
        try:
            with urlopen(request, timeout=max(10, min(300, int(self.timeout_seconds)))) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"hosted model HTTP {exc.code}") from None
        if result.get("status") != "completed":
            raise RuntimeError("hosted model returned an incomplete response")
        chunks: list[str] = []
        for output in result.get("output") or []:
            if not isinstance(output, dict) or output.get("type") != "message":
                continue
            for part in output.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    chunks.append(str(part.get("text") or ""))
        content = "".join(chunks)
        if not content.strip():
            raise RuntimeError("hosted model returned no visible text")
        return content


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
