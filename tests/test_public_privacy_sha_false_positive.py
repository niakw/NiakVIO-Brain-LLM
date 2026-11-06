from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("privacy", ROOT/"scripts/audit_public_repo_privacy.py")
assert spec and spec.loader
privacy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)
class PublicPrivacyCommitHashTest(unittest.TestCase):
    def test_sha_is_not_french_phone(self):
        self.assertFalse(privacy.phone_in_public_text('"sha": "0123456789abcdef0123456789abcdef01234567"'))
    def test_real_phone_remains_blocked(self):
        self.assertTrue(privacy.phone_in_public_text('Contact: 01 23 45 67 89'))
        self.assertTrue(privacy.phone_in_public_text('"sha":"'+("f"*40)+'", contact +33 6 12 34 56 78'))
    def test_nonhex_digit_sequence_remains_detected(self):
        self.assertTrue(privacy.phone_in_public_text('Phone: 0612345678'))
if __name__ == "__main__":
    unittest.main()
