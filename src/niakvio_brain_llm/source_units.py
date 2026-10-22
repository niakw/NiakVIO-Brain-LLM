from __future__ import annotations

import re

def javascript_function_end(text: str, start: int) -> int:
    """Return the exclusive end of one named JS function using balanced braces.

    Compact provider runtimes frequently keep registration/IIFE statements after
    the final named helper, so next-function-or-EOF is not a safe function
    boundary. Scan from the declaration opening brace while ignoring strings,
    comments and regex literals. This remains a structural locator only; the
    resulting mutation is still uniqueness-checked and node syntax-checked.
    """
    open_brace = text.find("{", max(0, int(start)))
    if open_brace < 0:
        return -1
    depth = 0
    i = open_brace
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    regex = False
    regex_class = False
    prev_sig = ""
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if ch in "\r\n":
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
            i += 1
            continue
        if regex:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "[":
                regex_class = True
            elif ch == "]" and regex_class:
                regex_class = False
            elif ch == "/" and not regex_class:
                regex = False
                prev_sig = "/"
            i += 1
            continue
        if ch == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if ch in {"'", '"', chr(96)}:
            quote = ch
            i += 1
            continue
        if ch == "/":
            if not prev_sig or prev_sig in "([{:;,=!?&|+-*%^~<>" or re.search(r"\b(?:return|throw|case|yield)\s*$", text[max(open_brace, i - 20):i]):
                regex = True
                regex_class = False
                escaped = False
                i += 1
                continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
            if depth < 0:
                return -1
        if not ch.isspace():
            prev_sig = ch
        i += 1
    return -1

