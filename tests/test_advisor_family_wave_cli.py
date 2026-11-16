from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")

assert '"--advisor-family-wave"' in source
assert '(args.mode == "repair" and not args.advisor_only)' in source
assert 'args.mode in {"repair", "brain"}' in source
assert "args.advisor_only" in source and "args.advisor_family_wave" in source
assert "select_family_wave(" in source
assert "family_wave_deferred" in source

# Opt-in only: ordinary advisor mode must retain its existing behavior unless
# NiakVIO explicitly requests one-oracle-per-family planning.
assert 'action="store_true"' in source.split('"--advisor-family-wave"', 1)[1].split(")", 1)[0]

print("Brain advisor family-wave opt-in contract passed")

# NiakVIO invokes advisor planning in mode=brain. The opt-in must cover that
# exact non-mutating mode without enabling family reduction by default.
assert 'args.mode in {"repair", "brain"}' in source
assert 'args.mode == "diagnostic"' not in source.split("family_wave_enabled =",1)[1].split("if family_wave_enabled:",1)[0]
