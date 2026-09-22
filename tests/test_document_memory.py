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
