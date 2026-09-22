import unittest

from niakvio_brain_llm.contracts import RepairProposal, RepairRequest
from niakvio_brain_llm.learning import sanitized_experience
from niakvio_brain_llm.session import VerificationOutcome

class LearningTests(unittest.TestCase):
    def test_learning_record_omits_raw_context(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="terminal_extractor",
            provider_context={"raw_secret": "must-not-persist"},
        )
        proposal = RepairProposal(
            provider_id="demo",
            diagnosis="extractor changed",
            strategy="repair_terminal",
            confidence=0.8,
            target_layer="provider",
            mutations=[{"scope": "provider_js", "code": "raw patch omitted"}],
        )
        row = sanitized_experience(
            request,
            proposal,
            VerificationOutcome(result="validated", verified_lanes=["movie"]),
        )
        encoded = str(row)
        self.assertNotIn("must-not-persist", encoded)
        self.assertNotIn("raw patch omitted", encoded)
        self.assertEqual(row["result"], "validated")

if __name__ == "__main__":
    unittest.main()
