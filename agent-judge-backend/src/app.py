import os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv
from .config import get_settings
from .schemas import AnalyzeRequest, AnalyzeResponse
from .service import analyze_url
from .db import init_engine_and_session
from .models import AnalysisCache
from fastapi.responses import JSONResponse

load_dotenv()

security = HTTPBasic()

settings = get_settings()

app = FastAPI(title="Agent Judge", version=settings.agent_version)

# CORS: allow local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB is initialized
_engine, _SessionLocal = init_engine_and_session()
try:
    AnalysisCache.__table__.create(bind=_engine, checkfirst=True)
except Exception:
    pass

def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (credentials.username == settings.analyzer_user and credentials.password == settings.analyzer_pass):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/health")
def health():
    return {"ok": True, "version": settings.agent_version}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest, _auth=Depends(require_basic_auth)):
    try:
        return analyze_url(body.url, force=body.force, mode=body.mode)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error":"internal_error","detail":str(e)})


