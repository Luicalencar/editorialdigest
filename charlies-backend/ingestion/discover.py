from typing import List, Dict
import feedparser
from urllib.parse import urlparse
from ingestion.canonicalize import canonicalize_url
from utils.logging import get_logger
import httpx

log = get_logger(__name__)

def _from_rss(cfg: Dict) -> List[str]:
    urls = []
    per_feed_limit = int(cfg.get("per_feed_limit", 0) or 0)
    headers = cfg.get("headers") or {}
    with httpx.Client(follow_redirects=True, timeout=15) as client:
        for feed in cfg.get("rss_feeds", []):
            try:
                r = client.get(feed, headers=headers)
                content = r.text if r.status_code == 200 else ""
            except Exception:
                content = ""
            parsed = feedparser.parse(content or feed)
            count = 0
            for e in parsed.entries:
                link = e.get("link")
                if link:
                    urls.append(link)
                    count += 1
                    if per_feed_limit and count >= per_feed_limit:
                        break
    return urls

def _from_html(cfg: Dict) -> List[str]:
    # HTML discovery stub (selectors could be added in config later)
    # Return empty for MVP; RSS gives us coverage now.
    return []

def discover_links(cfg: Dict) -> List[str]:
    seen = set()
    out = []
    for src in cfg.get("source_type_priority", ["rss"]):
        if src == "rss":
            batch = _from_rss(cfg)
        elif src == "html":
            batch = _from_html(cfg)
        else:
            batch = []
        for u in batch:
            cu = canonicalize_url(u)
            if cu not in seen:
                seen.add(cu)
                out.append(cu)
        if len(out) >= cfg.get("max_items", 15):
            break
    return out[: cfg.get("max_items", 15)]
