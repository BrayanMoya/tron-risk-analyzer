from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from tempfile import mkstemp
from .risk_engine.core import score_wallet
from .pdf_report.build import build_pdf
from .storage.db import maybe_init_db

load_dotenv()

AUDIT_MODE = os.getenv("AUDIT_MODE", "false").lower() == "true"

app = FastAPI(title="TRON Risk API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
