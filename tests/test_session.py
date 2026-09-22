import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.session import BrainSession, VerificationOutcome

def response(strategy: str) -> str:
    return json.dumps({
        "provider_id": "demo",
        "diagnosis": "bounded diagnosis",
        "strategy": strategy,
        "confidence": 0.8,
        "target_layer": "provider",
        "mutations": [{
            "scope": "provider_data",
            "operation": "set",
            "path": "repair.strategy",
            "value": strategy
        }],
        "tests": ["retest"],
        "abstain": False,
    })

class SessionTests(unittest.TestCase):
    def test_records_external_verification(self):
        session = BrainSession(BrainPlanner(StaticBackend(response("fix-a"))), max_attempts=2)
        request = RepairRequest(provider_id="demo", failure_class="terminal_extractor")
        proposal = session.propose(request)
        session.record(proposal, VerificationOutcome(result="failed", observations=["still zero"]))
        self.assertEqual(len(session.history), 1)

    def test_repeated_hypothesis_is_rejected(self):
        session = BrainSession(BrainPlanner(StaticBackend(response("fix-a"))), max_attempts=3)
        request = RepairRequest(provider_id="demo", failure_class="terminal_extractor")
        first = session.propose(request)
        session.record(first, VerificationOutcome(result="failed"))
        with self.assertRaises(RuntimeError):
            session.propose(request)

if __name__ == "__main__":
    unittest.main()
