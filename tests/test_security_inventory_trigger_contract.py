"""Keep the security inventory tied to actual source changes, not a stale week."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InventoryTriggerContractTests(unittest.TestCase):
    def test_source_changes_trigger_read_only_code_scanning_inventory(self):
        workflow = (ROOT / ".github/workflows/security-alert-inventory.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("branches: [main]", workflow)
        for scope in (".github/workflows/**", "src/**", "scripts/**", "tests/**", "pyproject.toml", "config/**"):
            self.assertIn("- '" + scope + "'", workflow)
        self.assertIn("security-events: read", workflow)
        self.assertIn("source=${source} status=unavailable_not_clean", workflow)
        self.assertIn("if [ \"${source}\" = \"code-scanning\" ]; then failed=1", workflow)
        self.assertIn('if [ "${failed}" -ne 0 ]; then', workflow)
        self.assertNotIn("continue-on-error: true", workflow)
        self.assertNotIn("security-events: write", workflow)


if __name__ == "__main__":
    unittest.main()
