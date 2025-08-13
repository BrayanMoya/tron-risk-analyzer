from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from tempfile import mkstemp
from .risk_engine.core import score_wallet
from .pdf_report.build import build_pdf
from .storage.db import maybe_init_db
from .web_ui import router as web_ui_router
from sqlalchemy import func
from .storage.db import SessionLocal
from .storage.models import Analysis

load_dotenv()

AUDIT_MODE = os.getenv("AUDIT_MODE", "false").lower() == "true"

app = FastAPI(title="TRON Risk API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_ui_router)

@app.on_event("startup")
async def _startup():
    maybe_init_db(AUDIT_MODE)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/risk/{address}")
async def risk(address: str):
    try:
        result = await score_wallet(address, audit=AUDIT_MODE)
        return result
    except Exception as e:
        raise HTTPException(400, detail=str(e))

@app.get("/report/{address}")
async def report(address: str):
    result = await score_wallet(address, audit=AUDIT_MODE)
    path = mkstemp(suffix=".pdf")[1]
    build_pdf(address, result, path)
    return FileResponse(path, media_type="application/pdf", filename=f"tron-risk-{address}.pdf")

@app.get("/debug/audit-status")
def audit_status():
    db = SessionLocal()
    try:
        total = db.query(func.count(Analysis.id)).scalar()
        return {
            "AUDIT_MODE_env": os.getenv("AUDIT_MODE"),
            "AUDIT_MODE_active": AUDIT_MODE,
            "CACHE_MINUTES": os.getenv("CACHE_MINUTES", "15"),
            "rows_in_db": total
        }
    finally:
        db.close()