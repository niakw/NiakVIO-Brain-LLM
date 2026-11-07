"""Workflow actions and checkout credentials must remain pinned and ephemeral."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class WorkflowSupplyChainTests(unittest.TestCase):
    def test_workflow_refs_and_checkouts(self):
        paths=sorted((ROOT/'.github/workflows').glob('*.yml'))
        self.assertGreater(len(paths),5)
        uses=0
        for path in paths:
            lines=path.read_text(encoding='utf-8').splitlines()
            for i,line in enumerate(lines):
                match=re.match(r'^(\s*)-\s+uses:\s+([^\s#]+)',line)
                if not match:
                    continue
                ref=match.group(2)
                if ref.startswith('./'):
                    continue
                uses+=1
                self.assertRegex(ref,r'@[a-f0-9]{40}$',f'{path.name}: mutable action {ref}')
                if not ref.startswith('actions/checkout@'):
                    continue
                depth=len(match.group(1))
                scope=[]
                for row in lines[i+1:]:
                    if row.strip() and len(row)-len(row.lstrip())<=depth:
                        break
                    scope.append(row)
                self.assertRegex('\n'.join(scope),r'(?m)^\s*persist-credentials:\s*false\s*$',path.name)
        self.assertGreater(uses,25)

if __name__=='__main__':
    unittest.main()
