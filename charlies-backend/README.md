# Charlie's Editorial Backend (MVP)

## 1) Setup
```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/html

# Edit .env if needed (ports/origins/cadence).
```

## 2) Run

```bash
uvicorn app:app --reload --port 8000
```

Scheduler runs immediately and then every CADENCE_HOURS (default 24h).

Manual trigger:
```bash
curl -X POST http://localhost:8000/publications/nyt/run
```

## 3) API quick checks

- List publications:
```bash
curl http://localhost:8000/publications
```

- Latest frontpage summary:
```bash
curl http://localhost:8000/publications/nyt/frontpage
```

- Articles (by name or id):
```bash
curl "http://localhost:8000/articles?publication=The%20New%20York%20Times&section=All"
```

- Article detail:
```bash
curl http://localhost:8000/articles/nyt-1
```

- Vote:
```bash
curl -X POST http://localhost:8000/feedback \
     -H "Content-Type: application/json" \
     -d '{"articleId":"nyt-1","action":"like"}'
```

## 4) Frontend integration

Set in your frontend .env:
```
VITE_USE_API=true
VITE_API_BASE_URL=http://localhost:8000
```

Wire api.js to call:
- GET /publications
- GET /articles?publication=<name or id>&timeRange=Today&section=All
- GET /publications/{id}/frontpage
- GET /articles/{article_id}
- POST /feedback

Fields present: title, author, publishedAt, thumbnail (og_image), category tag (Politics or Economy), approvalRate.
Score is null until agent is connected.

## 5) Notes

- Coverage via RSS (NYT homepage). HTML discovery hooks exist but disabled for MVP.
- Skim-before-pull: conditional GET via ETag/Last-Modified + body hash to avoid re-saves.
- Snapshots only when content changes.
- Agent hook: agent_job table + score table (unused for now).


