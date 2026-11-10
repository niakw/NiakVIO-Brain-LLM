import unittest

from niakvio_brain_llm.repair_family import (
    observed_source_topologies,
    repair_family_descriptor,
    select_family_wave,
)


def fixture(kind, *, markers=(), status=200, iframes=0):
    shape = {"kind": kind, "markers": list(markers), "iframes": iframes}
    return {
        "failure_class": "route_proven_gap",
        "status": "ROUTE PROVEN",
        "supported_types": ["movie", "tv"],
        "observations": [{
            "source": "census-sharded-current",
            "value": {"network": {"movie": [{"status": status, "shape": shape}]}},
        }],
    }


class CrossTopologyFamilyWaveTests(unittest.TestCase):
    def test_distinguishes_download_player_api_and_catalogue_without_splitting_family_hash(self):
        raws = [
            fixture("html", markers=("download",)),
            fixture("html", markers=("player", "embed"), iframes=2),
            fixture("json"),
            fixture("html"),
        ]
        descriptors = [repair_family_descriptor(x) for x in raws]
        self.assertEqual(len({d["key"] for d in descriptors}), 1)
        self.assertEqual(
            [d["sourceTopologies"] for d in descriptors],
            [["html-download"], ["html-player"], ["json-api"], ["html-catalogue"]],
        )
        rows = [
            {"provider": f"p{i}", "repair_family": descriptor}
            for i, descriptor in enumerate(descriptors)
        ]
        old, _ = select_family_wave(rows)
        self.assertEqual(len(old), 1)
        selected, deferred = select_family_wave(rows, ensure_topology_coverage=True)
        self.assertEqual({x["provider"] for x in selected}, {"p0", "p1", "p2", "p3"})
        self.assertEqual(deferred, [])

    def test_no_topology_from_waf_or_untrusted_historical_observation(self):
        challenged = fixture("html", markers=("player",), status=403)
        self.assertEqual(observed_source_topologies(challenged["observations"]), [])
        challenged["observations"][0]["source"] = "history"
        challenged["observations"][0]["value"]["network"]["movie"][0]["status"] = 200
        self.assertEqual(observed_source_topologies(challenged["observations"]), [])

    def test_overlapping_topologies_do_not_force_redundant_provider(self):
        mixed = fixture("html", markers=("download",))
        mixed["observations"][0]["value"]["network"]["movie"].append({
            "status": 200, "shape": {"kind": "json"}
        })
        raws = [mixed, fixture("json"), fixture("html", markers=("download",))]
        desc = [repair_family_descriptor(x) for x in raws]
        rows = [{"provider": f"p{i}", "repair_family": d} for i,d in enumerate(desc)]
        selected, deferred = select_family_wave(rows, ensure_topology_coverage=True)
        self.assertEqual([row["provider"] for row in selected], ["p0"])
        self.assertEqual(len(deferred), 2)

    def test_no_unverified_family_fanout(self):
        raw = fixture("json")
        family = repair_family_descriptor(raw)
        rows = [{"provider": "a", "repair_family": family}, {"provider": "b", "repair_family": family}]
        selected, _ = select_family_wave(rows, ensure_topology_coverage=True)
        self.assertEqual(len(selected), 1)


if __name__ == "__main__":
    unittest.main()
