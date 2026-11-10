from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ChallengerCpuWorkflowContract(unittest.TestCase):
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
        self.assertIn('ef6f244d63abcba4f8d30b7cbd9369e9e798fc33cf21109889373f59af329c93',workflow)


if __name__=="__main__":
    unittest.main()
