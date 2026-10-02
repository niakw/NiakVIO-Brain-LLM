import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload, build_prompt_payload

class PromptingTests(unittest.TestCase):
    def test_large_context_is_bounded(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="unknown",
            provider_context={
                "authored_module": "x" * 20000,
                "override": "y" * 10000,
            },
            observations=[{"blob": "z" * 10000}],
        )
        payload = build_prompt_payload(request, [{
            "failure_class": "unknown",
            "strategy": "inspect",
            "lesson": "l" * 10000,
        }])
        self.assertLess(len(payload["request"]["provider_context"]["authored_module"]), 2300)
        self.assertLess(len(payload["request"]["observations"][0]["blob"]), 700)
        self.assertLess(len(payload["retrieved_experiences"][0]["lesson"]), 700)

    def test_variant_coverage_focus_survives_advisor_and_force_compaction(self):
        source = (
            "function quality(f){return /(2160|1080|720|480)p/.test(f);} "
            "async function resolve(links){var out=[];for(var i=0;i<links.length;i++){"
            "var rows=source(links[i]);for(var j=0;j<rows.length;j++)out.push(rows[j]);"
            "if(out.length>=4)break}return out;}"
        )
        coverage = {
            "schemaVersion": 1,
            "riskKind": "variant-coverage-truncation",
            "risk": "high",
            "mechanisms": ["global_output_quota_break"],
            "dimensions": ["quality", "source"],
            "qualityHints": ["2160p", "1080p", "720p", "480p"],
            "repairHint": "enumerate variants before final cap",
            "proofAuthority": False,
        }
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": source,
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "runtime_variant_coverage": coverage,
            },
        )
        advisor = build_prompt_payload(
            request, [], [],
            {"target_layer": "provider", "confidence": 0.96},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(
            advisor["request"]["provider_context"]["runtime_variant_coverage"]["risk"],
            "high",
        )
        force = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(force["runtime_variant_coverage"]["riskKind"], "variant-coverage-truncation")
        self.assertIn("out.length", force["structural_focus"])
        self.assertIn("quality", force["structural_focus"])
        windows = force["new_bloc_target"]["source_windows"]
        self.assertTrue(any("out.length>=4" in row["source"] for row in windows), windows)

    def test_current_structure_and_dynamic_fanout_survive_force_compaction(self):
        source = (
            "async function resolve(q){var out=[];"
            "for(var i=0;i<players.length&&i<8;i++){out.push(players[i]);}"
            "return out;}"
        )
        structure = {
            "role": "current-provider-structure-observation",
            "proofAuthority": False,
            "executionAuthority": False,
            "originHost": "current.example",
            "routes": [{
                "path": "/wp-json/demo/v1/resolve",
                "method": "UNKNOWN",
                "role": "player-resolver",
            }],
            "requestKeys": ["tmdb", "type", "year", "pid"],
            "fanout": {
                "groupCount": 2,
                "groupVariantCounts": [10, 9],
                "indexedVariantCount": 19,
                "languageLabels": ["VF", "VOSTFR"],
            },
        }
        dynamic = {
            "provider": "demo",
            "fanout": {
                "movie": {
                    "announcedVariantCandidates": 7,
                    "streamsReturned": 2,
                    "state": "returned-subset",
                }
            },
        }
        coverage = {
            "riskKind": "variant-coverage-truncation",
            "risk": "high",
            "dimensions": ["player", "server", "source"],
            "proofAuthority": False,
        }
        request = RepairRequest(
            provider_id="demo",
            failure_class="variant_coverage_gap",
            status="FULL OK",
            observations=[
                {"source": "census_current", "value": {"status": "FULL OK"}},
                {"source": "runtime-variant-coverage-current", "value": coverage},
                {"source": "targeted-regression-current", "value": {"debugStages": {}}},
                {"source": "census-sharded-current", "value": dynamic},
                {"source": "current-provider-structure", "value": structure},
            ],
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "route_contract": {
                    "currentObservedRoutes": ["/wp-json/demo/v1/resolve"],
                    "currentObservedRoutesAuthority": "observation-only",
                },
                "current_structure_evidence": structure,
                "runtime_variant_coverage": coverage,
            },
        )

        advisor = build_prompt_payload(
            request,
            [],
            [],
            {"target_layer": "provider", "confidence": 0.96},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(
            advisor["request"]["provider_context"]["current_structure_evidence"]["originHost"],
            "current.example",
        )

        force = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "variant"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(force["current_provider_structure"]["originHost"], "current.example")
        self.assertEqual(
            force["current_provider_structure"]["fanout"]["indexedVariantCount"],
            19,
        )
        sources = [row.get("source") for row in force["current_observations"]]
        self.assertEqual(sources[:3], [
            "current-provider-structure",
            "census-sharded-current",
            "runtime-variant-coverage-current",
        ])
        sharded = next(
            row["value"] for row in force["current_observations"]
            if row.get("source") == "census-sharded-current"
        )
        self.assertEqual(sharded["fanout"]["movie"]["announcedVariantCandidates"], 7)
        self.assertEqual(sharded["fanout"]["movie"]["streamsReturned"], 2)
        self.assertEqual(sharded["fanout"]["movie"]["state"], "returned-subset")

    def test_high_confidence_prior_uses_focused_rag_budget(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={"override": "{}"},
        )
        experiences = [
            {"experience_id": str(i), "failure_class": "chain_terminal_gap", "lesson": "x"}
            for i in range(5)
        ]
        documents = [
            {"path": f"d{i}.md", "text": "x" * 2000}
            for i in range(4)
        ]
        payload = build_prompt_payload(
            request,
            experiences,
            documents,
            {"target_layer": "provider", "confidence": 0.96},
            {"allow_mutations": True},
        )
        self.assertEqual(payload["context_budget"]["mode"], "focused")
        self.assertEqual(len(payload["retrieved_experiences"]), 1)
        self.assertEqual(len(payload["retrieved_documents"]), 0)

    def test_route_contract_survives_compaction_and_force_prompt(self):
        route_contract = {
            "capability": "html_scraper",
            "learnedRoutes": ["/?s={query}"],
            "candidateRoutes": ["/detail/{slug}", "/player/{id}"],
            "plans": [{
                "kind": "search_request_plan",
                "route": "/?s={query}",
                "method": "GET",
                "role": "catalog-search",
                "lanes": ["movie", "tv"],
            }],
            "canonicalPreference": [{
                "owner": "route",
                "route": "/?s={query}",
                "lanes": ["movie", "tv"],
            }],
        }
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            provider_context={
                "route_contract": route_contract,
                "runtime_template_prior": {
                    "mode": "reuse_recognized_family_renderer",
                    "template": "scripts/provider_patches/stremio_json_runtime_common.py",
                    "reuseBeforeNovelBloc": True,
                },
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": (
                        "async function detail(q){return await fetch('/detail/'+q.slug);} "
                        "async function resolve(q){return await detail(q);}"
                    ),
                },
            },
        )
        advisor = build_prompt_payload(
            request,
            [],
            [],
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(
            advisor["request"]["provider_context"]["route_contract"]["learnedRoutes"],
            ["/?s={query}"],
        )
        self.assertTrue(
            advisor["request"]["provider_context"]["runtime_template_prior"]["reuseBeforeNovelBloc"]
        )
        force = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(force["current_route_contract"]["plans"][0]["method"], "GET")
        self.assertEqual(
            force["runtime_template_prior"]["template"],
            "scripts/provider_patches/stremio_json_runtime_common.py",
        )
        self.assertTrue(
            force["runtime_template_policy"]["reuse_shared_or_current_template_before_novel_bloc"]
        )
        self.assertEqual(
            force["current_route_contract"]["canonicalPreference"][0]["route"],
            "/?s={query}",
        )

    def test_exact_runtime_template_compacts_chain_force_to_causal_pair(self):
        source = (
            "function search(q){return q;} "
            "function detail(q){return q.detail;} "
            "function player(q){return q.player;} "
            "function terminal(q){return q.media;} "
            "function resolve(q){var d=detail(q);var p=player(d);return terminal(p);}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            provider_context={
                "preferredRuntimeMutationSource": source,
                "runtimeMutationFilename": "providers/demo.js",
                "runtime_template_prior": {
                    "mode": "reuse_current_provider_runtime_skeleton",
                    "template": "scripts/provider_patches/demo_runtime_v1.py",
                    "reuseBeforeNovelBloc": True,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        target = payload["new_bloc_target"]
        self.assertLessEqual(len(target["source_windows"]), 1)
        self.assertLessEqual(
            sum(len(row["source"]) for row in target["source_windows"]),
            550,
        )
        self.assertLessEqual(len(target["editable_units"]), 2)
        self.assertTrue(
            payload["runtime_template_policy"]["exact_materialized_runtime_bloc_first"]
        )
        self.assertFalse(payload["runtime_template_policy"]["provider_bloc_is_last_resort"])

    def test_force_mutation_context_prefers_registered_bloc_sources(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={
                "published_bundle": {
                    "filename": "providers/demo--nuvio--abc.js",
                    "version": "1.2.3",
                    "providerBlocks": [
                        {"id": "PROVIDER.DEMO.RUNTIME.V1", "source": "P" * 10000},
                        {"id": "PROVIDER.DEMO.CONFIG.V1", "source": "Q" * 10000},
                        {"id": "PROVIDER.DEMO.EXTRA.V1", "source": "R" * 10000},
                    ],
                },
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "A" * 10000,
                    "scripts/provider_patches/demo_extra_v1.py": "B" * 10000,
                    "scripts/provider_patches/demo_third_v1.py": "C" * 10000,
                },
                "authored_module": "M" * 10000,
                "override": "O" * 10000,
                "hub": "H" * 10000,
            },
        )
        payload = build_prompt_payload(
            request,
            [{"experience_id": "1", "lesson": "x" * 1000}],
            [{"path": "doc.md", "text": "x" * 4000}],
            {"target_layer": "provider", "confidence": 0.95},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        context = payload["request"]["provider_context"]
        # Advisor context keeps one representative Bloc; exact multi-Bloc source
        # remains available to compact Force and deterministic validation.
        self.assertEqual(len(context["published_bundle"]["providerBlocks"]), 1)
        self.assertLessEqual(
            max(len(v["source"]) for v in context["published_bundle"]["providerBlocks"]),
            3412,
        )
        self.assertEqual(context["published_bundle"]["filename"], "providers/demo--nuvio--abc.js")
        self.assertEqual(len(context["registered_patch_sources"]), 1)
        self.assertLessEqual(max(len(v) for v in context["registered_patch_sources"].values()), 2212)
        self.assertLess(len(context["authored_module"]), 1000)
        self.assertLess(len(context["override"]), 1000)
        self.assertLess(len(context["hub"]), 550)
        self.assertEqual(len(payload["retrieved_experiences"]), 1)
        self.assertEqual(payload["retrieved_documents"], [])

    def test_force_prompt_is_provider_local_and_drops_rag_bulk(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            observations=[{"stage": "player", "blob": "Z" * 5000} for _ in range(8)],
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "HEAD\nfunction resolve(){var media=null; if(!media)return null;}\n" + ("A" * 10000) + "\nvar tailValue=1;\nTAIL",
                    "scripts/provider_patches/demo_extra_v1.py": "B" * 10000,
                },
                "authored_module": "M" * 10000,
                "override": "O" * 10000,
                "published_bundle": {"providerBlocks": [{"source": "P" * 10000}]},
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal_media_extractor_with_playback_validation"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(payload["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(payload["mutation_target"]["path"], "scripts/provider_patches/demo_runtime_v1.py")
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2600)
        joined = "\n".join(row["source"] for row in windows)
        self.assertIn("HEAD", joined)
        self.assertIn("function resolve()", joined)
        self.assertTrue(payload["output_contract"]["source_windows_are_exact_current_bytes"])
        self.assertEqual(len(payload["current_observations"]), 2)
        self.assertNotIn("retrieved_experiences", payload)
        self.assertNotIn("retrieved_documents", payload)
        self.assertNotIn("published_bundle", payload)
        self.assertEqual(payload["output_contract"]["file_edit_format"], "unit_id_replace")
        self.assertTrue(payload["output_contract"]["unit_id_selects_exact_current_bytes"])
        self.assertTrue(payload["output_contract"]["model_never_copies_find_bytes"])
        self.assertTrue(payload["output_contract"]["brain_resolves_window_occurrence_by_causal_focus"])
        self.assertTrue(payload["output_contract"]["brain_resolves_global_anchor_uniqueness"])
        self.assertEqual([row["id"] for row in windows], [f"w{i}" for i in range(1, len(windows) + 1)])
        self.assertTrue(all(isinstance(row.get("focus_offset"), int) for row in windows))
        source = request.provider_context["registered_patch_sources"]["scripts/provider_patches/demo_runtime_v1.py"]
        self.assertTrue(all(row["source"] == source[row["offset"]:row["end_offset"]] for row in windows))
        units = payload["mutation_target"]["editable_units"]
        self.assertTrue(units)
        self.assertTrue(all(row["source"] == source[row["offset"]:row["end_offset"]] for row in units))
        self.assertTrue(all(len(row["source"]) <= 700 for row in units))
        self.assertTrue(any(row.get("kind") == "statement_sequence" for row in units))
        self.assertTrue(any(row["source"].count(";") >= 2 for row in units if row.get("kind") == "statement_sequence"))
        self.assertTrue(all(row["window_id"] in {window["id"] for window in windows} for row in units))


    def test_force_edit_units_include_bounded_causal_function(self):
        source = (
            "function noise(){return 1;} "
            "function confirmLinks(page){var raw=page.url;if(!raw)return [];return [raw];} "
            "function unrelated(){return 2;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        units = payload["mutation_target"]["editable_units"]
        causal = [row for row in units if row.get("kind") == "function_unit"]
        self.assertTrue(causal)
        self.assertIn("function confirmLinks", causal[0]["source"])
        self.assertNotIn("function unrelated", causal[0]["source"])
        self.assertLessEqual(len(causal[0]["source"]), 1800)

    def test_force_edit_units_include_generic_named_causal_function_bodies(self):
        source = (
            "function a(page){var href=\'/confirm/\'+page.id;return href;} "
            "function b(page){var path='/internal/'+page.id;return path;} "
            "function unrelated(){return 2;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        functions = [
            row["source"]
            for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        self.assertGreaterEqual(len(functions), 2)
        self.assertTrue(any("function a(" in row and "/confirm/" in row for row in functions))
        self.assertTrue(any("function b(" in row and "/internal/" in row for row in functions))
        # Causal keyword matches rank first, but generic complete functions remain
        # available as a bounded invention fallback instead of being hidden.
        self.assertIn("function a(", functions[0])
        self.assertIn("function b(", functions[1])

    def test_force_edit_units_keep_generic_function_fallback_when_taxonomy_has_no_name_match(self):
        source = (
            "function a(page){var next=page.next;return next;} "
            "function b(page){var rows=page.rows||[];return rows;} "
            "function c(){return 3;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
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
        functions = [
            row
            for row in payload["new_bloc_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        self.assertTrue(functions)
        self.assertTrue(any("function a(" in row.get("source", "") for row in functions))
        self.assertTrue(any("function b(" in row.get("source", "") for row in functions))

    def test_force_edit_units_follow_direct_runtime_callees(self):
        source = (
            "function request(a){return a;} "
            "function candidateDownloadLinks(page){return [page.url];} "
            "function modLinks(url){return fetch(url).then(r=>r.text());} "
            "function resolve(args){var q=request(args);var rows=candidateDownloadLinks(q);"
            "return rows.length?modLinks(rows[0]):[];} "
            "function unrelated(){return 1;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
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
        functions = [
            row
            for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        joined = "\n".join(row.get("source", "") for row in functions)
        self.assertEqual(len(functions), 2)
        self.assertIn("function resolve(", joined)
        self.assertIn("function modLinks(", joined)
        self.assertNotIn("function unrelated(", joined)
        self.assertTrue(
            any(
                row.get("reason") == "causal_call_neighbor"
                and "function modLinks(" in row.get("source", "")
                for row in functions
            )
        )

    def test_route_gap_prefers_detail_selector_as_causal_pair(self):
        source = (
            "function req(a){return a;} "
            "async function meta(q){return q;} "
            "async function detail(q,m){var page=await fetch('/?s='+m.title);"
            "var cards=classBlocks(await page.text(),'movie-card');return cards[0]||null;} "
            "function classBlocks(html,cls){return [];} "
            "async function resolve(args){var q=req(args),m=await meta(q);return await detail(q,m);} "
            "function unrelated(){return 1;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
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
        functions = [
            row
            for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        joined = "\n".join(row.get("source", "") for row in functions)
        self.assertEqual(len(functions), 2)
        self.assertIn("function resolve(", joined)
        self.assertIn("function detail(", joined)
        self.assertNotIn("function unrelated(", joined)

    def test_force_targeted_observation_keeps_shape_hint_and_summarizes_network(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            observations=[{
                "source": "targeted-regression-current",
                "value": {
                    "debugStages": {"movie": "provider_network_zero_result"},
                    "statuses": {"movie": "no_streams"},
                    "sampleTitles": {"movie": ["Sinners"]},
                    "structureHints": [
                        "movie:classes=movie-card,movie-card-title,movie-card-format"
                    ],
                    "network": {
                        "movie": [{
                            "host": "provider.example",
                            "status": 200,
                            "shape": {"kind": "html", "anchors": 42},
                        }],
                    },
                },
            }],
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": (
                        "async function detail(q){return await fetch(q.url);} "
                        "async function resolve(a){return await detail({url:a[0]});}"
                    ),
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "route"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        observation = payload["current_observations"][0]
        value = observation["value"]
        self.assertIn("structureHints", value)
        self.assertIn("movie-card-title", value["structureHints"][0])
        self.assertEqual(value["networkSummary"], ["movie:provider.example:200:html"])
        self.assertNotIn("network", value)

    def test_force_edit_units_follow_second_hop_runtime_callees(self):
        source = (
            "function jsonGet(url){return fetch(url).then(r=>r.json());} "
            "function currentRows(value){return value&&value.streams||[];} "
            "function current(q){return jsonGet(q.url).then(value=>currentRows(value));} "
            "function legacy(q){return [];} "
            "function resolve(args){var q={url:String(args&&args[0]||'')};"
            "return current(q).then(rows=>rows.length?rows:legacy(q));} "
            "function unrelated(){return 1;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        functions = [
            row
            for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        joined = "\n".join(row.get("source", "") for row in functions)
        self.assertIn("function resolve(", joined)
        self.assertIn("function current(", joined)
        self.assertTrue(
            any(
                row.get("reason") == "causal_call_neighbor_depth2"
                and (
                    "function currentRows(" in row.get("source", "")
                    or "function jsonGet(" in row.get("source", "")
                )
                for row in functions
            )
        )

    def test_force_edit_units_reserve_second_hop_when_depth1_is_crowded(self):
        source = (
            "function terminalParser(value){return value&&value.streams||[];} "
            "function current(q){return fetch(q.url).then(r=>r.json()).then(terminalParser);} "
            "function legacy(q){return [];} "
            "function decorate(rows){return rows;} "
            "function metrics(rows){return rows;} "
            "function resolve(args){var q={url:String(args&&args[0]||'')};"
            "return current(q).then(rows=>decorate(metrics(rows.length?rows:legacy(q))));} "
            "function unrelated(){return 1;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        functions = [
            row
            for row in payload["mutation_target"]["editable_units"]
            if row.get("kind") == "function_unit"
        ]
        self.assertEqual(len(functions), 4)
        self.assertTrue(
            any(
                row.get("reason") == "causal_call_neighbor_depth2"
                and "function terminalParser(" in row.get("source", "")
                for row in functions
            ),
            functions,
        )

    def test_force_validation_retry_uses_focused_context(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction internalLink(){ return '/internal/' + id; }\n"
            + "J" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            observations=[
                {
                    "stage": "force_validation_feedback",
                    "reason": "syntax_error",
                    "correction_index": 1,
                    "instruction": "previous edit rejected",
                },
                {"stage": "player", "blob": "Z" * 5000},
                {"stage": "detail", "blob": "Y" * 5000},
            ],
            census_prior={"blob": "C" * 5000},
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "validated_reference_patterns": [
                    {
                        "provider": "healthy",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:x",
                        "technical_features": ["fetch", "iframe", "m3u8"],
                        "snippet": "S" * 1100,
                    }
                ],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2200)
        self.assertLessEqual(len(windows), 2)
        self.assertEqual(len(payload["current_observations"]), 1)
        self.assertEqual(payload["current_observations"][0]["stage"], "force_validation_feedback")
        self.assertEqual(payload["validated_reference_patterns"], [])
        self.assertEqual(payload["census_prior"], {})
        self.assertEqual(payload["output_contract"]["validation_retry_context"], "focused")

    def test_force_prompt_targets_family_relevant_middle_windows(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction internalLink(){ return '/internal/' + id; }\n"
            + "J" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        units = payload["mutation_target"]["editable_units"]
        joined = "\n".join(row["source"] for row in windows)
        unit_source = "\n".join(row["source"] for row in units)
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2000)
        self.assertLessEqual(len(windows), 2)
        self.assertIn("confirmLink", joined)
        self.assertIn("internalLink", unit_source)
        self.assertTrue(all("...<middle-clipped>..." not in row["source"] for row in windows))

    def test_force_initial_prompt_keeps_one_same_provider_field_evidence_excerpt(self):
        request = RepairRequest(
            provider_id="moviebox",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            supported_types=["movie", "tv"],
            allowed_mutations=["provider_patch"],
            provider_context={
                "registered_patch_sources":{
                    "scripts/provider_patches/moviebox_runtime_v1.py":"function resolveCandidate(u){return u}"
                },
            },
            observations=[{"source":"census_current","value":{"debugStages":{"movie":"provider_network_zero_result"}}}],
        )
        documents = [
            {
                "kind":"document",
                "path":"automation/USER-PROVIDER-EVIDENCE-LEDGER.md",
                "heading":"Exact provider route captures relevant to unresolved providers",
                "role":"field_evidence",
                "authority":92,
                "text":"MovieBox manual positive: moviebox.yachts -> provider-local API -> terminal master.m3u8 HTTP 200.",
            },
            {
                "kind":"document",
                "path":"automation/USER-PROVIDER-EVIDENCE-LEDGER.md",
                "heading":"Other",
                "role":"field_evidence",
                "authority":92,
                "text":"AllWish manual positive: unrelated provider route.",
            },
        ]
        payload = build_force_prompt_payload(
            request,
            {"target_layer":"provider","confidence":0.9,"strategy_prior":"terminal"},
            {"allow_mutations":True,"allowed_scopes":["provider_patch"]},
            documents,
        )
        self.assertEqual(len(payload["provider_field_evidence"]), 1)
        row = payload["provider_field_evidence"][0]
        self.assertIn("MovieBox manual positive", row["text"])
        self.assertFalse(row["proof_authority"])
        self.assertTrue(row["must_revalidate_current_network"])
        self.assertTrue(payload["field_evidence_policy"]["same_provider_only"])

    def test_force_initial_prompt_is_compact_and_keeps_one_optional_reference(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            observations=[
                {"stage": "player", "blob": "Z" * 5000},
                {"stage": "detail", "blob": "Y" * 5000},
                {"stage": "other", "blob": "X" * 5000},
            ],
            census_prior={"blob": "C" * 5000},
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "validated_reference_patterns": [
                    {
                        "provider": "healthy-a",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:a",
                        "technical_features": ["fetch", "iframe", "m3u8"],
                        "snippet": "S" * 1100,
                    },
                    {
                        "provider": "healthy-b",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:b",
                        "technical_features": ["fetch", "json"],
                        "snippet": "R" * 1100,
                    },
                ],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2600)
        self.assertLessEqual(len(windows), 3)
        self.assertEqual(len(payload["current_observations"]), 2)
        self.assertEqual(len(payload["validated_reference_patterns"]), 1)
        self.assertLessEqual(len(payload["validated_reference_patterns"][0]["snippet"]), 520)
        self.assertEqual(payload["census_prior"], {})
        self.assertEqual(payload["output_contract"]["validation_retry_context"], "compact_initial")

    def test_force_prompt_references_are_optional_and_novelty_allowed(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": "function resolve(){return null;}",
                "validated_reference_patterns": [{
                    "provider": "healthy",
                    "status": "FULL OK",
                    "source_kind": "registered_bloc:x",
                    "technical_features": ["fetch", "iframe", "m3u8"],
                    "snippet": "async function resolvePlayer(){return '<ROUTE>';}",
                    "proof_authority": False,
                    "copy_policy": "pattern_reference_only",
                    "novelty_allowed": True,
                }],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(len(payload["validated_reference_patterns"]), 1)
        self.assertTrue(payload["reference_policy"]["may_adapt_combine_or_ignore"])
        self.assertTrue(payload["reference_policy"]["novel_provider_local_mechanisms_allowed"])
        self.assertTrue(payload["reference_policy"]["reference_is_not_proof"])

    def test_provider_bloc_prefers_registered_runtime_block_over_generic_base(self):
        generic = (
            "function _routeKind(route){return 'ignore';} "
            "function genericExtract(text){return [];}"
        )
        dedicated = (
            "function classBlocks(html){return html?['card']:[];} "
            "async function detail(q,m){var cards=classBlocks(m.html);return cards[0]||null;} "
            "async function resolve(args){return detail(args,{html:'x'});}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
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
        target = payload["new_bloc_target"]
        joined = "\n".join(
            str(row.get("source") or "")
            for row in target.get("editable_units") or []
        )
        windows = "\n".join(
            str(row.get("source") or "")
            for row in target.get("source_windows") or []
        )
        self.assertIn("function detail(", joined + windows)
        self.assertIn("function resolve(", joined + windows)
        self.assertNotIn("_routeKind", joined + windows)

    def test_route_force_focuses_html_class_prefix_collisions(self):
        source = (
            "function classBlocks(html,cls){return html.indexOf(cls)>=0?[html]:[];} "
            "function classText(html,cls){return classBlocks(html,cls).join(' ');} "
            "async function detail(q){var cards=classBlocks(q.html,'movie-card');"
            "return cards.find(x=>classText(x,'movie-card-title'))||null;} "
            "async function resolve(args){return detail({html:String(args&&args[0]||'')});}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            observations=[{
                "source": "targeted-regression-current",
                "value": {
                    "structureHints": [
                        "movie:classes=movie-card,movie-card-format,movie-card-content,movie-card-title;markers=download"
                    ],
                },
            }],
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
        self.assertIn("movie-card", payload["structural_focus"])
        self.assertIn("classblocks", payload["structural_focus"])
        units = payload["mutation_target"]["editable_units"]
        joined = "\n".join(str(row.get("source") or "") for row in units)
        self.assertIn("function classBlocks(", joined)
        self.assertIn("function classText(", joined)
        self.assertNotIn("function detail(", joined)
        self.assertNotIn("function resolve(", joined)
        self.assertEqual(len(units), 2)
    def test_force_prompt_preserves_all_allowed_mutation_scopes(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "const x = 1;",
                },
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": "function resolve(){ return 1; }",
            },
        )
        scopes = ["provider_bloc", "provider_data", "provider_js", "provider_patch"]
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": scopes},
        )
        self.assertEqual(payload["mutation_policy"]["allowed_scopes"], scopes)
        self.assertEqual(payload["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(payload["new_bloc_target"]["scope"], "provider_bloc")

        patch_only = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(patch_only["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(patch_only["new_bloc_target"], {})

        bloc_only = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(bloc_only["mutation_target"], {})
        self.assertEqual(bloc_only["new_bloc_target"]["scope"], "provider_bloc")

    def test_brain_owned_required_tests_are_hidden_from_model(self):
        payload = build_prompt_payload(
            RepairRequest(provider_id="demo", failure_class="chain_terminal_gap"),
            [],
            [],
            {"target_layer": "provider", "confidence": 0.96},
            {
                "allow_mutations": False,
                "force_abstain": True,
                "required_tests": [
                    "replay_proven_chain_to_terminal_media",
                    "validate_media_signature_duration_and_identity",
                ],
            },
        )
        self.assertNotIn("required_tests", payload["mutation_policy"])
        self.assertTrue(payload["verification_owned_by_brain"])

if __name__ == "__main__":
    unittest.main()
