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
CARD_OPEN_RE = re.compile(
    r"""<(?:a|div|article|li)\b[^>]*\bclass\s*=\s*['"]([^'"]{1,300})['"][^>]*>""",re.I
)
TITLE_RE = re.compile(
    r"""<[^>]*\bclass\s*=\s*['"][^'"]*\bmovie-card-title\b[^'"]*['"][^>]*>(.*?)</[^>]+>""",re.I|re.S
)
FORMAT_RE = re.compile(
    r"""<[^>]*\bclass\s*=\s*['"][^'"]*\bmovie-card-format\b[^'"]*['"][^>]*>(.*?)</[^>]+>""",re.I|re.S
)
HTML_RE = re.compile(r"<(?:!doctype\s+html|html\b)",re.I)
WORDS = ("movie-card","movie-card-content","movie-card-title",
         "movie-card-format","episode-download-item","wp-block","post-item")
ERRORS = ("cloudflare","access denied","captcha","just a moment","checking your browser")

def shape(text: str, query: str) -> dict:
    # Reconstruct only safe structural facts. No titles, links or HTML escape.
    card_matches=[m for m in CARD_OPEN_RE.finditer(text)
                  if "movie-card" in m.group(1).lower().split()]
    cards=[m.group(0) for m in card_matches]
    card_regions=[
        text[m.start():(
          card_matches[i+1].start() if i+1<len(card_matches)
          else min(len(text),m.start()+15000)
        )]
        for i,m in enumerate(card_matches)
    ]
    title_nodes=[re.sub(r"<[^>]*>"," ",part).casefold()
                 for part in TITLE_RE.findall(text)]
    query_terms=[word for word in re.findall(r"[a-z0-9]+",query.casefold())
                 if word not in {"the","a","an","season","episode","of","and"}
                 and not word.isdigit()]
    matching_title_nodes=sum(
        bool(query_terms) and all(word in node for word in query_terms)
        for node in title_nodes
    )
    raw_formats=[re.sub(r"<[^>]*>"," ",part).casefold().strip()
                 for part in FORMAT_RE.findall(text)]
    category_counts={
        "movie":sum(bool(re.search(r"\bmovies?\b|\bfilms?\b",x)) for x in raw_formats),
        "series":sum(bool(re.search(r"\bseries\b|\bshows?\b|\btv\b",x)) for x in raw_formats),
        "uncategorized":sum(not re.search(r"\bmovies?\b|\bfilms?\b|\bseries\b|\bshows?\b|\btv\b",x)
                            for x in raw_formats)
    }
    def kind(label: str) -> str:
        if re.search(r"\\bseries\\b|\\bshows?\\b|\\btv\\b", label):
            return "series"
        if re.search(r"\\bmovies?\\b|\\bfilms?\\b", label):
            return "movie"
        return "other"
    card_badges=[
        [kind(re.sub(r"<[^>]*>"," ",part).casefold())
         for part in FORMAT_RE.findall(region)]
        for region in card_regions
    ]
    first_badges=[badges[0] if badges else "missing" for badges in card_badges]
    card_formats={
        "first_badge_movie":first_badges.count("movie"),
        "first_badge_series":first_badges.count("series"),
        "first_badge_other":first_badges.count("other"),
        "first_badge_missing":first_badges.count("missing"),
        "any_movie":sum("movie" in badges for badges in card_badges),
        "any_series":sum("series" in badges for badges in card_badges),
    }
    classes=[w for val in CLASS_RE.findall(text) for w in val.lower().split()]
    count={w:classes.count(w) for w in WORDS}
    hint={w:(w in text.casefold()) for w in ERRORS}
    return {
        "html":bool(HTML_RE.search(text[:400])),
        "html_class_attributes":len(CLASS_RE.findall(text)),
        "anchors_with_href":len(ANCHOR_RE.findall(text)),
        "exact_card_open_tags":len(cards),
        "exact_cards_with_href":sum(bool(re.search(r"\bhref\s*=",tag,re.I)) for tag in cards),
        "card_regions_with_nested_href":sum(bool(ANCHOR_RE.search(region))
                                           for region in card_regions),
        "card_regions_with_matching_query":sum(
            bool(query_terms) and all(word in re.sub(r"<[^>]*>"," ",region).casefold()
                                      for word in query_terms)
            for region in card_regions
        ),
        "title_nodes_matching_query_terms":matching_title_nodes,
        "title_nodes_parsed":len(title_nodes),
        "format_nodes_parsed":len(raw_formats),
        "format_category_counts":category_counts,
        "card_format_type_evidence":card_formats,
        "class_token_counts":count,
        "waf_marker_flags":hint,
        "body_sha256_16":hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
    }

# A genuinely present href must never be miscounted as absent.
assert re.search(r"\bhref\s*=", '<a class="movie-card" href="/detail">')

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
            out["shape"]=shape(body.decode("utf-8",errors="replace"),term)
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
