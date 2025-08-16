# app/main.py
import os
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from tempfile import mkstemp

from dotenv import load_dotenv
load_dotenv()

from .risk_engine.core import score_wallet
from .pdf_report.build import build_pdf
from .web_ui import router as web_ui_router
from .storage.snapshots import save_snapshot, load_snapshot, clear_snapshot

app = FastAPI(title="TRON Risk API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_ui_router)

@app.api_route("/health", methods=["GET", "HEAD"])
async def health(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return {"ok": True}

@app.get("/risk/{address}")
async def risk(address: str):
    try:
        result = await score_wallet(address)
        save_snapshot(address, result)
        return result
    except IndexError:
        raise HTTPException(400, detail="Respuesta de la API vacía o inesperada (IndexError).")
    except Exception as e:
        raise HTTPException(400, detail=str(e))

@app.get("/report/{address}")
async def report(address: str):
    snap = load_snapshot(address)
    if snap is None:
        snap = await score_wallet(address)
        save_snapshot(address, snap)
    path = mkstemp(suffix=".pdf")[1]
    build_pdf(address, snap, path)
    pdf = FileResponse(path, media_type="application/pdf", filename=f"tron-risk-{address}.pdf")
    clear_snapshot(address)
    return pdf