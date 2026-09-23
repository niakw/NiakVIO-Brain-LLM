#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import re
import subprocess
from pathlib import Path

SKIP_PREFIXES = (
    "tests/",
    ".git/",
)
SKIP_FILES = {
    "src/niakvio_brain_llm/private_chat_memory.py",
    "scripts/audit_public_repo_privacy.py",
}

TOKEN_PATTERNS = (
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b")),
    ("authorization_value", re.compile(r"(?i)authorization\s*[:=]\s*[^\s'\"$\{]{12,}")),
    ("password_value", re.compile(r"(?i)password\s*[:=]\s*[^\s'\"$\{]{8,}")),
    ("secret_value", re.compile(r"(?i)secret\s*[:=]\s*[^\s'\"$\{]{8,}")),
    ("api_key_value", re.compile(r"(?i)api[_-]?key\s*[:=]\s*[^\s'\"$\{]{8,}")),
)

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_FR = re.compile(r"(?<!\d)(?:\+33[ .-]?|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)")
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
HOME_PATH = re.compile(r"(?:/Users|/home)/([A-Za-z0-9._-]+)")

ALLOWED_EMAIL_SUFFIXES = (
    "@users.noreply.github.com",
)
ALLOWED_IPS = {
    "127.0.0.1",
    "0.0.0.0",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    ]


def public_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if str(address) in ALLOWED_IPS:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def main() -> int:
    findings: list[str] = []

    for path in tracked_files():
        raw = path.as_posix()
        if raw in SKIP_FILES or any(raw.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append(f"{raw}: potential {label}")

        for match in EMAIL.finditer(text):
            value = match.group(0)
            if not value.casefold().endswith(tuple(s.casefold() for s in ALLOWED_EMAIL_SUFFIXES)):
                findings.append(f"{raw}: potential email address")

        if PHONE_FR.search(text):
            findings.append(f"{raw}: potential French phone number")

        for match in IPV4.finditer(text):
            if public_ipv4(match.group(0)):
                findings.append(f"{raw}: potential public IPv4 address")

        for match in HOME_PATH.finditer(text):
            username = match.group(1)
            if username not in {"runner", "user", "USERNAME", "[REDACTED_USER]"}:
                findings.append(f"{raw}: potential personal home path")

    if findings:
        print("Public-repository privacy audit failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1

    print("Public-repository privacy audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
