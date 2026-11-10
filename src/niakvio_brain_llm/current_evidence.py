"""Evidence-only causal signatures for provider runtime reverse diagnostics.

Signatures summarize current observed response *structure*, not raw URLs,
payloads, historical guesses, playable streams or permission to mutate.
Every signature is a hypothesis classification until code, playback and
content identity have been proven against exact current source bytes.
"""
from __future__ import annotations

from typing import Any

STAGES = frozenset({
    "search", "detail", "episode", "player", "source", "media",
    "content_lookup", "resolve", "redirect",
})
HTTP_BLOCKED = frozenset({401, 403, 429, 503})


def _rows(value: Any, limit: int) -> list[dict[str, Any]]:
    return [row for row in value[:limit] if isinstance(row, dict)] if isinstance(value, list) else []


def current_causal_signatures(live: dict[str, Any] | None) -> dict[str, Any]:
    """Describe *which* causal observation is available without guessing fixes.

    Input is the already-sanitized current-live-context projection. The output
    has no host, URL, ID, title, episode name, response or arbitrary text.
    """
    data = live if isinstance(live, dict) else {}
    network = _rows(data.get("network_evidence"), 12)
    fixtures = _rows(data.get("fixture_evidence"), 8)
    failed_count = sum(
        row.get("streamsPlayable") == 0
        for row in fixtures
        if type(row.get("streamsPlayable")) is int
    )
    available_stages = sorted({
        str(row["stage"]) for row in network
        if str(row.get("stage") or "") in STAGES
    })
    kind_counts = {"html": 0, "json": 0, "binary": 0, "other": 0}
    signals: list[str] = []
    def add(code: str) -> None:
        if code not in signals and len(signals) < 4:
            signals.append(code)

    for row in network:
        shape = row.get("response_structure")
        shape = shape if isinstance(shape, dict) else {}
        kind = str(shape.get("kind") or "")
        kind_counts[kind if kind in kind_counts else "other"] += 1
        status = row.get("status")
        if type(status) is int and status in HTTP_BLOCKED:
            add("http_origin_rejection_or_throttle")
        graphql = shape.get("graphql")
        if isinstance(graphql, dict) and kind == "json":
            error_count = graphql.get("errorCount")
            if type(error_count) is int and error_count > 0:
                add("graphql_response_errors")
            if graphql.get("dataState") == "null" or (
                isinstance(graphql.get("nullRoots"), list) and graphql["nullRoots"]
            ):
                add("graphql_null_result")
        announced = row.get("announced_players")
        if type(announced) is int and announced > 0 and failed_count:
            add("announced_player_unresolved")
        media = row.get("media_observation")
        if isinstance(media, dict) and media.get("signature") in {"mp4", "hls", "mpegts"} and failed_count:
            add("terminal_media_observed_but_unverified")

    if not network and failed_count:
        add("no_observed_provider_network")
    elif failed_count and not signals and network:
        add("network_observed_no_terminal_proof")
    # Labels below describe the next evidence to inspect; none is an edit
    # prescription, trusted domain, safety override, or media identity proof.
    next_probe = {
        "no_observed_provider_network": "compare_exact_bytes_deep_vs_nuvio_invocation",
        "graphql_response_errors": "compare_current_query_fields_and_variables",
        "graphql_null_result": "verify_episode_identity_and_response_shape",
        "http_origin_rejection_or_throttle": "separate_waf_transport_from_provider_parse",
        "announced_player_unresolved": "trace_player_links_to_terminal_bytes",
        "terminal_media_observed_but_unverified": "inspect_duration_headers_and_identity",
        "network_observed_no_terminal_proof": "locate_last_executed_stage_and_parser",
    }
    return {
        "network_events": len(network),
        "failed_fixtures": failed_count,
        "observed_stages": available_stages,
        "response_kinds": {key: value for key, value in kind_counts.items() if value},
        "signals": signals,
        "next_evidence": [next_probe[s] for s in signals if s in next_probe],
        "proof_authority": False,
        "publication_authority": False,
        "media_identity_verified": False,
    }
