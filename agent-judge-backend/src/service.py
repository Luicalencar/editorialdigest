from datetime import datetime, timezone
import httpx
from .config import get_settings
from .db import init_engine_and_session, session_scope
from .models import AnalysisCache
from .extract import extract_meta_and_text
from .features import compute_features
from .openai_client import call_openai


_engine, SessionLocal = init_engine_and_session()


CRITERIA_ORDER = [
    "clarity_coherence",
    "five_w_one_h",
    "attribution_evidence",
    "hedging_overclaim",
    "balance_opposing",
    "inversion_touch",
    "context_proportionality",
    "multidisciplinarity",
    "civic_utility",
    "transparency_cues",
    "language_credibility",
]


def analyze_url(url: str, inference: float = 0.3, force: bool = False, mode: str = "editors_bench") -> dict:
    settings = get_settings()
    url = str(url)
    cache_key = (url, settings.agent_version, f"{mode}")
    with session_scope(SessionLocal) as s:
        cached = s.query(AnalysisCache).filter_by(url=cache_key[0], version=cache_key[1], inference_key=cache_key[2]).first()
        if cached and not force:
            out = dict(cached.result_json)
            # Sanitize any stale rationales before returning
            try:
                from .openai_client import _sanitize_rationale
                for s in out.get("scores", []) or []:
                    s["rationale"] = _sanitize_rationale(s.get("rationale", ""))
            except Exception:
                pass
            out["fromCache"] = True
            return out

    # Fetch page
    html = None
    with httpx.Client(follow_redirects=True, timeout=25) as client:
        r = client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        if r.status_code < 400 and r.text:
            html = r.text
        else:
            # Try r.jina.ai mirror as a fallback
            try:
                from urllib.parse import urlsplit
                scheme = urlsplit(url).scheme or "https"
                mirror = f"https://r.jina.ai/{scheme}://{urlsplit(url).netloc}{urlsplit(url).path}"
                r2 = client.get(mirror, timeout=25)
                if r2.status_code < 400 and r2.text:
                    html = r2.text
                else:
                    raise RuntimeError(f"fetch_failed status={r.status_code}")
            except Exception:
                raise RuntimeError(f"fetch_failed status={r.status_code}")
    if not html:
        raise RuntimeError("empty_html")

    meta, text = extract_meta_and_text(url, html)
    features = compute_features(text)
    features["paragraph_count"] = len(features.get("paragraphs", []))
    features["headline"] = meta.get("title")

    rules = "(11 criteria and rules per spec; condensed in final prompt)"
    model_json = call_openai(text, {**meta, "published": ""}, features, rules, mode=mode)

    # Normalize and compute overall if needed
    scores = model_json.get("scores") or []
    if scores:
        avg = round(sum([float(x.get("score", 0)) for x in scores]) / len(scores), 2)
    else:
        avg = 0.0

    result = {
        "meta": {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "thumbnail": meta.get("thumbnail", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
        "scores": scores,
        "overall": {"average": avg, "method": "mean_of_subscores"},
        "headline_summary": model_json.get("headline_summary", {"one_sentence_summary": "", "headline_body_match": True}),
        "raw": {"url": url, "word_count": features.get("word_count", 0)},
        "version": settings.agent_version,
        "fromCache": False,
        "mindsetEcho": model_json.get("_mindset"),
        "mode": mode,
        "intent": model_json.get("_intent"),
        "necessity_map": model_json.get("_necessity_map"),
    }

    with session_scope(SessionLocal) as s:
        existing = s.query(AnalysisCache).filter_by(url=cache_key[0], version=cache_key[1], inference_key=cache_key[2]).first()
        if existing:
            existing.result_json = result
            existing.raw_response = str(model_json)
        else:
            row = AnalysisCache(
                url=cache_key[0],
                version=cache_key[1],
                inference_key=cache_key[2],
                result_json=result,
                raw_response=str(model_json),
            )
            s.add(row)

    return result


