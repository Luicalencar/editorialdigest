from fastapi import APIRouter, Query
from datetime import datetime, timedelta, timezone
from storage.db import init_engine_and_session, session_scope
from storage.models import Publication, Article, ArticleSnapshot, Score, FrontpageRun, FrontpageItem

router = APIRouter()
_engine, SessionLocal = init_engine_and_session()

def _approval(up: int, down: int):
    total = (up or 0) + (down or 0)
    if total == 0:
        return 0
    return round(100 * (up or 0) / total)

def _select_run(s, pub_id: int, time_range: str):
    runs = s.query(FrontpageRun).filter_by(publication_id=pub_id).order_by(FrontpageRun.started_at.desc()).all()
    run = runs[0] if runs else None
    if time_range == "Yesterday" and len(runs) > 1:
        run = runs[1]
    return run

@router.get("/daily")
def daily_metrics(
    publication: str = Query(...),
    section: str = "All",
    metric: str = "approvalRate",  # approvalRate | composite
    timeRange: str = "Today",
):
    # Align to run-based selection for Today/Yesterday

    with session_scope(SessionLocal) as s:
        pub = s.query(Publication).filter_by(name=publication).first()
        if not pub:
            pub = s.query(Publication).filter_by(external_id=publication).first()
        if not pub:
            return {"metric": metric, "current": None, "previous": None, "delta": None}

        def collect_avg_for_run(run):
            if not run:
                return None
            vals = []
            items = s.query(FrontpageItem).filter_by(run_id=run.id).order_by(FrontpageItem.rank.asc()).all()
            for it in items:
                a = s.query(Article).filter_by(publication_id=pub.id, url_canonical=it.url).first()
                if not a:
                    continue
                snap = s.query(ArticleSnapshot).filter_by(id=a.last_snapshot_id).first()
                if section != "All":
                    cat = (snap.tag if snap else None) or "Politics"
                    if cat != section:
                        continue
                if metric == "approvalRate":
                    vals.append(_approval(a.votes_up, a.votes_down))
                elif metric == "composite":
                    sc = s.query(Score).filter_by(snapshot_id=a.last_snapshot_id).first()
                    if sc and sc.composite is not None:
                        try:
                            vals.append(float(sc.composite))
                        except Exception:
                            pass
            if not vals:
                return None
            return sum(vals) / len(vals)

        current_run = _select_run(s, pub.id, timeRange)
        previous_run = None
        if current_run:
            # previous is the immediately earlier run
            previous_run = s.query(FrontpageRun).filter(FrontpageRun.publication_id==pub.id, FrontpageRun.started_at < current_run.started_at).order_by(FrontpageRun.started_at.desc()).first()

        current = collect_avg_for_run(current_run)
        previous = collect_avg_for_run(previous_run)
        delta = None
        if current is not None and previous is not None:
            delta = current - previous
        return {
            "metric": metric,
            "publication": publication,
            "section": section,
            "timeRange": timeRange,
            "current": current,
            "previous": previous,
            "delta": delta,
        }


