import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


page=load_module("page",Path("scripts/select_niakvio_guidance_page.py"))
merge=load_module("merge",Path("scripts/merge_niakvio_guidance_page.py"))


class GuidancePagingTests(unittest.TestCase):
    def test_pages_cover_exact_cohort_without_starvation(self):
        requested=[f"p{i}" for i in range(1,15)]
        state={}
        seen=[]
        for _ in range(2):
            current,state=page.select(
                requested,state,
                source_sha="a"*40,
                brain_sha="b"*40,
                page_size=8,
            )
            seen.extend(current)
        self.assertEqual(seen,requested)
        self.assertTrue(state["complete"])
        self.assertEqual(state["remainingProviders"],[])

    def test_completed_explicit_cohort_starts_new_cycle(self):
        requested=["a","b","c"]
        first,state=page.select(
            requested,{},
            source_sha="a"*40,
            brain_sha="b"*40,
            page_size=3,
        )
        self.assertEqual(first,requested)
        self.assertTrue(state["complete"])
        again,next_state=page.select(
            requested,state,
            source_sha="a"*40,
            brain_sha="b"*40,
            page_size=2,
        )
        self.assertEqual(again,["a","b"])
        self.assertEqual(next_state["cycle"],2)
        self.assertEqual(next_state["remainingProviders"],["c"])

    def test_source_or_brain_change_resets_progress(self):
        requested=["a","b","c"]
        _first,state=page.select(
            requested,{},
            source_sha="a"*40,
            brain_sha="b"*40,
            page_size=1,
        )
        current,_=page.select(
            requested,state,
            source_sha="c"*40,
            brain_sha="b"*40,
            page_size=1,
        )
        self.assertEqual(current,["a"])


class GuidanceMergeTests(unittest.TestCase):
    def advisor(self,source,brain,rows):
        return {
            "schemaVersion":2,
            "sourceNiakvioSha":source,
            "brainLlmSha":brain,
            "providerCount":len({r["providerId"] for r in rows}),
            "rows":rows,
        }

    def force(self,source,brain,rows):
        return {
            "schemaVersion":1,
            "sourceNiakvioSha":source,
            "brainLlmSha":brain,
            "providerCount":len({r["providerId"] for r in rows}),
            "rows":rows,
        }

    def test_merge_preserves_unrefreshed_and_replaces_refreshed(self):
        source="a"*40;brain="b"*40
        previous=self.advisor(source,brain,[
            {"providerId":"a","profile":"old","experimentFingerprint":"1"*64,"confidence":.9},
            {"providerId":"b","profile":"keep","experimentFingerprint":"2"*64,"confidence":.9},
        ])
        candidate=self.advisor(source,brain,[
            {"providerId":"a","profile":"new","experimentFingerprint":"3"*64,"confidence":.95},
        ])
        out=merge.merge(previous,candidate,{"a"},kind="advisor")
        self.assertEqual({r["profile"] for r in out["rows"]},{"new","keep"})
        self.assertEqual(out["providerCount"],2)

    def test_new_brain_revision_does_not_mix_old_rows(self):
        previous=self.force("a"*40,"b"*40,[
            {"providerId":"old","mutationFingerprint":"1"*64,"mutationContextFingerprint":"2"*64,"confidence":.9},
        ])
        candidate=self.force("a"*40,"c"*40,[
            {"providerId":"new","mutationFingerprint":"3"*64,"mutationContextFingerprint":"4"*64,"confidence":.9},
        ])
        out=merge.merge(previous,candidate,{"new"},kind="force")
        self.assertEqual([r["providerId"] for r in out["rows"]],["new"])


if __name__=="__main__":
    unittest.main()
