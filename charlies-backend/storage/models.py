from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from storage.db import Base

class Publication(Base):
    __tablename__ = "publication"
    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True, index=True)
    name = Column(String)
    frontpage_url = Column(String, nullable=True)
    config_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class FrontpageRun(Base):
    __tablename__ = "frontpage_run"
    id = Column(Integer, primary_key=True)
    publication_id = Column(Integer, ForeignKey("publication.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="running")
    links_found = Column(Integer, default=0)
    links_new = Column(Integer, default=0)
    links_updated = Column(Integer, default=0)
    error_json = Column(JSON, nullable=True)

class FrontpageItem(Base):
    __tablename__ = "frontpage_item"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("frontpage_run.id"))
    rank = Column(Integer)
    url = Column(String)
    is_new = Column(Integer, default=0)
    is_updated = Column(Integer, default=0)

class Article(Base):
    __tablename__ = "article"
    id = Column(Integer, primary_key=True)
    publication_id = Column(Integer, ForeignKey("publication.id"))
    url_canonical = Column(String, index=True)
    title = Column(String)
    byline = Column(String)
    published_time = Column(String)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    last_snapshot_id = Column(Integer, nullable=True)
    last_body_hash = Column(String, nullable=True)
    last_etag = Column(String, nullable=True)
    last_modified = Column(String, nullable=True)
    votes_up = Column(Integer, default=0)
    votes_down = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("publication_id","url_canonical", name="u_article_pub_url"),)

class ArticleSnapshot(Base):
    __tablename__ = "article_snapshot"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("article.id"))
    fetched_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String)
    byline = Column(String)
    published_time = Column(String)
    body_text = Column(Text)
    body_hash = Column(String, index=True)
    raw_html_ref = Column(String)
    og_image_url = Column(String, nullable=True)
    tag = Column(String, default="Politics")  # MVP two-category scope

class Score(Base):
    __tablename__ = "score"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("article_snapshot.id"), unique=True)
    composite = Column(Numeric, nullable=True)
    version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CriterionScore(Base):
    __tablename__ = "criterion_score"
    id = Column(Integer, primary_key=True)
    score_id = Column(Integer, ForeignKey("score.id"))
    criterion = Column(String)
    value = Column(Numeric)
    rationale = Column(Text, nullable=True)

class AgentJob(Base):
    __tablename__ = "agent_job"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("article_snapshot.id"), unique=True)
    status = Column(String, default="pending")  # pending, processing, done, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

