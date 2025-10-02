from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta, timezone
from storage.db import init_engine_and_session, session_scope
from storage.models import Publication, Article, ArticleSnapshot, Score, FrontpageRun, FrontpageItem

router = APIRouter()
_engine, SessionLocal = init_engine_and_session()

@router.get("")
def list_articles(publication: str = Query(...), timeRange: str = "Today", section: str = "All"):
    with session_scope(SessionLocal) as s:
        pub = s.query(Publication).filter_by(name=publication).first()
        if not pub:
            pub = s.query(Publication).filter_by(external_id=publication).first()
        if not pub:
            return {"articles": [], "notice": "Publication not found"}

        # Determine which frontpage run to use: latest for Today, previous for Yesterday
        runs = s.query(FrontpageRun).filter_by(publication_id=pub.id).order_by(FrontpageRun.started_at.desc()).all()
        run = runs[0] if runs else None
        if timeRange == "Yesterday" and len(runs) > 1:
            run = runs[1]
        if not run:
            return {"articles": [], "dateISO": None, "sections": ["All"]}

        # Get the 15 ranked URLs from this run
        items = s.query(FrontpageItem).filter_by(run_id=run.id).order_by(FrontpageItem.rank.asc()).all()

        out = []
        sections_set = set()
        for it in items:
            a = s.query(Article).filter_by(publication_id=pub.id, url_canonical=it.url).first()
            if not a:
                continue
            snap = s.query(ArticleSnapshot).filter_by(id=a.last_snapshot_id).first()
            cat = (snap.tag if snap else None) or "Politics"
            sections_set.add(cat)
            if section != "All" and cat != section:
                continue
            out.append({
                "id": f"{pub.external_id}-{a.id}",
                "title": (snap.title if snap and snap.title else a.title),
                "author": (snap.byline if snap and snap.byline else a.byline),
                "thumbnail": (snap.og_image_url if snap else None),
                "score": None,
                "approvalRate": _approval(a.votes_up, a.votes_down),
                "liked": False, "disliked": False,
                "publishedAt": a.published_time,
                "category": cat
            })

        date_iso = run.started_at.date().isoformat() if run and run.started_at else None
        sections = ["All"] + sorted(sections_set)
        return {"articles": out, "dateISO": date_iso, "sections": sections}

@router.get("/{article_id}")
def article_detail(article_id: str):
    with session_scope(SessionLocal) as s:
        pub_key, dbid = article_id.split("-", 1)
        art = s.get(Article, int(dbid))
        if not art:
            raise HTTPException(404, "Not found")
        snap = s.get(ArticleSnapshot, art.last_snapshot_id)
        score = s.query(Score).filter_by(snapshot_id=art.last_snapshot_id).first()
        return {
            "article": {
                "id": article_id,
                "title": art.title,
                "author": art.byline,
                "thumbnail": snap.og_image_url if snap else None,
                "publishedAt": art.published_time,
                "category": snap.tag if snap else None,
                "url": art.url_canonical,
                "text": (snap.body_text if snap else None)
            },
            "score": {
                "composite": score.composite if score else None,
                "breakdown": []
            }
        }

@router.get("/{article_id}/history")
def article_history(article_id: str):
    with session_scope(SessionLocal) as s:
        _, dbid = article_id.split("-", 1)
        snaps = s.query(ArticleSnapshot).filter_by(article_id=int(dbid)).order_by(ArticleSnapshot.fetched_at.asc()).all()
        return {
            "history": [
                {
                    "snapshotId": sn.id,
                    "fetchedAt": sn.fetched_at.isoformat(),
                    "title": sn.title,
                    "publishedAt": sn.published_time,
                    "ogImage": sn.og_image_url,
                    "tag": sn.tag
                } for sn in snaps
            ]
        }

def _approval(up: int, down: int):
    total = (up or 0)+(down or 0)
    if total == 0: return 0
    return round(100*(up or 0)/total)
