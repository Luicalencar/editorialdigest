from fastapi import APIRouter, Depends, HTTPException
from storage.db import session_scope
from storage.db import init_engine_and_session
from storage.models import Publication, FrontpageRun, FrontpageItem, Article
from publications.registry import list_publications
from scheduler import trigger_publication_now

router = APIRouter()
_engine, SessionLocal = init_engine_and_session()

@router.get("")
def list_pubs():
    pubs = list_publications()
    # For MVP, earliest/latest unknown until first run; return placeholders.
    return {
        "publications": [p["name"] for p in pubs],
        "ids": [p["id"] for p in pubs],
        "available_range": None
    }

@router.post("/{pub_id}/run")
def run_now(pub_id: str):
    trigger_publication_now(SessionLocal, pub_id)
    return {"ok": True, "triggered": pub_id}
    
@router.get("/{pub_id}/frontpage")
def frontpage(pub_id: str, limit: int = 15):
    with session_scope(SessionLocal) as s:
        pub = s.query(Publication).filter_by(external_id=pub_id).first()
        if not pub:
            raise HTTPException(404, "Publication not found")
        run = s.query(FrontpageRun).filter_by(publication_id=pub.id).order_by(FrontpageRun.started_at.desc()).first()
        if not run:
            return {"articles": [], "dateISO": None}
        items = s.query(FrontpageItem).filter_by(run_id=run.id).order_by(FrontpageItem.rank.asc()).limit(limit).all()
        # map URLs to article meta
        out = []
        for it in items:
            art = s.query(Article).filter_by(publication_id=pub.id, url_canonical=it.url).first()
            if not art:
                continue
            out.append({
                "id": f"{pub.external_id}-{art.id}",
                "title": art.title,
                "author": art.byline,
                "score": None,  # agent later
                "approvalRate": _approval(art.votes_up, art.votes_down),
                "liked": False,
                "disliked": False,
                "publishedAt": art.published_time,
                "thumbnail": None,  # taken from latest snapshot in article detail
                "category": None,   # taken from snapshot.tag in detail
            })
        return {"articles": out, "dateISO": run.started_at.date().isoformat()}

def _approval(up: int, down: int):
    total = (up or 0) + (down or 0)
    if total == 0: 
        return 0
    return round(100 * (up or 0) / total)

