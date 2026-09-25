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
    "retry_backend = LocalOpenAICompatibleBackend",
    "timeout_seconds=120",
    "max_tokens=max(128, min(int(args.max_tokens), 256))",
):
    assert token in src, token

assert 'parser.add_argument("--advisor-only", action="store_true")' in route
assert "request.advisor_only = bool(args.advisor_only)" in route
assert "--mode brain \\" in wf
assert "--advisor-only \\" in wf
assert "--mode repair \\" in wf
assert '"${provider_args[@]}"' in wf
assert "force_llm_needed=" in wf
assert "--limit 4" not in wf
assert "requested_repair_queue" in wf
assert "niakvio-guidance-targets.txt" in wf
assert "produced zero executable mutations" in wf

assert "-c 32768" in wf
assert "-np 1" in wf
assert "--workers 1" in wf
assert "--advisor-only" in wf
assert "--max-tokens 256" in wf
assert "--timeout-seconds 75" in wf
assert wf.index("-np 1") < wf.index("--workers 1")

print("bounded concurrent private-guidance batch contract passed")
