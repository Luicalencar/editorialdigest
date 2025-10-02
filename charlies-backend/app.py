import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from storage.db import init_engine_and_session, Base
from storage.models import *  # register models
from api.publications import router as pubs_router
from api.articles import router as articles_router
from api.feedback import router as feedback_router
from api.metrics import router as metrics_router
from scheduler import start_scheduler

ALLOWED = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="Charlie's Editorial Backend", version="0.1.0")

if ALLOWED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.on_event("startup")
def on_startup():
    engine, SessionLocal = init_engine_and_session()
    Base.metadata.create_all(bind=engine)
    start_scheduler(SessionLocal)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(pubs_router, prefix="/publications", tags=["publications"])
app.include_router(articles_router, prefix="/articles", tags=["articles"])
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])

