from pathlib import Path
import contextlib
import io
import json
import sys
import unittest
import importlib.util
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]


spec=importlib.util.spec_from_file_location("golden_model", ROOT/"benchmark/golden_model_benchmark.py")
benchmark=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(benchmark)


class ChallengerCpuWorkflowContract(unittest.TestCase):
    def test_numeric_telemetry_cannot_corrupt_stdout_json(self):
        class FakePlanner:
            def propose_raw(self, _request):
                print("FIELD_BRAIN_LOCAL_INFERENCE prompt_n=10 predicted_n=5")
                return {"result":"ok"}
        stdout,stderr=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            outcome=benchmark.propose_without_stdout_telemetry(FakePlanner(), object())
        self.assertEqual(outcome, {"result":"ok"})
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("FIELD_BRAIN_LOCAL_INFERENCE", stderr.getvalue())
        with TemporaryDirectory() as td:
            path=Path(td)/"checkpoint.json"
            report=benchmark.aggregate_report(model="test",cases=[{},{}],rows=[{"id":"a"}],
                counts={"schema_valid":1},extra_documents=0)
            benchmark.write_report(report,str(path))
            self.assertEqual(json.loads(path.read_text())["completedCases"],1)
            self.assertTrue(json.loads(path.read_text())["incomplete"])
            self.assertEqual(list(Path(td).glob("*.tmp")),[])

    def test_no_paid_runner_or_provider_publication(self):
        workflow=(ROOT/'.github/workflows/model-challenger-cpu.yml').read_text()
        self.assertIn('runs-on: ubuntu-latest',workflow)
        self.assertIn('workflow_dispatch:',workflow)
        self.assertIn("'benchmark/model-challenger.trigger'",workflow)
        self.assertIn('model=qwen35-9b-q4',workflow)
        self.assertIn('acceptance=not-run decoded=not-run',workflow)
        self.assertNotIn('NIAKVIO_ALLOW_PAID_API=1',workflow)
        self.assertNotIn('api.openai.com',workflow)
        self.assertNotIn('publish_niakvio_force_mutations.py',workflow)
        self.assertNotIn('manifest.json',workflow)
        self.assertIn('sha256sum -c -',workflow)
        self.assertIn('--output .challenger/result.json',workflow)
        self.assertIn('benchmark incomplete: do not publish a model quality score',workflow)
        self.assertIn('ef6f244d63abcba4f8d30b7cbd9369e9e798fc33cf21109889373f59af329c93',workflow)


if __name__=="__main__":
    unittest.main()
