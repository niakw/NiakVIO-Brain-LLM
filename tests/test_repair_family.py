import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.repair_family import repair_family_descriptor


class RepairFamilyTests(unittest.TestCase):
    def _request(self, provider: str, *, nested: int = 24) -> RepairRequest:
        return RepairRequest(
            provider_id=provider,
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            supported_types=["movie", "tv"],
            observations=[{
                "source": "census-sharded-current",
                "value": {
                    "debugStages": {"movie": "provider_network_zero_result"},
                    "structureHints": [
                        "movie:classes=movie-card,movie-card-format;"
                        f"classFacts=[movie-card;count=12;selfHref=1;nestedAnchors={nested};"
                        "tags=a,div,span;signals=movie,series,year]"
                    ],
                    "network": {
                        "movie": [{
                            "status": 200,
                            "shape": {"kind": "html"},
                        }]
                    },
                },
            }],
            allowed_mutations=["provider_patch", "provider_bloc"],
        )

    def test_family_identity_is_provider_independent(self):
        left = repair_family_descriptor(self._request("alpha"))
        right = repair_family_descriptor(self._request("beta"))
        self.assertEqual(left["key"], right["key"])
        self.assertEqual(left["archetype"], right["archetype"])
        self.assertIn("class-prefix-family", left["signals"])
        self.assertIn("mixed-tag-nested-container", left["signals"])

    def test_materially_different_structure_changes_family(self):
        nested = repair_family_descriptor(self._request("alpha", nested=24))
        flat = repair_family_descriptor(self._request("alpha", nested=0))
        self.assertNotEqual(nested["key"], flat["key"])
        self.assertNotEqual(nested["archetype"], flat["archetype"])


if __name__ == "__main__":
    unittest.main()
