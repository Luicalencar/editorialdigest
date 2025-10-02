import hashlib, os, asyncio, httpx
import feedparser
from datetime import datetime, timezone
from typing import List, Tuple
from slugify import slugify

from ingestion.fetch import get_with_cache_headers
from ingestion.canonicalize import canonicalize_url
from ingestion.extract import extract_article_fields
from storage.models import Article, ArticleSnapshot, FrontpageItem, AgentJob
from storage.objects import save_raw_html
from utils.logging import get_logger

log = get_logger(__name__)

def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def _canonicalize_section_to_tag(section: str) -> str:
    s = (section or "").strip().lower()
    if not s:
        return ""
    mapping = {
        # common sections to our canonical tags
        "politics": "Politics",
        "us": "Politics",
        "u.s.": "Politics",
        "world": "Politics",
        "business": "Economy",
        "economy": "Economy",
        "technology": "Technology",
        "tech": "Technology",
        "science": "Science",
        "health": "Health",
    }
    # exact match first
    if s in mapping:
        return mapping[s]
    # startswith heuristics
    for key, val in mapping.items():
        if s.startswith(key):
            return val
    return ""

def _infer_tag(title: str, section: str = None) -> str:
    t = (title or "").lower()
    # Prefer explicit section mapping if available
    sec_tag = _canonicalize_section_to_tag(section or "")
    if sec_tag:
        return sec_tag
    # simple keyword mapper broadened
    economy_kw = ["economy","inflation","market","jobs","gdp","finance","bank","stocks","wall street"]
    politics_kw = ["election","congress","president","policy","senate","government","politics","white house"]
    tech_kw = ["tech","technology","ai","artificial intelligence","software","apple","google","microsoft","startup"]
    health_kw = ["health","covid","hospital","medicine","medical","cdc","virus","disease"]
    science_kw = ["science","space","nasa","research","study","physics","biology","chemistry"]
    if any(k in t for k in economy_kw):
        return "Economy"
    if any(k in t for k in politics_kw):
        return "Politics"
    if any(k in t for k in tech_kw):
        return "Technology"
    if any(k in t for k in health_kw):
        return "Health"
    if any(k in t for k in science_kw):
        return "Science"
    return "Politics"  # default fallback

def _build_rss_index(feeds: List[str], request_headers: dict = None) -> dict:
    index = {}
    headers = request_headers or {}
    with httpx.Client(follow_redirects=True, timeout=15) as client:
        for f in feeds or []:
            try:
                r = client.get(f, headers=headers)
                content = r.text if r.status_code == 200 else ""
            except Exception:
                content = ""
            try:
                parsed = feedparser.parse(content or f)
            except Exception:
                parsed = feedparser.parse(f)
            for e in parsed.entries:
                # Index by link
                link = e.get("link")
                if link and link not in index:
                    index[link] = e
                # Index by canonicalized link
                if link:
                    try:
                        can = canonicalize_url(link)
                        if can and can not in index:
                            index[can] = e
                    except Exception:
                        pass
                # Index by entry id/guid if available
                eid = e.get("id") or e.get("guid")
                if eid and eid not in index:
                    index[eid] = e
                # Also index by normalized base of link (scheme+host+path)
                if link:
                    try:
                        from urllib.parse import urlsplit, urlunsplit
                        parts = urlsplit(link)
                        base = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, "", ""))
                        if base not in index:
                            index[base] = e
                    except Exception:
                        pass
    return index

def _rss_lookup(enrich_index: dict, url: str):
    if not enrich_index:
        return None
    # direct
    if url in enrich_index:
        return enrich_index[url]
    # try canonicalized form
    try:
        can = canonicalize_url(url)
        if can in enrich_index:
            return enrich_index[can]
    except Exception:
        pass
    # normalized base (lower-cased host, no query/fragment)
    from urllib.parse import urlsplit, urlunsplit
    try:
        parts = urlsplit(url)
        base = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, "", ""))
        if base in enrich_index:
            return enrich_index[base]
    except Exception:
        pass
    return None

def process_article_links(session, publication, run, links: List[str], cfg) -> Tuple[int,int]:
    new_count = 0
    updated_count = 0
    # simple sequential for MVP
    rss_index = _build_rss_index(cfg.get("rss_feeds"), request_headers=cfg.get("headers")) if cfg.get("rss_enrich") else {}
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        for rank, url in enumerate(links, start=1):
            # Upsert Article
            art = session.query(Article).filter_by(url_canonical=url, publication_id=publication.id).first()
            if not art:
                art = Article(publication_id=publication.id, url_canonical=url, first_seen_at=datetime.utcnow())
                session.add(art); session.flush()

            # Skim-before-pull: send conditional GET if we have cache headers
            etag = art.last_etag
            last_mod = art.last_modified
            # If rss_only, skip page fetch entirely and synthesize from RSS
            if cfg.get("rss_only") and rss_index:
                ent = _rss_lookup(rss_index, url)
                html = ""
                if not ent:
                    # No enrichment available; skip this item cleanly
                    session.add(FrontpageItem(run_id=run.id, rank=rank, url=url, is_new=False, is_updated=False))
                    continue
                title = ent.get("title")
                # author/byline
                byline = ent.get("author") or None
                if not byline and ent.get("authors"):
                    try:
                        byline = ", ".join([a.get("name") for a in ent.get("authors") if a.get("name")])
                    except Exception:
                        pass
                # published
                published = ent.get("published") or ent.get("updated")
                # media thumbnail
                media = ent.get("media_content") or ent.get("media_thumbnail") or []
                try:
                    if not media and ent.get("links"):
                        encl = [l for l in ent.get("links") if l.get("rel") == "enclosure" and l.get("type", "").startswith("image/")]
                        if encl:
                            media = [{"url": encl[0].get("href") }]
                except Exception:
                    pass
                og_image = media[0].get("url") if media else None
                text = ""
                section = None
            else:
                r = client.get(url, headers={
                **(cfg.get("headers") or {}),
                **({"If-None-Match": etag} if etag else {}),
                **({"If-Modified-Since": last_mod} if last_mod else {}),
                })

            if not cfg.get("rss_only") and r.status_code == 304:
                # unchanged
                FrontpageItem(run_id=run.id, rank=rank, url=url, is_new=False, is_updated=False)
                session.add(FrontpageItem(run_id=run.id, rank=rank, url=url, is_new=False, is_updated=False))
                continue
            if not cfg.get("rss_only") and r.status_code >= 400:
                # Try mirror first, then AMP/mobile fallback if configured
                fallback_done = False
                if cfg.get("mirror_base") and url:
                    try:
                        mirror_url = cfg.get("mirror_base") + url
                        r2 = client.get(mirror_url, headers=cfg.get("headers") or {})
                        if r2.status_code < 400 and len(r2.text) > 0:
                            r = r2
                            fallback_done = True
                    except Exception:
                        pass
                if not fallback_done and cfg.get("amp_fallback") and url:
                    try:
                        from urllib.parse import urlsplit, urlunsplit
                        parts = urlsplit(url)
                        amp_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip('/') + '/amp', parts.query, parts.fragment))
                        r2 = client.get(amp_url, headers=cfg.get("mobile_headers") or cfg.get("headers") or {})
                        if r2.status_code < 400:
                            r = r2
                            fallback_done = True
                    except Exception:
                        pass
                if not fallback_done:
                    session.add(FrontpageItem(run_id=run.id, rank=rank, url=url, is_new=False, is_updated=False))
                    continue

            if not cfg.get("rss_only"):
                html = r.text
                title, byline, published, og_image, text, section = extract_article_fields(url, html)
            if (not title or not og_image or not published or not byline) and rss_index:
                ent = _rss_lookup(rss_index, url)
                if ent:
                    title = title or ent.get("title")
                    published = published or ent.get("published") or ent.get("updated")
                    # byline/author
                    byline = byline or ent.get("author")
                    if not byline and ent.get("authors"):
                        try:
                            byline = ", ".join([a.get("name") for a in ent.get("authors") if a.get("name")])
                        except Exception:
                            pass
                    # media thumbnail
                    media = ent.get("media_content") or ent.get("media_thumbnail") or []
                    if not og_image and media:
                        og_image = media[0].get("url")
                    if not og_image and ent.get("links"):
                        try:
                            encl = [l for l in ent.get("links") if l.get("rel") == "enclosure" and l.get("type","").startswith("image/")]
                            if encl:
                                og_image = encl[0].get("href")
                        except Exception:
                            pass
            body_hash = _hash(text)
            changed = (body_hash != (art.last_body_hash or ""))

            # Save raw HTML (local disk for MVP)
            raw_ref = save_raw_html(publication.external_id, slugify(title)[:80], html)

            snap = ArticleSnapshot(
                article_id=art.id,
                fetched_at=datetime.utcnow(),
                title=title or art.title or "",
                byline=byline or art.byline or "",
                published_time=published,
                body_text=text or "",
                body_hash=body_hash,
                raw_html_ref=raw_ref,
                og_image_url=og_image,
                tag=_infer_tag(title or "", section),
            )
            session.add(snap); session.flush()

            art.title = snap.title
            art.byline = snap.byline
            art.published_time = snap.published_time
            art.last_snapshot_id = snap.id
            art.last_body_hash = body_hash
            # Guard when using rss_only (no HTTP response object)
            try:
                art.last_etag = r.headers.get("ETag")
                art.last_modified = r.headers.get("Last-Modified")
            except Exception:
                art.last_etag = art.last_etag
                art.last_modified = art.last_modified
            art.last_seen_at = datetime.utcnow()

            # Agent outbox placeholder (no processing yet)
            job = AgentJob(snapshot_id=snap.id, status="pending")
            session.add(job)

            is_new = (art.first_seen_at == art.last_seen_at)  # if first run, same timestamp
            session.add(FrontpageItem(run_id=run.id, rank=rank, url=url, is_new=is_new, is_updated=(not is_new and changed)))

            if is_new:
                new_count += 1
            elif changed:
                updated_count += 1

    return new_count, updated_count
