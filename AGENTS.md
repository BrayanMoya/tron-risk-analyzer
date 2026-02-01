# AI Agent Guide - TRON Risk Check

This document provides a detailed technical overview of the project to help AI agents (such as OpenCode, Claude, GPT, etc.) collaborate on development, maintenance, and improvements.

## 1. System Overview
This project is a risk analyzer for TRON network addresses, focused on USDT (TRC-20). It uses a **FastAPI** architecture and connects to external APIs (**TronGrid** and **TronScan**) to collect on-chain data and apply a heuristic scoring engine.

## 2. Code Map
To navigate efficiently, the agent should know each module's responsibilities:

- `app/main.py`: API entry point. Handles routes, middleware, and environment loading.
- `app/risk_engine/`:
    - `core.py`: Main orchestration logic for analysis and scoring.
    - `weights.py`: Defines the weights (points) assigned to each risk signal.
- `app/sources/`: Infrastructure layer for external API communication.
    - `tronscan.py`: TronScan API client (fraud detection, blacklist).
    - `trongrid.py`: TronGrid API client (TRC20 transfers, balances).
- `app/pdf_report/`: Visual report generation logic using `fpdf2`.
- `app/storage/`: Temporary persistence (snapshots) to avoid redundant API calls during report generation.
- `app/web_ui.py` & `app/templates/`: Minimal web UI for end users.

## 3. Risk Engine Logic
The final score is a weighted sum (capped at 100) based on:
1.  **Direct Blacklist**: Immediate detection of inclusion in Tether's official blacklist (USDT).
2.  **Fraud Flags**: External signals of malicious behavior reported by explorers.
3.  **1-hop Analysis**: Verification of counterparties (addresses it interacted with). If the wallet interacts with high-risk addresses, its score increases.
4.  **Dust Activity**: Identification of micro-transaction patterns that suggest automation or dusting attacks.

## 4. Common Task Instructions

### How to add a new risk signal:
1.  Define the new weight in `app/risk_engine/weights.py`.
2.  Implement the detection logic in `app/risk_engine/core.py` (inside `score_wallet`).
3.  Make sure the reason is included in the `reasons` list of the result.

### How to modify the PDF report UI:
1.  Go to `app/pdf_report/build.py`.
2.  Use `FPDF` methods to adjust the layout.
3.  Data is injected from the `snap` object (analysis snapshot).

### How to debug connections:
- Check the functions in `app/sources/`.
- All requests use async `httpx`.
- If an API returns errors, verify API keys in `.env`.

## 5. Development Conventions
- **Async**: Prefer `async/await` for all I/O operations.
- **Typing**: Use `typing` (List, Dict, Any, etc.) to keep code clear.
- **Security**: Never hardcode contract addresses or API keys. Use `os.getenv`.
- **Decimals**: For financial amounts (USDT), always use `Decimal` to avoid floating point precision errors.

## 6. Useful Commands
- **Start server**: `python -m uvicorn app.main:app --reload` (or use `run.bat` on Windows).
- **Health check**: `GET /health`.
- **Direct analysis**: `GET /risk/{address}`.

---
*Agent note: If you find missing test coverage, prioritize creating a `tests/` directory and use `pytest` to validate the risk engine.*
