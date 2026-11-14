from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from niakvio_brain_llm.advisor_experiments import next_advisor_experiment
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.priors import taxonomy_prior
from niakvio_brain_llm.repair_family import repair_family_descriptor


class ContentIdentityGapTests(unittest.TestCase):
    def request(self) -> RepairRequest:
        return RepairRequest(
            provider_id="demo",
            failure_class="content_identity_gap",
            status="PROVIDER JS BROKEN",
            supported_types=["movie", "tv"],
            census_prior={"dominantIssue": "provider_returned_wrong_content×2"},
            advisor_only=True,
        )

    def test_taxonomy_owns_provider_identity_selection(self) -> None:
        prior=taxonomy_prior("content_identity_gap")
        self.assertIsNotNone(prior)
        self.assertEqual(prior["target_layer"], "provider")
        self.assertEqual(prior["strategy_prior"], "bind_catalogue_result_to_requested_identity")
        self.assertGreaterEqual(float(prior["confidence"]), 0.95)

    def test_identity_advisor_experiment_is_alias_first_and_non_terminal(self) -> None:
        exp=next_advisor_experiment(
            self.request(),
            "bind_catalogue_result_to_requested_identity",
        )
        self.assertTrue(exp)
        self.assertTrue(exp["alias_search"])
        self.assertFalse(exp["terminal_only"])
        self.assertEqual(exp["role_order"][:4], ["search", "detail", "api", "episode"])
        self.assertTrue(exp["document_request_mining"])

    def test_repair_family_is_not_terminal_extraction(self) -> None:
        family=repair_family_descriptor(self.request())
        self.assertEqual(family["failure"], "content-identity-gap")
        self.assertEqual(family["archetype"], "content-identity-gap:content-identity")

    def test_guidance_publisher_maps_to_identity_alias_profile(self) -> None:
        root=Path(__file__).resolve().parents[1]
        path=root/"scripts"/"publish_niakvio_guidance.py"
        spec=importlib.util.spec_from_file_location("publish_niakvio_guidance",path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(
            mod.STRATEGY_TO_PROFILE["bind-catalogue-result-to-requested-identity"],
            "identity_alias_search_traversal_v1",
        )
        default=mod.DEFAULTS["bind-catalogue-result-to-requested-identity"]
        self.assertTrue(default["alias_search"])
        self.assertFalse(default.get("terminal_only", False))


if __name__ == "__main__":
    unittest.main()
