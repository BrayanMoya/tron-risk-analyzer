import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = "sqlite:///./audits.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def maybe_init_db(audit_enabled: bool):
    if not audit_enabled:
        return
    from .models import Analysis  # noqa
    Base.metadata.create_all(bind=engine)
