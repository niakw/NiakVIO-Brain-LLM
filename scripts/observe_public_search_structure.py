#!/usr/bin/env python3
"""Read-only structural probe for a current public provider search endpoint.

No raw HTML, link, player, caption, media URL, token or host-derived path is
printed or persisted. Outcome is causal diagnostic, never playback proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

MAX_BODY = 256_000
CLASS_RE = re.compile(r"""class\s*=\s*['"]([^'"]{1,300})['"]""",re.I)
ANCHOR_RE = re.compile(r"<a\b[^>]*\bhref\s*=",re.I)
HTML_RE = re.compile(r"<(?:!doctype\s+html|html\b)",re.I)
WORDS = ("movie-card","movie-card-content","movie-card-title",
         "movie-card-format","episode-download-item","wp-block","post-item")
ERRORS = ("cloudflare","access denied","captcha","just a moment","checking your browser")

def shape(text: str) -> dict:
    classes=[w for val in CLASS_RE.findall(text) for w in val.lower().split()]
    count={w:classes.count(w) for w in WORDS}
    hint={w:(w in text.casefold()) for w in ERRORS}
    return {
        "html":bool(HTML_RE.search(text[:400])),
        "html_class_attributes":len(CLASS_RE.findall(text)),
        "anchors_with_href":len(ANCHOR_RE.findall(text)),
        "class_token_counts":count,
        "waf_marker_flags":hint,
        "body_sha256_16":hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
    }

def probe(origin: str, term: str) -> dict:
    target=origin.rstrip("/")+"/?"+urllib.parse.urlencode({"s":term})
    req=urllib.request.Request(target,headers={
      "User-Agent":"Mozilla/5.0 (compatible; NiakVIO-Brain/1.0; diagnostic)",
      "Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
      "Accept-Language":"en-US,en;q=0.9",
    })
    out={"fixture":term,"diagnostic_only":True,
         "terminal_media_verified":False,"decoded_episode_verified":False}
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            body=response.read(MAX_BODY+1)
            final=urllib.parse.urlparse(response.geturl())
            out.update({
                "status":response.status,
                "redirect_cross_origin":final.hostname!=urllib.parse.urlparse(origin).hostname,
                "content_type":response.headers.get_content_type(),
                "body_bytes_sampled":min(len(body),MAX_BODY),
                "body_truncated":len(body)>MAX_BODY,
            })
            if len(body)>MAX_BODY:body=body[:MAX_BODY]
            out["shape"]=shape(body.decode("utf-8",errors="replace"))
    except urllib.error.HTTPError as e:
        out.update({"status":e.code,"network_state":"http_error"})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason=getattr(e,"reason",None)
        out.update({"status":None,"network_state":type(reason or e).__name__})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--origin",required=True)
    p.add_argument("--query",action="append",required=True)
    args=p.parse_args()
    parsed=urllib.parse.urlparse(args.origin)
    if parsed.scheme!="https" or parsed.username or parsed.password or not parsed.hostname or parsed.port not in (None,443):
        raise SystemExit("Only public HTTPS origins are eligible")
    if parsed.hostname.lower() in {"localhost","127.0.0.1"} or parsed.hostname.endswith((".local",".internal")):
        raise SystemExit("Private/local origins are prohibited")
    for term in args.query[:4]:
        result=probe(args.origin,str(term)[:100])
        print("FIELD_BRAIN_PUBLIC_SEARCH_STRUCTURE "+json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
