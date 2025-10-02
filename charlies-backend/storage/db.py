import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
_engine = None
_SessionLocal = None

def init_engine_and_session():
    global _engine, _SessionLocal
    url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, echo=False, future=True, connect_args=connect_args)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal

@contextmanager
def session_scope(SessionLocal=None):
    session = (SessionLocal or _SessionLocal)()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

