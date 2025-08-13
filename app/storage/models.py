from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from .db import Base

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    risk_score = Column(Integer)
    risk_level = Column(String)
    reasons = Column(JSON)
    summary = Column(String)
    snapshot = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
