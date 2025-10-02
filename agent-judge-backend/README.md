Agent Judge (Standalone)

Overview
This is a standalone backend service that analyzes a single news article URL and returns 11 criteria scores (0–10), concise rationales, flags, and an overall average. It is designed to be integrated later with Charlie's Editorial MVP, but runs independently now.

Endpoints
- GET /health: Health check.
- POST /analyze: Analyze an article by URL with an inference parameter.

Request (POST /analyze)
{
  "url": "https://example.com/article",
  "inference": 0.3
}

Response (shape, truncated)
{
  "meta": {"title": "...", "author": "...", "thumbnail": "...", "fetched_at": "ISO-8601"},
  "scores": [{"criterion":"clarity_coherence","score":0,"rationale":"...","flags":[]}],
  "overall": {"average": 0, "method": "mean_of_subscores"},
  "headline_summary": {"one_sentence_summary":"...", "headline_body_match": true},
  "raw": {"url":"...", "word_count": 0},
  "version": "v1-2025-10-01",
  "inference": 0.3
}

Setup
1) Create and activate venv, then install deps:
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2) Create .env from example:
   cp .env.example .env
   # Edit with your OpenAI key and basic auth credentials

3) Run the server:
   uvicorn src.app:app --reload --port 8100

4) Create DB tables (first run happens automatically when using the API). If needed:
   python -c "from src.db import init_engine_and_session; from src.models import AnalysisCache; e,_=init_engine_and_session(); AnalysisCache.metadata.create_all(e)"

Environment
- OPENAI_API_KEY: Required for analysis.
- ANALYZER_USER / ANALYZER_PASS: Basic auth credentials.
- DATABASE_URL: Defaults to sqlite:///./data/app.db
- AGENT_VERSION: Optional version tag, defaults to v1.

Notes
- The /analyze route currently returns a stub response; scoring and feature extraction will be added next.
- Language: The service returns rationales in the article language (PT/EN) once scoring is enabled.


