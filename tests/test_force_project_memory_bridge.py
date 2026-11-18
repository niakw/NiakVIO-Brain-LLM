"""Existing Markdown/chat RAG and executed experiments must reach FORCE.

This validates retrieval and prompt projection, not a real provider repair.
No private source text is persisted or printed by these tests.
"""
import json
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.retrieval import ExperienceStore


class ForceProjectMemoryBridgeTests(unittest.TestCase):
    def test_existing_md_and_private_chat_reach_compact_force_without_authority(self):
        provider = "sekai"
        documents = [{
            "kind": "document",
            "role": "brain_repair_architecture",
            "path": "BRAIN_REPAIR_ARCHITECTURE.md",
            "heading": "route_proven_gap",
            "authority": 96,
            "text": "Sekai route_proven_gap preserve player execution and verify terminal decoded media",
        }] + [
            {
                "kind": "document",
                "role": "durable_recovery_memory",
                "path": f"MEMORY.md#{i}",
                "heading": f"sekai route_proven_gap exact run {i}",
                "authority": 95,
                "text": "Sekai route_proven_gap no prior decoded playback and no publication proof",
            } for i in range(8)
        ] + [{
            "kind": "document",
            "document_id": "private-c1",
            "role": "private_chat_user",
            "source": "niakvio-private-chat",
            "private_memory": True,
            "proof_authority": False,
            "path": "conversations/c1/part-01.md",
            "heading": "old diagnosis",
            "authority": 38,
            "text": (
                "Sekai previously reached a player but required current request "
                "and decoded identity replay https://secret.example.org/player "
                "on /Users/Example/code; this is historical only"
            ),
        }]
        historical = [{
            "experience_id": f"hist-{i}",
            "source": "brain-repair-experience",
            "failure_class": "route_proven_gap",
            "strategy": "search_detail_player_terminal_traversal",
            "result": "validated",
            "providers": [provider],
            "signals": ["http_player"],
            "proof_authority": False,
        } for i in range(12)]
        negative = {
            "experience_id": "hosted-negative:44327993359:abcdefabcdefabcd",
            "source": "hosted-executed-negative",
            "providers": [provider],
            "failure_class": "executed_provider_no_improvement",
            "strategy": "slug_saga_inline_media",
            "result": "rejected_executed_no_improvement",
            "prior_only": True,
            "proof_authority": False,
            "mutation_fingerprint": "c" * 64,
        }
        structured = {
            "experience_id": "provider-knowledge:aaaaaaaaaaaa:sekai",
            "source": "provider-structured-knowledge",
            "providers": [provider],
            "failure_class": "provider_structured_recipe_prior",
            "strategy": "html_scraper",
            "result": "provider_recipe_prior",
            "prior_only": True,
            "proof_authority": False,
            "current_execution_proof": False,
            "current_network_proof": False,
            "provider_recipe": {
                "strategy": "html_scraper",
                "lego_families": ["sekai_runtime_v1"],
                "route_families": ["api", "detail", "episode", "player"],
                "recipe_roles": ["detail"],
                "recipe_methods": ["get"],
                "recipe_responses": ["html-or-text"],
                "media_types": ["anime"],
                "has_api_recipe": False,
                "has_provider_value_plan": False,
                "has_search_request_plan": False,
            },
        }
        request = RepairRequest(
            provider_id=provider,
            failure_class="route_proven_gap",
            status="REGRESSION PROVIDER",
            supported_types=["anime"],
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": (
                    "async function getStreams(query) { "
                    "const player = await extractPlayer(query); "
                    "return player || []; }\n"
                ),
            },
        )
        planner = BrainPlanner(
            object(), store=ExperienceStore(historical + [negative, structured]),
            documents=DocumentStore(documents),
        )
        experiences, retrieved, prior, policy, unused = planner._prepare(
            request, compact_force=True
        )
        self.assertEqual(unused, "")
        self.assertIn(negative["experience_id"], [
            row.get("experience_id") for row in experiences
        ], "a historical top-6 may not evict a current executed negative")
        self.assertTrue(any(
            row.get("private_memory") is True for row in retrieved
        ), "one old-chat provider-specific hit must survive MD result crowding")
        payload = build_force_prompt_payload(
            request, prior, policy, retrieved, experiences=experiences
        )
        negative_hints = payload.get("retrieved_executed_negative_memory") or []
        self.assertEqual(len(negative_hints), 1)
        self.assertEqual(negative_hints[0]["mechanism"], "slug_saga_inline_media")
        self.assertFalse(negative_hints[0]["proof_authority"])
        structured_hints = payload.get("retrieved_structured_provider_memory") or []
        self.assertEqual(len(structured_hints), 1)
        self.assertEqual(structured_hints[0]["lego_families"], ["sekai_runtime_v1"])
        self.assertEqual(structured_hints[0]["route_families"], ["api", "detail", "episode", "player"])
        self.assertFalse(structured_hints[0]["proof_authority"])
        self.assertNotIn("host", json.dumps(structured_hints))
        self.assertNotIn("routeTemplates", json.dumps(structured_hints))
        md_and_chat = payload.get("retrieved_document_hints") or []
        self.assertTrue(any(row["source_kind"] == "private_chat" for row in md_and_chat))
        self.assertTrue(any(row["source_kind"] == "public_markdown" for row in md_and_chat))
        self.assertTrue(all(row["proof_authority"] is False for row in md_and_chat))
        serialized = json.dumps(md_and_chat, ensure_ascii=False)
        self.assertNotIn("secret.example.org", serialized)
        self.assertNotIn("/Users/Example", serialized)
        self.assertNotIn("conversations/c1", serialized)
        self.assertNotIn("https://", serialized)
        self.assertFalse(payload["mutation_policy"]["force_abstain"] is False and
                         any(row["proof_authority"] is not False for row in md_and_chat))

    def test_other_provider_private_memory_and_failed_edits_do_not_transfer(self):
        request = RepairRequest(
            provider_id="movix", failure_class="route_proven_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={"runtimeMutationSource":"function getStreams(){return [];}"},
        )
        store = DocumentStore([{
            "kind": "document", "source": "niakvio-private-chat",
            "role": "private_chat_assistant", "private_memory": True,
            "proof_authority": False, "heading": "old Sekai note",
            "text": "Sekai provider route_proven_gap player crawler",
        }])
        planner = BrainPlanner(
            object(),
            store=ExperienceStore([{
                "source": "hosted-executed-negative", "providers": ["sekai"],
                "result": "rejected_executed_no_improvement",
                "prior_only": True, "proof_authority": False,
                "mutation_fingerprint": "c" * 64,
            }, {
                "source": "provider-structured-knowledge", "providers": ["sekai"],
                "result": "provider_recipe_prior", "prior_only": True,
                "proof_authority": False, "current_execution_proof": False,
                "current_network_proof": False,
                "provider_recipe": {"strategy": "html_scraper", "lego_families": ["sekai_runtime_v1"]},
            }]),
            documents=store,
        )
        experiences, docs, prior, policy, _ = planner._prepare(
            request, compact_force=True
        )
        self.assertFalse(any(row.get("private_memory") for row in docs))
        payload = build_force_prompt_payload(
            request, prior, policy, docs, experiences=experiences
        )
        self.assertNotIn("retrieved_executed_negative_memory", payload)
        self.assertNotIn("retrieved_document_hints", payload)
        self.assertNotIn("retrieved_structured_provider_memory", payload)


if __name__ == "__main__":
    unittest.main()
