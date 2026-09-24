from __future__ import annotations
import importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("publish",ROOT/"scripts"/"publish_niakvio_guidance.py");assert SPEC and SPEC.loader
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
class GuidanceTests(unittest.TestCase):
 def test_non_sensitive_experiment_survives(self):
  rows=[{"provider":"Movie_Box","failure_class":"media_extraction_gap","ok":True,"proposal":{"provider_id":"movie-box","target_layer":"provider","strategy":"proven_request_program_and_terminal_extraction","confidence":.94,"abstain":False,"diagnosis":"secret historical explanation","evidence":["https://sensitive.example/path"],"mutations":[{"scope":"provider_data","value":"secret"}],"experiment":{"route_policy":"owned_only","recipe_policy":"current_plus_provider","role_order":["api","source","player"],"terminal_only":True,"response_salvage":True,"max_depth":5,"max_pages":19,"max_embeds":27,"max_recipe_passes":5},"tests":["x"]}}]
  result=mod.sanitize(rows,niakvio_sha="a"*40,brain_llm_sha="b"*40);self.assertEqual(result["schemaVersion"],2);row=result["rows"][0];self.assertEqual(row["experiment"]["maxPages"],19);self.assertEqual(row["experiment"]["roleOrder"],["api","source","player"]);self.assertRegex(row["experimentFingerprint"],r"^[0-9a-f]{64}$");self.assertEqual(row["experimentFingerprint"],mod.experiment_fingerprint(row["experiment"]));serial=str(result);self.assertNotIn("sensitive.example",serial);self.assertNotIn("secret",serial)
 def test_distinct_specs_have_distinct_fingerprints(self):
  a=mod.sanitize_experiment({"max_depth":4},strategy="terminal-media-extractor-with-playback-validation");b=mod.sanitize_experiment({"max_depth":6},strategy="terminal-media-extractor-with-playback-validation");self.assertTrue(a["terminalOnly"]);self.assertNotEqual(mod.experiment_fingerprint(a),mod.experiment_fingerprint(b))
 def test_unbounded_fields_rejected(self):
  with self.assertRaises(ValueError):mod.sanitize_experiment({"url":"https://private.invalid"},strategy="search-detail-player-terminal-traversal")
 def test_unknown_or_abstain_dropped(self):
  base={"provider":"demo","failure_class":"route_proven_gap","ok":True}
  proposals=[{"provider_id":"demo","target_layer":"provider","strategy":"search_detail_player_terminal_traversal","confidence":.99,"abstain":True},{"provider_id":"demo","target_layer":"core","strategy":"search_detail_player_terminal_traversal","confidence":.99,"abstain":False},{"provider_id":"demo","target_layer":"provider","strategy":"unknown","confidence":.99,"abstain":False}]
  self.assertEqual(mod.sanitize([{**base,"proposal":p} for p in proposals],niakvio_sha="a"*40,brain_llm_sha="b"*40)["rows"],[])
 def test_shas_required(self):
  with self.assertRaises(ValueError):mod.sanitize([],niakvio_sha="main",brain_llm_sha="b"*40)
if __name__=="__main__":unittest.main()
