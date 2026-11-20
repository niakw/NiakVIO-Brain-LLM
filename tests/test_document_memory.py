import unittest

from niakvio_brain_llm.document_memory import DocumentStore, chunk_markdown

class DocumentMemoryTests(unittest.TestCase):
    def test_provider_specific_memory_is_retrieved(self):
        rows = []
        rows += chunk_markdown(
            "## Current\nPurstream terminal extractor changed after upstream drift.",
            path="MEMORY.md",
            authority=95,
            role="durable_recovery_memory",
        )
        rows += chunk_markdown(
            "## Other\nGeneric documentation about releases.",
            path="CHANGELOG.md",
            authority=65,
            role="change_history",
        )
        store = DocumentStore(rows)
        found = store.search({
            "provider_id": "purstream",
            "failure_class": "terminal_extractor",
        }, limit=1)
        self.assertEqual(found[0]["path"], "MEMORY.md")

    def test_high_authority_irrelevant_memory_is_not_injected(self):
        rows = chunk_markdown(
            "## Unrelated\nDesktop timer compatibility for an unrelated provider.",
            path="MEMORY.md",
            authority=100,
            role="durable_recovery_memory",
        )
        store = DocumentStore(rows)
        found = store.search({
            "provider_id": "movix",
            "failure_class": "api_discovery_gap",
        })
        self.assertEqual(found, [])

    def test_exact_native_source_shape_reserves_one_contract_reference(self):
        # Many generic provider-specific documents previously crowded a
        # verified structural contract out of a four-document LLM context.
        rows = []
        for index in range(6):
            rows += chunk_markdown(
                "## Anime-Sama regression provider\n"
                "Anime-Sama media_extraction_gap zero streams regression provider "
                "missing player terminal. " * 4,
                path=f"memory/{index}.md", authority=99,
                role="durable_recovery_memory",
            )
        rows += chunk_markdown(
            "## Catalogue episode contract\n"
            "Anime-Sama source shape script_html_2xx, script_http_missing. "
            "The catalogue has inline episode token declarations and an "
            "opaque identifier, not legacy external source URLs. "
            "Diagnosis only; no mutation, no WAF or domain claim.",
            path="docs/brain-oracle-catalogue-inline-episode-contract.md",
            authority=88,
            role="source_contract_reference",
        )
        store = DocumentStore(rows)
        base = {"provider_id": "anime-sama",
                "failure_class": "media_extraction_gap",
                "status": "REGRESSION PROVIDER",
                "supported_types": ["anime"]}
        # Ordinary lexical ranking is allowed to prefer current MEMORY.
        old = store.search(base, limit=4)
        self.assertEqual(len(old), 4)
        self.assertFalse(any(x["role"] == "source_contract_reference" for x in old))

        value = {
            "client": "tv", "historicalOnly": True, "appSelected": True,
            "readerEvidenceComplete": True, "nativeExtractionZeroObserved": True,
            "nativeSourceScriptShapePatterns": [
                "script_html_2xx", "script_http_missing",
                "https://PRIVATE.example/?token=SECRET",
            ],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }
        query = {**base, "observations": [{
            "source": "official-android-tv-emulator", "value": value,
        }]}
        found = store.search(query, limit=4)
        self.assertEqual(len(found), 4)
        self.assertEqual(
            sum(x["role"] == "source_contract_reference" for x in found), 1
        )
        self.assertIn(
            "docs/brain-oracle-catalogue-inline-episode-contract.md",
            [x["path"] for x in found],
        )
        for item in found:
            self.assertNotIn("SECRET", str(item))
            self.assertNotIn("PRIVATE.example", str(item))
        # Forged/selected-out/unknown signatures do not gain RAG priority.
        for changed in (
            {"appSelected": False},
            {"readerEvidenceComplete": False},
            {"historicalOnly": False},
            {"providerMutationAuthority": True},
            {"nativeSourceScriptShapePatterns": [
                "https://PRIVATE.example/?token=SECRET"
            ]},
        ):
            with self.subTest(changed=changed):
                invalid = {**base, "observations": [{
                    "source": "official-android-tv-emulator",
                    "value": {**value, **changed},
                }]}
                self.assertFalse(any(
                    x["role"] == "source_contract_reference"
                    for x in store.search(invalid, limit=4)
                ))
        self.assertFalse(any(x["role"] == "source_contract_reference"
                             for x in store.search(query, limit=4, private_only=True)))

    def test_markdown_is_chunked_by_major_heading(self):
        rows = chunk_markdown(
            "# Root\nintro\n## One\na\n## Two\nb",
            path="MEMORY.md",
            authority=95,
            role="memory",
        )
        headings = [row["heading"] for row in rows]
        self.assertIn("One", headings)
        self.assertIn("Two", headings)

if __name__ == "__main__":
    unittest.main()
