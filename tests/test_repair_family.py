import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.repair_family import repair_family_descriptor, select_family_wave


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

    def test_catalogue_metadata_does_not_fragment_same_causal_family(self):
        left = self._request("alpha")
        right = self._request("beta")
        right.status = "CHAIN REACHED"
        right.supported_types = ["anime"]
        right.allowed_mutations = ["provider_bloc"]
        self.assertEqual(
            repair_family_descriptor(left)["key"],
            repair_family_descriptor(right)["key"],
        )

    def test_materially_different_structure_changes_family(self):
        nested = repair_family_descriptor(self._request("alpha", nested=24))
        flat = repair_family_descriptor(self._request("alpha", nested=0))
        self.assertNotEqual(nested["key"], flat["key"])
        self.assertNotEqual(nested["archetype"], flat["archetype"])


    def test_response_format_does_not_split_same_route_parser_family(self):
        base = self._request("alpha", nested=0)
        left = base.to_dict()
        right = base.to_dict()
        left["observations"][0]["value"]["network"] = {"movie":[{"status":200,"shape":{"kind":"html"}}]}
        right["observations"][0]["value"]["network"] = {"movie":[{"status":200,"shape":{"kind":"json"}}]}
        left_family = repair_family_descriptor(left)
        right_family = repair_family_descriptor(right)
        self.assertEqual(left_family["key"], right_family["key"])
        self.assertEqual(left_family["archetype"], "route-proven-gap:route-parser")

    def test_family_wave_selects_one_unvalidated_representative_and_rotates(self):
        family = {"key": "a" * 64}
        rows = [
            {"provider": "alpha", "repair_family": family},
            {"provider": "beta", "repair_family": family},
            {"provider": "gamma", "repair_family": {"key": "b" * 64}},
        ]
        selected, deferred = select_family_wave(
            rows,
            provider_failure_burden={"alpha": 3, "beta": 0, "gamma": 2},
        )
        self.assertEqual([row["provider"] for row in selected], ["beta", "gamma"])
        self.assertEqual([row["provider"] for row in deferred], ["alpha"])

    def test_validated_family_fans_out_all_members(self):
        family = {"key": "c" * 64}
        rows = [
            {"provider": "alpha", "repair_family": family},
            {"provider": "beta", "repair_family": family},
        ]
        selected, deferred = select_family_wave(
            rows,
            validated_family_keys={family["key"]},
            provider_failure_burden={"alpha": 9, "beta": 0},
        )
        self.assertEqual([row["provider"] for row in selected], ["alpha", "beta"])
        self.assertEqual(deferred, [])


if __name__ == "__main__":
    unittest.main()
