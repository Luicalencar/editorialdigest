import os, yaml
from pathlib import Path
from typing import List, Dict
from ingestion.discover import discover_links
from ingestion.snapshots import process_article_links
from storage.db import session_scope
from storage.models import Publication, FrontpageRun
from utils.logging import get_logger

log = get_logger(__name__)
CONFIG_DIR = Path(__file__).parent / "configs"

def list_publications() -> List[Dict]:
    pubs = []
    for yml in CONFIG_DIR.glob("*.yaml"):
        data = yaml.safe_load(yml.read_text())
        pubs.append({"id": data["id"], "name": data["name"], "config": data})
    enabled = [p.strip() for p in os.getenv("PUBLICATIONS", "").split(",") if p.strip()]
    if enabled:
        pubs = [p for p in pubs if p["id"] in enabled]
    return pubs

def get_publication_config(pub_id: str) -> Dict:
    path = CONFIG_DIR / f"{pub_id}.yaml"
    if not path.exists():
        raise ValueError(f"No config for publication {pub_id}")
    return yaml.safe_load(path.read_text())

def ensure_publication_record(session, cfg: Dict) -> Publication:
    pub = session.query(Publication).filter_by(external_id=cfg["id"]).first()
    if not pub:
        pub = Publication(
            external_id=cfg["id"],
            name=cfg["name"],
            frontpage_url=cfg.get("frontpage_url"),
            config_json=cfg,
        )
        session.add(pub)
        session.flush()
    return pub

def run_publication_harvest(SessionLocal, pub_id: str):
    cfg = get_publication_config(pub_id)
    with session_scope(SessionLocal) as session:
        pub = ensure_publication_record(session, cfg)
        run = FrontpageRun(publication_id=pub.id, status="running")
        session.add(run); session.flush()
        try:
            links = discover_links(cfg)  # merged/deduped from sources
            run.links_found = len(links)
            new_count, updated_count = process_article_links(session, pub, run, links, cfg)
            run.links_new = new_count
            run.links_updated = updated_count
            run.status = "ok"
        except Exception as e:
            run.status = "error"
            run.error_json = {"msg": str(e)}
            log.exception("Harvest error")

