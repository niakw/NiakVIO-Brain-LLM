from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
src=(ROOT/"scripts/plan_batch_from_checkout.py").read_text(encoding="utf-8")
wf=(ROOT/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")
route=(ROOT/"scripts/route_batch_from_checkout.py").read_text(encoding="utf-8")

for token in (
    "ThreadPoolExecutor",
    "as_completed",
    "--workers",
    'thread_name_prefix="niakvio-llm"',
    'rows.sort(key=lambda row: int(row["position"]))',
    '"parallel_workers": workers',
    "--advisor-only",
    "--max-tokens",
    "--timeout-seconds",
):
    assert token in src, token

assert 'parser.add_argument("--advisor-only", action="store_true")' in route
assert "request.advisor_only = bool(args.advisor_only)" in route
assert "--mode brain             --advisor-only" in wf
assert "--mode repair             --output routing-force.jsonl" in wf
assert "force_llm_needed=" in wf

assert "-c 24576" in wf
assert "-np 2" in wf
assert "--workers 2" in wf
assert "--advisor-only" in wf
assert "--max-tokens 512" in wf
assert "--timeout-seconds 90" in wf
assert "--max-tokens 1024" in wf
assert "--timeout-seconds 120" in wf
assert wf.index("-np 2") < wf.index("--workers 2")

print("bounded concurrent private-guidance batch contract passed")
