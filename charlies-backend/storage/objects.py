import os, uuid
from pathlib import Path

BASE = Path(os.getenv("RAW_HTML_DIR","./data/html")).resolve()
BASE.mkdir(parents=True, exist_ok=True)

def save_raw_html(pub_id: str, slug: str, html: str) -> str:
    fname = f"{pub_id}-{slug}-{uuid.uuid4().hex}.html"
    path = BASE / fname
    path.write_text(html, encoding="utf-8")
    return str(path)


