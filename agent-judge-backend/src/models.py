from sqlalchemy import Column, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_mixin
from .db import Base


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"
    id = Column(Integer, primary_key=True)
    url = Column(String, index=True)
    version = Column(String, index=True)
    inference_key = Column(String, index=True)
    result_json = Column(JSON)
    raw_response = Column(Text)
    __table_args__ = (UniqueConstraint("url", "version", "inference_key", name="u_cache_key"),)


