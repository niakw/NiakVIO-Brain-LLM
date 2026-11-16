from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")

assert '"--advisor-family-wave"' in source
assert "and (not args.advisor_only or args.advisor_family_wave)" in source
assert 'args.mode == "repair"' in source
assert "select_family_wave(" in source
assert "family_wave_deferred" in source

# Opt-in only: ordinary advisor mode must retain its existing behavior unless
# NiakVIO explicitly requests one-oracle-per-family planning.
assert 'action="store_true"' in source.split('"--advisor-family-wave"', 1)[1].split(")", 1)[0]

print("Brain advisor family-wave opt-in contract passed")
