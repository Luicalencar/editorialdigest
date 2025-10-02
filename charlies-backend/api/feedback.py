from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from storage.db import init_engine_and_session, session_scope
from storage.models import Article

router = APIRouter()
_engine, SessionLocal = init_engine_and_session()

class FeedbackBody(BaseModel):
    articleId: str
    action: str  # 'like'|'dislike'|'undo-like'|'undo-dislike'

@router.post("")
def post_feedback(body: FeedbackBody):
    with session_scope(SessionLocal) as s:
        try:
            _, dbid = body.articleId.split("-", 1)
            art = s.get(Article, int(dbid))
            if not art:
                raise HTTPException(404, "Article not found")
        except Exception:
            raise HTTPException(400, "Invalid articleId")

        if body.action == "like":
            # For MVP we don't store per-user, just aggregate counts
            art.votes_up = (art.votes_up or 0) + 1
        elif body.action == "dislike":
            art.votes_down = (art.votes_down or 0) + 1
        elif body.action == "undo-like":
            art.votes_up = max(0, (art.votes_up or 0) - 1)
        elif body.action == "undo-dislike":
            art.votes_down = max(0, (art.votes_down or 0) - 1)
        else:
            raise HTTPException(400, "Invalid action")

        up, down = art.votes_up or 0, art.votes_down or 0
        approval = 0 if (up+down)==0 else round(100*up/(up+down))
        return {"votesUp": up, "votesDown": down, "approvalRate": approval, "liked": None, "disliked": None}

