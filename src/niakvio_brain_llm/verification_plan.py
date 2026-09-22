from __future__ import annotations

from typing import Any

STRATEGY_TESTS: dict[str, list[str]] = {
    "discover_api_from_current_page_and_bundles": [
        "probe_current_provider_page_and_bundles",
        "validate_discovered_provider_owned_api",
        "replay_known_positive_lane",
    ],
    "compare_browser_native_residential_profiles_without_provider_mutation": [
        "compare_browser_native_residential_profiles",
        "replay_same_route_same_identity_across_transports",
    ],
    "normalize_client_media_type_before_provider_capability_gate": [
        "replay_series_alias_before_network_gate",
        "run_cross_platform_capability_regression",
    ],
    "terminal_media_extractor_with_playback_validation": [
        "replay_proven_chain_to_terminal_media",
        "validate_media_signature_duration_and_identity",
    ],
    "search_detail_player_terminal_traversal": [
        "replay_proven_route",
        "traverse_search_detail_player_terminal",
        "validate_terminal_media_identity",
    ],
    "same_provider_candidate_program_replay": [
        "replay_same_provider_candidate_on_current_bytes",
        "validate_playback_and_identity",
    ],
    "proven_request_program_and_terminal_extraction": [
        "replay_provider_owned_request_program",
        "validate_terminal_media_identity",
    ],
}

def recommended_tests(
    strategy: str,
    *,
    target_layer: str,
    mutation_policy: dict[str, Any] | None = None,
) -> list[str]:
    tests = list(STRATEGY_TESTS.get(strategy) or [])
    policy = mutation_policy or {}

    if not tests and target_layer == "provider":
        tests = [
            "replay_provider_on_current_bytes",
            "validate_playback_identity_and_non_regression",
        ]
    elif not tests and target_layer == "core":
        tests = ["run_core_regression_matrix"]
    elif not tests and target_layer == "harness":
        tests = ["run_transport_profile_differential"]
    elif not tests and target_layer == "network":
        tests = ["replay_provider_owned_route_across_network_profiles"]

    if policy.get("force_abstain") and "collect_required_current_evidence" not in tests:
        tests.insert(0, "collect_required_current_evidence")

    return tests[:8]
