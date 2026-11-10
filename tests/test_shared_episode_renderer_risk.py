import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import compact_request
from niakvio_brain_llm.provider_context import (
    build_provider_context, shared_episode_identity_risk,
)


BROKEN_SHARED = """
var season=Number((obj&&obj.season)!=null?obj.season:args[2])||1;
var episode=Number((obj&&obj.episode)!=null?obj.episode:args[3])||1;
if(!season)season=seasons[0]||null;
if(!ep)ep=eps[0]||null;
"""


class SharedRendererCurrentSourceTests(unittest.TestCase):
    def test_actual_shared_runtime_not_only_wrapper_exposes_failure_mechanism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patches = root / "scripts" / "provider_patches"
            patches.mkdir(parents=True)
            (patches / "animevost_fr_runtime_v1.py").write_text(
                "from anime_catalogue_runtime_common import apply_runtime\n",
                encoding="utf-8",
            )
            (patches / "anime_catalogue_runtime_common.py").write_text(
                BROKEN_SHARED, encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text(
                json.dumps({"provider_patches": {
                    "demo": {"patch_scripts": [
                        "scripts/provider_patches/animevost_fr_runtime_v1.py"
                    ]}
                }}),
                encoding="utf-8",
            )
            context = build_provider_context(root, "demo")
            self.assertEqual(
                context["runtime_template_prior"]["template"],
                "scripts/provider_patches/anime_catalogue_runtime_common.py",
            )
            risk = context["runtime_episode_safety_diagnostics"]
            self.assertFalse(risk["proofAuthority"])
            self.assertTrue(risk["diagnosticOnly"])
            self.assertEqual(len(risk["signals"]), 4)
            self.assertIn("season_zero_coerced_to_one", risk["signals"])
            self.assertIn("missing_episode_falls_back_to_first", risk["signals"])
            request = RepairRequest(
                provider_id="demo", failure_class="episode-coordinate-loss",
                provider_context=context,
            )
            compact = compact_request(
                request, high_confidence=True, mutation_allowed=False,
            )
            model_risks = compact["provider_context"][
                "runtime_episode_safety_diagnostics"
            ]
            self.assertFalse(model_risks["proofAuthority"])
            self.assertEqual(model_risks["signals"], risk["signals"])
            self.assertNotIn(BROKEN_SHARED, str(model_risks))

    def test_safe_shared_code_does_not_create_fake_negative_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patches = root / "scripts" / "provider_patches"
            patches.mkdir(parents=True)
            (patches / "safe_common.py").write_text(
                "const season=Number(arg.season);\n"
                "if (!seasons.find(x => x.number === season)) return [];\n",
                encoding="utf-8",
            )
            self.assertEqual(shared_episode_identity_risk(
                root, "scripts/provider_patches/safe_common.py"
            ), {})
            self.assertEqual(shared_episode_identity_risk(
                root, "scripts/provider_patches/../../secrets.txt"
            ), {})


if __name__ == "__main__":
    unittest.main()
