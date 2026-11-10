"""Single authority for evidence-backed, provider-local FORCE mutation scope priority.

Shared by production batch planner and read-only model challenger. This chooses
which scope to TRY, never publication or playback authority.
"""
from __future__ import annotations

def select_force_scopes(request) -> list[str]:
    context = request.provider_context or {}
    allowed = set(request.allowed_mutations or [])
    scopes: list[str] = []
    failure_key = str(request.failure_class or "").strip().casefold().replace("-", "_")
    bloc_ready = (
        "provider_bloc" in allowed
        and bool(context.get("runtimeMutationSource"))
    )
    registered_patch_sources = (
        context.get("registered_patch_sources")
        if isinstance(context.get("registered_patch_sources"), dict)
        else {}
    )
    patch_ready = "provider_patch" in allowed and bool(registered_patch_sources)
    runtime_patch_ready = patch_ready and any(
        "NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1" in str(source)
        or "__niakvioProviderRuntimeResolverV1" in str(source)
        or (
            "MANAGED_FIX_ID" in str(source)
            and "PROVIDER." in str(source)
            and ".RUNTIME." in str(source)
        )
        for source in registered_patch_sources.values()
    )

    structural_gap = (
        failure_key in {
            "route_proven_gap",
            "chain_terminal_gap",
            "media_extraction_gap",
            "variant_coverage_gap",
        }
        or str(request.status or "").strip().upper() in {"ROUTE PROVEN", "CHAIN REACHED"}
    )

    runtime_template_prior = (
        context.get("runtime_template_prior")
        if isinstance(context.get("runtime_template_prior"), dict)
        else {}
    )
    template_first = bool(runtime_template_prior.get("reuseBeforeNovelBloc"))

    # Structural route/terminal failures should mutate the exact materialized
    # provider runtime Bloc first when one exists. The Python generator is a
    # larger authoring surface and proved much slower/noisier under 7B FORCE.
    # A template prior means "reuse this runtime skeleton", not "rewrite the
    # generator from scratch". Keep provider_patch only as a bounded fallback.
    if bloc_ready and structural_gap and template_first:
        scopes.append("provider_bloc")
    if runtime_patch_ready and structural_gap and not template_first:
        scopes.append("provider_patch")
    if bloc_ready and structural_gap and "provider_bloc" not in scopes:
        scopes.append("provider_bloc")

    if (
        patch_ready
        and "provider_patch" not in scopes
        and not (structural_gap and template_first)
    ):
        scopes.append("provider_patch")
    elif not patch_ready and "provider_js" in allowed and context.get("authored_module"):
        scopes.append("provider_js")
    elif (
        not patch_ready
        and not ("provider_js" in allowed and context.get("authored_module"))
        and "provider_data" in allowed
        and (context.get("override") or context.get("hub"))
    ):
        scopes.append("provider_data")

    if bloc_ready and "provider_bloc" not in scopes:
        scopes.append("provider_bloc")
    from niakvio_brain_llm.live_evidence import prioritize_domain_data
    return prioritize_domain_data(list(dict.fromkeys(scopes)), allowed, context)

