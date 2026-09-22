import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_prompt_payload

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
        self.assertEqual(len(payload["retrieved_experiences"]), 2)
        self.assertEqual(len(payload["retrieved_documents"]), 1)
        self.assertLess(len(payload["retrieved_documents"][0]["text"]), 700)

if __name__ == "__main__":
    unittest.main()
