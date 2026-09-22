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
        self.assertLess(len(payload["request"]["provider_context"]["authored_module"]), 5100)
        self.assertLess(len(payload["request"]["observations"][0]["blob"]), 1000)
        self.assertLess(len(payload["retrieved_experiences"][0]["lesson"]), 1000)

if __name__ == "__main__":
    unittest.main()
