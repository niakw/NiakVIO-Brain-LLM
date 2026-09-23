import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.private_chat_memory import (
    PROJECT_ID,
    import_private_chat_project,
    redact_sensitive,
)


class PrivateChatMemoryTests(unittest.TestCase):
    def _project(self, root: Path) -> Path:
        project = root / "project"
        conv = project / "conversations" / "c1"
        conv.mkdir(parents=True)
        (project / "project.json").write_text(json.dumps({
            "id": PROJECT_ID,
            "name": "NiakVIO",
        }), encoding="utf-8")
        (project / "index.json").write_text(json.dumps({
            "projectId": PROJECT_ID,
            "conversations": {"c1": {}},
        }), encoding="utf-8")
        (conv / "index.json").write_text(json.dumps({
            "id": "c1",
            "title": "Provider repair",
            "capturedAt": "2026-09-23T00:00:00Z",
            "signals": {
                "architecture": ["ASSISTANT: provider census route repair core"],
                "noise": ["hello there"],
            },
        }), encoding="utf-8")
        (conv / "part-001.md").write_text(
            "# Provider repair\n\n"
            "## USER · 2026-09-23T00:00:00Z\n\n"
            "Movix provider route is CHAIN REACHED, repair terminal extractor.\n\n"
            "## TOOL · 2026-09-23T00:00:01Z\n\n"
            "Authorization: Bearer secret-token-value\n\n"
            "## ASSISTANT · 2026-09-23T00:00:02Z\n\n"
            "Use provider-local terminal extraction and playback identity validation.\n",
            encoding="utf-8",
        )
        return project

    def test_imports_signals_and_user_assistant_but_not_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = import_private_chat_project(self._project(Path(tmp)))
            roles = {row["role"] for row in rows}
            self.assertIn("private_chat_signal", roles)
            self.assertIn("private_chat_user", roles)
            self.assertIn("private_chat_assistant", roles)
            self.assertNotIn("private_chat_tool", roles)
            self.assertTrue(all(row["proof_authority"] is False for row in rows))
            self.assertTrue(all("conversation_title" not in row for row in rows))

    def test_rejects_wrong_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            (project / "project.json").write_text(json.dumps({
                "id": "wrong",
                "name": "Other",
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                import_private_chat_project(project)

    def test_redacts_sensitive_personal_and_secret_values(self):
        value = redact_sensitive(
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz "
            "github_pat_abcdefghijklmnopqrstuvwxyz "
            "mail test@example.com "
            "phone +33 6 12 34 56 78 "
            "ip 82.10.20.30 "
            "path /Users/tommy/project "
            "password=supersecret"
        )
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", value)
        self.assertNotIn("test@example.com", value)
        self.assertNotIn("+33 6 12 34 56 78", value)
        self.assertNotIn("82.10.20.30", value)
        self.assertNotIn("/Users/tommy", value)
        self.assertNotIn("supersecret", value)


if __name__ == "__main__":
    unittest.main()
