import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.planner import BrainPlanner, COMPACT_FORCE_SYSTEM_PROMPT, _compact_edit_to_mutation, _deterministic_structural_force_mutation, _resolve_structured_anchor
from niakvio_brain_llm.prompting import _force_source_windows, build_force_prompt_payload

class PlannerTests(unittest.TestCase):
    def test_compact_force_function_unit_prompt_requires_body_only_rewrite(self):
        self.assertIn("kind=function_unit", COMPACT_FORCE_SYSTEM_PROMPT)
        self.assertIn("NEW FUNCTION BODY ONLY", COMPACT_FORCE_SYSTEM_PROMPT)
        self.assertIn("Never emit or rename the function declaration/name/signature", COMPACT_FORCE_SYSTEM_PROMPT)

    def test_deterministic_class_prefix_collision_synthesizes_exact_boundary(self):
        source = r'''function classBlocks(html,cls){var esc=cls;var re=new RegExp("\\b"+esc+"\\b");return re.test(html)?[html]:[]} async function resolve(args){return []}'''
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            observations=[{
                "source":"targeted-regression-current",
                "value":{"structureHints":[
                    "movie:classes=movie-card,movie-card-format,movie-card-content"
                ]},
            }],
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationFilename":"providers/demo.js",
                "runtimeMutationSource":source,
            },
        )
        mutation = _deterministic_structural_force_mutation(
            request,
            {"allow_mutations":True,"allowed_scopes":["provider_bloc"]},
        )
        self.assertIsNotNone(mutation)
        self.assertEqual(mutation["scope"], "provider_bloc")
        self.assertEqual(mutation["family"], "exact_class_token_boundary")
        updated = source.replace(mutation["find"], mutation["replace"], 1)
        self.assertIn('(?![-_])', updated)
        self.assertNotEqual(updated, source)

    def test_deterministic_mixed_nested_class_container_uses_balanced_extraction(self):
        source = r'''function classBlocks(html,cls){var esc=cls.replace(/[-/\\^$*+?.()|[\]{}]/g,"\\    def test_structural_focus_unit_id_resolves_to_same_dom_helper(self):
"),re=new RegExp("<(?:div|article|li|a)\\b[^>]*class=[\"'][^\"']*\\b"+esc+"\\b[^\"']*[\"'][^>]*>","gi"),starts=[],m;while((m=re.exec(html||""))!==null)starts.push({at:m.index,tag:m[0]});var out=[];for(var i=0;i<starts.length;i++){var end=i+1<starts.length?starts[i+1].at:Math.min(String(html||"").length,starts[i].at+12000);out.push({html:String(html||"").slice(starts[i].at,end),tag:starts[i].tag})}return out} async function resolve(args){return []}'''
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            observations=[{
                "source":"targeted-regression-current",
                "value":{"structureHints":[
                    "movie:classFacts=[movie-card;count=12;selfHref=1;nestedAnchors=24;"
                    "tags=a,div,span;signals=movie,series,year]"
                    "[movie-card-format;count=12;selfHref=0;nestedAnchors=0;"
                    "tags=span;signals=movie,series]"
                ]},
            }],
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationFilename":"providers/demo.js",
                "runtimeMutationSource":source,
            },
        )
        mutation = _deterministic_structural_force_mutation(
            request,
            {"allow_mutations":True,"allowed_scopes":["provider_bloc"]},
        )
        self.assertIsNotNone(mutation)
        self.assertEqual(mutation["scope"], "provider_bloc")
        self.assertEqual(mutation["family"], "balanced_class_container")
        updated = source.replace(mutation["find"], mutation["replace"], 1)
        self.assertIn("closeRe", updated)
        self.assertIn('(?![-_])', updated)
        self.assertNotIn("starts[i+1].at", updated)
        self.assertNotEqual(updated, source)

    def test_structural_focus_unit_id_resolves_to_same_dom_helper(self):
        source = (
            "function classBlocks(html,cls){return html.indexOf(cls)>=0?[html]:[]} "
            "function classText(html,cls){return classBlocks(html,cls).join(' ')} "
            "async function detail(q){var cards=classBlocks(q.html,'movie-card');"
            "return cards.find(x=>classText(x,'movie-card-title'))||null} "
            "async function resolve(args){return detail({html:String(args&&args[0]||'')})}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            observations=[{
                "source":"targeted-regression-current",
                "value":{"structureHints":[
                    "movie:classes=movie-card,movie-card-format,movie-card-content,movie-card-title"
                ]},
            }],
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationFilename":"providers/demo.js",
                "runtimeMutationSource":source,
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer":"provider","confidence":0.96,"strategy_prior":"route"},
            {"allow_mutations":True,"allowed_scopes":["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if "function classBlocks(" in str(row.get("source") or "")
        )
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope":"provider_bloc",
                "family":"exact_class_token_boundary",
                "unit_id":unit["id"],
                "replace":"return html===cls?[html]:[];",
            },
        )
        self.assertIsNotNone(mutation)
        class_blocks = "function classBlocks(html,cls){return html.indexOf(cls)>=0?[html]:[]}"
        resolve = "async function resolve(args){return detail({html:String(args&&args[0]||'')})}"
        self.assertIn(mutation["find"], class_blocks)
        self.assertNotIn(mutation["find"], resolve)
        self.assertNotEqual(mutation["find"], mutation["replace"])

    def test_accepts_bounded_provider_mutation(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "terminal extractor changed",
            "strategy": "repair_terminal_extractor",
            "confidence": 0.8,
            "target_layer": "provider",
            "evidence": ["player reached"],
            "mutations": [{
                "scope": "provider_js",
                "operation": "unified_diff",
                "path": "engine_v2/providers/demo.mjs",
                "diff": "--- a/engine_v2/providers/demo.mjs\n+++ b/engine_v2/providers/demo.mjs\n@@\n-old\n+new"
            }],
            "experiment": {"route_policy":"owned_plus_peer","recipe_policy":"current_plus_provider","role_order":["player","source","api"],"terminal_only":True,"response_salvage":True,"max_depth":5,"max_pages":20,"max_embeds":24,"max_recipe_passes":4},
            "tests": ["known positive movie"],
            "abstain": False,
            "abstain_reason": ""
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="unknown_provider_gap",
                status="CHAIN REACHED",
                provider_context={"authored_module": "export default {}"},
            )
        )
        self.assertEqual(proposal.strategy, "repair_terminal_extractor")
        self.assertEqual(proposal.target_layer, "provider")
        self.assertEqual(proposal.experiment["route_policy"],"owned_plus_peer")
        self.assertTrue(proposal.experiment["terminal_only"])

    def test_rejects_forbidden_scope(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "guess",
            "strategy": "rewrite_core",
            "confidence": 0.9,
            "target_layer": "provider",
            "mutations": [{"scope": "core", "operation": "rewrite"}],
            "tests": ["retest"],
            "abstain": False,
            "abstain_reason": ""
        })
        with self.assertRaises(ValueError):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(provider_id="demo", failure_class="unknown")
            )

    def test_non_provider_layer_is_bounded_abstention(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "transport environment differs",
            "strategy": "compare_browser_native_residential_profiles_without_provider_mutation",
            "confidence": 0.9,
            "target_layer": "harness",
            "evidence": ["browser/native differ"],
            "mutations": [],
            "tests": ["native transport replay"],
            "abstain": True,
            "abstain_reason": "provider mutation is not justified"
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(provider_id="demo", failure_class="transport_environment_gap")
        )
        self.assertTrue(proposal.abstain)
        self.assertEqual(proposal.target_layer, "harness")

    def test_compact_force_wire_synthesizes_full_validated_proposal(self):
        response = json.dumps({
            "edit": {
                "scope": "provider_data",
                "operation": "set",
                "path": "notes",
                "value": "current terminal extractor repair",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                provider_context={"override": {"notes": "old"}},
            ),
            compact_force=True,
        )
        self.assertEqual(proposal.provider_id, "demo")
        self.assertEqual(proposal.target_layer, "provider")
        self.assertEqual(proposal.strategy, "terminal_media_extractor_with_playback_validation")
        self.assertEqual(len(proposal.mutations), 1)
        self.assertFalse(proposal.abstain)
        self.assertTrue(proposal.tests)

    def test_compact_force_file_edit_compiles_to_validated_unified_diff(self):
        source = "def resolver():\n    return 'old'\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "    return 'old'",
                "replace": "    return 'new'",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                provider_context={
                    "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                    "registered_patch_sources": {
                        "scripts/provider_patches/demo_runtime_v1.py": source,
                    },
                },
            ),
            compact_force=True,
        )
        mutation = proposal.mutations[0]
        self.assertEqual(mutation["scope"], "provider_patch")
        self.assertEqual(mutation["operation"], "unified_diff")
        self.assertIn("--- scripts/provider_patches/demo_runtime_v1.py", mutation["diff"])
        self.assertIn("-    return 'old'", mutation["diff"])
        self.assertIn("+    return 'new'", mutation["diff"])

    def test_compact_force_window_resolves_global_non_unique_anchor(self):
        filler = "/*" + ("x" * 5000) + "*/\n"
        source = (
            "function first(){return null;}\n"
            + filler
            + "function confirmTarget(){return null;}\n"
            + filler
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_js",
                "path": "engine_v2/providers/demo.mjs",
                "window_id": "w1",
                "find": "return null;",
                "replace": "return media;",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                provider_context={"authored_module": source},
                allowed_mutations=["provider_js"],
            ),
            compact_force=True,
        )
        mutation = proposal.mutations[0]
        self.assertEqual(mutation["scope"], "provider_js")
        self.assertIn("function confirmTarget(){return media;}", mutation["diff"])
        self.assertNotIn("-function first(){return null;}", mutation["diff"])

    def test_structured_anchor_relocates_exact_find_from_wrong_window(self):
        source = (
            "function confirmTarget(){return null;}\n"
            + "/*" + ("x" * 14000) + "*/\n"
            + "function terminalTarget(){const media='ok';return media;}\n"
        )
        find = "return media;"
        windows = _force_source_windows(source, "chain_terminal_gap")
        self.assertGreaterEqual(len(windows), 2)
        wrong = next(
            row for row in windows
            if find not in str(row.get("source") or "")
        )
        resolved_find, resolved_replace = _resolve_structured_anchor(
            source,
            "chain_terminal_gap",
            str(wrong["id"]),
            find,
            "return resolvedMedia;",
            max_find=320,
            max_replace=1200,
        )
        self.assertIn("return media;", resolved_find)
        self.assertIn("return resolvedMedia;", resolved_replace)

    def test_compact_force_window_focus_resolves_repeated_local_find(self):
        source = (
            "function first(){return null;}\n"
            "function helper(){return null;}\n"
            "function confirmTarget(){return null;}\n"
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_js",
                "path": "engine_v2/providers/demo.mjs",
                "window_id": "w1",
                "find": "return null;",
                "replace": "return media;",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                provider_context={"authored_module": source},
                allowed_mutations=["provider_js"],
            ),
            compact_force=True,
        )
        mutation = proposal.mutations[0]
        self.assertIn("function confirmTarget(){return media;}", mutation["diff"])
        self.assertNotIn("-function first(){return null;}", mutation["diff"])
        self.assertNotIn("-function helper(){return null;}", mutation["diff"])

    def test_compact_force_rejects_partial_function_copy_before_minimization(self):
        source = (
            "function resolve(url){const score=55;if(score<55)return null;return url;}\n"
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_js",
                "path": "engine_v2/providers/demo.mjs",
                "window_id": "w1",
                "find": "function resolve(url){const score=55;if(score<55",
                "replace": "function resolve(url){const score=55;if(score<60",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "structurally incomplete"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="route_proven_gap",
                    status="ROUTE PROVEN",
                    provider_context={"authored_module": source},
                    allowed_mutations=["provider_js"],
                ),
                compact_force=True,
            )

    def test_compact_force_file_edit_rejects_non_unique_find(self):
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "return None",
                "replace": "return []",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "exactly once"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": "def a():\n    return None\ndef b():\n    return None\n",
                        },
                    },
                ),
                compact_force=True,
            )

    def test_compact_force_file_edit_rejects_truncated_source_fragment(self):
        source = (
            'function A(v){return v;}\n'
            'function H(v){return v;}\n'
            'async function T(v){return fetch(v,{redirect:"follow"});}\n'
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": source.strip(),
                "replace": 'ollow"});',
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "truncated|helper function"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="provider_transport_gap",
                    status="NO PROOF",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": source,
                        },
                    },
                    allowed_mutations=["provider_patch"],
                ),
                compact_force=True,
            )

    def test_compact_force_provider_bloc_rejects_partial_function_anchor(self):
        source = "function resolve(url) { const x = normalize(url); return x; }\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_bloc",
                "family": "terminal_resolution",
                "find": "function resolve(url) { const x = normalize(url);",
                "replace": "function resolve(url) { return normalize(url); }",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "syntax validation|structurally incomplete|removes live binding"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "runtimeMutationFilename": "providers/demo.js",
                        "runtimeMutationSource": source,
                    },
                    allowed_mutations=["provider_bloc"],
                ),
                compact_force=True,
            )

    def test_compact_force_provider_bloc_allows_novel_helper(self):
        source = "var seed=1;\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_bloc",
                "family": "novel_terminal_helper",
                "find": "var seed=1;",
                "replace": "function freshHelper(){return 2;}\nvar seed=freshHelper();",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                provider_context={
                    "runtimeMutationFilename": "providers/demo.js",
                    "runtimeMutationSource": source,
                },
                allowed_mutations=["provider_bloc"],
            ),
            compact_force=True,
        )
        self.assertFalse(proposal.abstain)
        self.assertEqual(proposal.mutations[0]["scope"], "provider_bloc")
        self.assertIn("function freshHelper()", proposal.mutations[0]["replace"])

    def test_compact_force_provider_bloc_rejects_helper_collision(self):
        source = "function existing(){return 1;}\nvar seed=1;\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_bloc",
                "family": "novel_terminal_helper",
                "find": "var seed=1;",
                "replace": "function existing(){return 2;}\nvar seed=existing();",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "helper name collides"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "runtimeMutationFilename": "providers/demo.js",
                        "runtimeMutationSource": source,
                    },
                    allowed_mutations=["provider_bloc"],
                ),
                compact_force=True,
            )

    def test_compact_force_rejects_neighbor_helper_absorption(self):
        source = (
            'async function T(url){return fetch(url);}\n'
            'function Q(a){return a;}\n'
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "async function T(url){return fetch(url);}",
                "replace": "async async function T(url){return fetch(url);}function Q(a){return a;}",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "neighboring helper|duplicated|structurally incomplete|syntax validation"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="provider_transport_gap",
                    status="NO PROOF",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": (
                                "WRAPPER = r'''\\n"
                                + source
                                + "'''\\n"
                            ),
                        },
                    },
                    allowed_mutations=["provider_patch"],
                ),
                compact_force=True,
            )

    def test_compact_force_rejects_boolean_neutral_noop(self):
        source = (
            "WRAPPER = r'''\n"
            "function detail(m){if(!m||m.score<55)return null;return m;}\n"
            "'''\n"
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "function detail(m){if(!m||m.score<55)return null;return m;}",
                "replace": "function detail(m){if(!m||m.score<55 || 0)return null;return m;}",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "no-op|boolean-neutral"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": source,
                        },
                    },
                    allowed_mutations=["provider_patch"],
                ),
                compact_force=True,
            )

    def test_compact_force_file_edit_preserves_single_helper_signature(self):
        source = (
            "WRAPPER = r\'\'\'\n"
            "function T(v){return fetch(v);}\n"
            "\'\'\'\n"
        )
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "function T(v){return fetch(v);}",
                "replace": "function T(v){return fetch(v,{redirect:'follow'});}",
            },
            "abstain_reason": "",
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="NO PROOF",
                provider_context={
                    "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                    "registered_patch_sources": {
                        "scripts/provider_patches/demo_runtime_v1.py": source,
                    },
                },
                allowed_mutations=["provider_patch"],
            ),
            compact_force=True,
        )
        self.assertEqual(proposal.mutations[0]["scope"], "provider_patch")

    def test_compact_force_file_edit_rejects_boolean_identity_noop(self):
        source = "function detail(best,score,min){if(!best||score<min)return null;return best;}\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "if(!best||score<min)return null;",
                "replace": "if(!best||score<min || 0)return null;",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "no-op"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": source,
                        },
                    },
                    allowed_mutations=["provider_patch"],
                ),
                compact_force=True,
            )

    def test_compact_force_provider_bloc_rejects_boolean_identity_noop(self):
        source = "function ok(v){return v&&true;}\n"
        response = json.dumps({
            "edit": {
                "scope": "provider_bloc",
                "family": "terminal_boolean_guard",
                "find": "return v;",
                "replace": "return v&&true;",
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "no-op"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "runtimeMutationFilename": "providers/demo.js",
                        "runtimeMutationSource": "function ok(v){return v;}\n",
                    },
                    allowed_mutations=["provider_bloc"],
                ),
                compact_force=True,
            )

    def test_compact_force_file_edit_rejects_oversized_replace(self):
        response = json.dumps({
            "edit": {
                "scope": "provider_patch",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "find": "return 'old'",
                "replace": "x" * 641,
            },
            "abstain_reason": "",
        })
        with self.assertRaisesRegex(ValueError, "oversized"):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(
                    provider_id="demo",
                    failure_class="chain_terminal_gap",
                    status="CHAIN REACHED",
                    provider_context={
                        "registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                        "registered_patch_sources": {
                            "scripts/provider_patches/demo_runtime_v1.py": "def a():\n    return 'old'\n",
                        },
                    },
                ),
                compact_force=True,
            )

    def test_compact_force_function_unit_allows_bounded_large_replacement(self):
        path = "scripts/provider_patches/demo_runtime_v1.py"
        source = 'WRAPPER = """function a(page){var href="/confirm/"+page.id;return href;}"""\n'
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            provider_context={"registered_patch_sources": {path: source}},
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        unit = next(
            row for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        )
        replacement = (
            'function a(page){/*' + ("x" * 700)
            + '*/var href="/confirm/"+page.id;return href;}'
        )
        self.assertGreater(len(replacement), 640)
        mutation = _compact_edit_to_mutation(
            request,
            {"scope": "provider_patch", "path": path, "unit_id": unit["id"], "replace": replacement},
        )
        self.assertEqual(mutation["scope"], "provider_patch")
        self.assertIn("unified_diff", mutation["operation"])

    def test_compact_force_provider_patch_preserves_function_envelope_for_body_only_rewrite(self):
        path = "scripts/provider_patches/demo_runtime_v1.py"
        old_body = "var x=page.url;" + ("x=x;" * 90) + "return x;"
        source = 'WRAPPER = """function resolve(page){' + old_body + '}"""\n'
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            provider_context={"registered_patch_sources": {path: source}},
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        unit = next(
            row for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit" and "function resolve(" in row.get("source", "")
        )
        self.assertGreater(len(unit["source"]), 320)
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_patch",
                "path": path,
                "unit_id": unit["id"],
                "replace": "var rows=page.rows||[];return rows.length?rows[0]:page.url;",
            },
        )
        self.assertEqual(mutation["scope"], "provider_patch")
        self.assertIn("function resolve(page)", mutation["diff"])
        self.assertNotIn('WRAPPER = """var rows=', mutation["diff"])

    def test_provider_bloc_validation_uses_preferred_runtime_source(self):
        generic = "function _routeKind(route){return 'ignore';}"
        dedicated = "async function detail(page){return page.cards&&page.cards[0]||null;}"
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": generic,
                "preferredRuntimeMutationBlockId": "PROVIDER.DEMO.RUNTIME.V1",
                "preferredRuntimeMutationSource": dedicated,
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit" and "function detail(" in row.get("source", "")
        )
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_bloc",
                "family": "search_result_selection",
                "unit_id": unit["id"],
                "replace": "const cards=page.cards||[];return cards.find(Boolean)||null;",
            },
        )
        self.assertIn("page.cards", mutation["find"])
        self.assertIn("cards.find(Boolean)", mutation["replace"])
        self.assertNotIn("_routeKind", mutation["find"])
        self.assertNotIn("return 'ignore'", mutation["find"])

    def test_compact_force_provider_bloc_allows_bounded_full_function_invention(self):
        source = "function resolve(page){return page.url;}"
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/demo.js",
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        )
        replacement = "function resolve(page){/*" + ("x" * 1250) + "*/return page.url;}"
        self.assertGreater(len(replacement), 1200)
        self.assertLessEqual(len(replacement), 1800)
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_bloc",
                "family": "terminal_resolution",
                "unit_id": unit["id"],
                "replace": replacement,
            },
        )
        self.assertEqual(mutation["scope"], "provider_bloc")
        self.assertEqual(mutation["operation"], "upsert")
        self.assertIn("function resolve(page)", mutation["replace"])

    def test_compact_force_provider_bloc_preserves_selected_function_envelope_for_body_only_rewrite(self):
        source = "async function resolve(page){return page.url;}"
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/demo.js",
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        )
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_bloc",
                "family": "terminal_resolution",
                "unit_id": unit["id"],
                "replace": "const finalUrl=page.finalUrl||page.url;return finalUrl;",
            },
        )
        updated = source.replace(mutation["find"], mutation["replace"], 1)
        self.assertNotEqual(updated, source)
        self.assertTrue(updated.startswith("async function resolve(page){"))
        self.assertIn("const finalUrl=page.finalUrl||page.url;return finalUrl;", updated)
        self.assertTrue(updated.rstrip().endswith("}"))

    def test_compact_force_provider_bloc_rejects_network_return_collapse(self):
        source = (
            "async function request(url, options){"
            "const response=await fetch(url,options||{});"
            "if(!response.ok)throw new Error('http');"
            "return response;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="provider_transport_gap",
            status="NO PROOF",
            allowed_mutations=["provider_bloc"],
            provider_context={"runtimeMutationSource": source, "runtimeMutationFilename": "providers/demo.js"},
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "transport"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit" and "function request(" in row.get("source", "")
        )
        with self.assertRaisesRegex(ValueError, "discard request return semantics"):
            _compact_edit_to_mutation(
                request,
                {
                    "scope": "provider_bloc",
                    "family": "transport_response",
                    "unit_id": unit["id"],
                    "replace": "if(row.referer&&!headers.Referer)headers.Referer=recipe.referer;",
                },
            )

    def test_compact_force_provider_patch_rejects_async_signature_drift(self):
        source = (
            "function req(a){return {tmdbId:String(a&&a[0]||'')}} "
            "async function resolve(a){var q=req(a);return q.tmdbId?[]:[];}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            allowed_mutations=["provider_patch"],
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        unit = next(
            row for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit" and "function req(" in row.get("source", "")
        )
        with self.assertRaisesRegex(ValueError, "declaration/signature changed"):
            _compact_edit_to_mutation(
                request,
                {
                    "scope": "provider_patch",
                    "path": "scripts/provider_patches/demo_runtime_v1.py",
                    "unit_id": unit["id"],
                    "replace": "async function req(a){return {tmdbId:String(a&&a[0]||'')}}",
                },
            )

    def test_compact_force_provider_bloc_normalizes_explicit_helper_wrapper_to_selected_unit(self):
        source = "function _routeKind(route){return route;} function _extractUrls(text){return [text];}"
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/demo.js",
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit" and "_routeKind" in row.get("source", "")
        )
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_bloc",
                "family": "route_proven_gap",
                "unit_id": unit["id"],
                "replace": "function _extractUrls(text){return [text,text];}",
            },
        )
        updated = source.replace(mutation["find"], mutation["replace"], 1)
        self.assertIn("function _routeKind(route){return [text,text];}", updated)
        self.assertIn("function _extractUrls(text){return [text];}", updated)

    def test_compact_force_provider_bloc_allows_long_exact_function_anchor(self):
        old_body = "a" * 900
        new_body = "b" * 900
        source = 'function resolve(page){const marker="' + old_body + '";return page.url;}'
        replacement = 'function resolve(page){const marker="' + new_body + '";return page.finalUrl||page.url;}'
        self.assertGreater(len(source), 320)
        self.assertLessEqual(len(source), 1800)
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/demo.js",
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        unit = next(
            row for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        )
        mutation = _compact_edit_to_mutation(
            request,
            {
                "scope": "provider_bloc",
                "family": "terminal_resolution",
                "unit_id": unit["id"],
                "replace": replacement,
            },
        )
        self.assertEqual(mutation["scope"], "provider_bloc")
        self.assertGreater(len(mutation["find"]), 320)
        self.assertLessEqual(len(mutation["find"]), 1800)
        self.assertLessEqual(len(mutation["replace"]), 1800)

    def test_private_chat_document_reaches_planner_prompt(self):
        planner = BrainPlanner(
            StaticBackend("{}"),
            documents=DocumentStore([{
                "kind": "document",
                "document_id": "private-1",
                "source": "niakvio-private-chat",
                "private_memory": True,
                "proof_authority": False,
                "path": "conversations/c1/index.json",
                "heading": "architecture",
                "role": "private_chat_signal",
                "authority": 55,
                "text": "Movix api discovery gap current route and provider repair strategy",
            }]),
        )
        _, documents, _, _, user = planner._prepare(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                status="CHAIN REACHED",
            )
        )
        self.assertTrue(documents)
        self.assertEqual(documents[0]["source"], "niakvio-private-chat")
        self.assertIn("niakvio-private-chat", user)
        self.assertIn("Movix api discovery gap", user)

    def test_raw_proposal_skips_production_post_validation(self):
        response = json.dumps({
            "provider_id": "wrong-id",
            "diagnosis": "raw benchmark answer",
            "strategy": "wrong_strategy",
            "confidence": 0.5,
            "target_layer": "core",
            "evidence": [],
            "mutations": [],
            "tests": [],
            "abstain": False,
            "abstain_reason": ""
        })
        proposal = BrainPlanner(StaticBackend(response)).propose_raw(
            RepairRequest(provider_id="demo", failure_class="api_discovery_gap")
        )
        self.assertEqual(proposal.provider_id, "wrong-id")
        self.assertEqual(proposal.strategy, "wrong_strategy")

class PlannerGuardTests(unittest.TestCase):
    def test_force_rejects_removed_live_binding_and_pure_traversal_deletion(self):
        source = "function scan(text){const out=[];const normalized=_embeddedText(text);if(normalized)out.push(normalized);return out;}"
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={"runtimeMutationSource": source},
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer":"provider","confidence":0.96,"strategy_prior":"search_detail_player_terminal_traversal"},
            {"allow_mutations":True,"allowed_scopes":["provider_bloc"]},
        )
        units = payload["new_bloc_target"]["editable_units"]
        target = next(row for row in units if "normalized=_embeddedText" in row["source"] and "const out" in row["source"])
        with self.assertRaisesRegex(ValueError, "removes live binding|pure deletion|helper function declaration"):
            _compact_edit_to_mutation(
                request,
                {"scope":"provider_bloc","family":"url_extractor","unit_id":target["id"],"replace":"const out=[];"},
            )


if __name__ == "__main__":
    unittest.main()
