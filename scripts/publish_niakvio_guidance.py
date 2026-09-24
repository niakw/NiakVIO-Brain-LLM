#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

STRATEGY_TO_PROFILE={
 "provider-owned-origin-header-and-domain-replay":"provider_origin_failover_v1",
 "search-detail-player-terminal-traversal":"proven_route_terminal_traversal_v1",
 "terminal-media-extractor-with-playback-validation":"chain_terminal_extractor_v1",
 "same-provider-candidate-program-replay":"retained_candidate_replay_v1",
 "proven-request-program-and-terminal-extraction":"player_media_extractor_v1",
 "discover-api-from-current-page-and-bundles":"search_contract_inference_v1",
}
ALLOWED_PROFILES=frozenset(STRATEGY_TO_PROFILE.values())
PROVIDER_ID=re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$"); SHA40=re.compile(r"^[0-9a-f]{40}$")
ROLES=("search","detail","episode","player","source","api","other")
ROUTE_POLICIES={"owned_only","owned_plus_peer","owned_plus_peer_generic"}
RECIPE_POLICIES={"current_only","current_plus_provider","current_plus_provider_peer"}
EXPERIMENT_KEYS={"route_policy","recipe_policy","role_order","terminal_only","alias_search","response_salvage","document_request_mining","session_bootstrap","max_depth","max_pages","max_embeds","max_recipe_passes"}
DEFAULTS={
 "provider-owned-origin-header-and-domain-replay":{"route_policy":"owned_plus_peer","recipe_policy":"current_plus_provider","role_order":["api","detail","search","player","source","episode","other"],"session_bootstrap":True,"max_depth":3,"max_pages":14,"max_embeds":12,"max_recipe_passes":3},
 "search-detail-player-terminal-traversal":{"route_policy":"owned_plus_peer","recipe_policy":"current_plus_provider_peer","role_order":["search","detail","episode","player","source","api","other"],"max_depth":5,"max_pages":24,"max_embeds":24,"max_recipe_passes":4},
 "terminal-media-extractor-with-playback-validation":{"route_policy":"owned_plus_peer","recipe_policy":"current_plus_provider_peer","role_order":["player","source","api","episode","detail","other"],"terminal_only":True,"response_salvage":True,"max_depth":5,"max_pages":20,"max_embeds":28,"max_recipe_passes":4},
 "same-provider-candidate-program-replay":{"route_policy":"owned_only","recipe_policy":"current_plus_provider","role_order":["player","api","source","detail","episode","other"],"max_depth":4,"max_pages":18,"max_embeds":24,"max_recipe_passes":4},
 "proven-request-program-and-terminal-extraction":{"route_policy":"owned_only","recipe_policy":"current_plus_provider","role_order":["api","source","player","episode","detail","other"],"terminal_only":True,"response_salvage":True,"max_depth":5,"max_pages":18,"max_embeds":28,"max_recipe_passes":5},
 "discover-api-from-current-page-and-bundles":{"route_policy":"owned_plus_peer_generic","recipe_policy":"current_plus_provider_peer","role_order":["search","api","detail","player","source","episode","other"],"document_request_mining":True,"max_depth":4,"max_pages":28,"max_embeds":20,"max_recipe_passes":4},
}
def canon(v): return str(v or "").strip().casefold().replace("_","-")
def load_jsonl(path):
 out=[]
 for line in path.read_text(encoding="utf-8").splitlines():
  if line.strip():
   v=json.loads(line)
   if isinstance(v,dict): out.append(v)
 return out
def bounded(v,lo,hi,default):
 try:n=int(v)
 except (TypeError,ValueError):n=default
 return max(lo,min(hi,n))
def sanitize_experiment(value:Any,*,strategy:str)->dict[str,Any]:
 src=value if isinstance(value,dict) else {}
 extra=set(src)-EXPERIMENT_KEYS
 if extra: raise ValueError("unexpected experiment fields: "+",".join(sorted(extra)))
 default=dict(DEFAULTS.get(strategy) or {})
 rp=str(src.get("route_policy") or default.get("route_policy") or "owned_only").strip().casefold()
 qp=str(src.get("recipe_policy") or default.get("recipe_policy") or "current_only").strip().casefold()
 if rp not in ROUTE_POLICIES or qp not in RECIPE_POLICIES: raise ValueError("invalid experiment policy")
 raw=src.get("role_order"); raw=raw if isinstance(raw,list) else default.get("role_order") or list(ROLES)
 roles=[]
 for x in raw:
  role=str(x or "").strip().casefold()
  if role not in ROLES: raise ValueError("invalid experiment role")
  if role not in roles: roles.append(role)
 return {
  "routePolicy":rp,"recipePolicy":qp,"roleOrder":roles[:7],
  "terminalOnly":bool(src.get("terminal_only",default.get("terminal_only",False))),
  "aliasSearch":bool(src.get("alias_search",default.get("alias_search",False))),
  "responseSalvage":bool(src.get("response_salvage",default.get("response_salvage",False))),
  "documentRequestMining":bool(src.get("document_request_mining",default.get("document_request_mining",False))),
  "sessionBootstrap":bool(src.get("session_bootstrap",default.get("session_bootstrap",False))),
  "maxDepth":bounded(src.get("max_depth",default.get("max_depth")),2,6,4),
  "maxPages":bounded(src.get("max_pages",default.get("max_pages")),6,36,18),
  "maxEmbeds":bounded(src.get("max_embeds",default.get("max_embeds")),6,36,20),
  "maxRecipePasses":bounded(src.get("max_recipe_passes",default.get("max_recipe_passes")),1,6,4),
 }
def experiment_fingerprint(exp):
 return hashlib.sha256(json.dumps(exp,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
def sanitize(rows,*,niakvio_sha,brain_llm_sha,min_confidence=.80):
 niakvio_sha=str(niakvio_sha).strip().casefold(); brain_llm_sha=str(brain_llm_sha).strip().casefold()
 if not SHA40.fullmatch(niakvio_sha) or not SHA40.fullmatch(brain_llm_sha): raise ValueError("exact 40-hex source SHAs are required")
 guidance=[];seen=set()
 for row in rows:
  if row.get("ok") is not True: continue
  provider=canon(row.get("provider")); proposal=row.get("proposal")
  if not provider or not PROVIDER_ID.fullmatch(provider) or not isinstance(proposal,dict) or canon(proposal.get("provider_id"))!=provider: continue
  strategy=canon(proposal.get("strategy")); profile=STRATEGY_TO_PROFILE.get(strategy,""); target=canon(proposal.get("target_layer")); failure=canon(row.get("failure_class"))
  try:confidence=max(0.,min(1.,float(proposal.get("confidence") or 0.)))
  except (TypeError,ValueError):confidence=0.
  if proposal.get("abstain") is True or target!="provider" or confidence<min_confidence or profile not in ALLOWED_PROFILES: continue
  exp=sanitize_experiment(proposal.get("experiment"),strategy=strategy); fp=experiment_fingerprint(exp); key=(provider,profile,fp)
  if key in seen: continue
  seen.add(key)
  guidance.append({"providerId":provider,"failureClass":failure,"targetLayer":"provider","strategy":strategy,"profile":profile,"confidence":round(confidence,6),"priorOnly":True,"experiment":exp,"experimentFingerprint":fp})
 return {"schemaVersion":2,"sourceNiakvioSha":niakvio_sha,"brainLlmSha":brain_llm_sha,"publicationAuthority":False,"directMutationAuthority":False,"proofAuthority":False,"rawMutationContentRetained":False,"privateContentRetained":False,"minConfidence":min_confidence,"providerCount":len({r["providerId"] for r in guidance}),"rows":guidance}
def main():
 p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--niakvio-sha",required=True);p.add_argument("--brain-llm-sha",required=True);p.add_argument("--min-confidence",type=float,default=.80);a=p.parse_args()
 out=sanitize(load_jsonl(a.input),niakvio_sha=a.niakvio_sha,brain_llm_sha=a.brain_llm_sha,min_confidence=a.min_confidence);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps({"provider_count":out["providerCount"],"rows":len(out["rows"]),"experiment_specs":len(out["rows"]),"private_content_retained":False},sort_keys=True));return 0
if __name__=="__main__": raise SystemExit(main())
