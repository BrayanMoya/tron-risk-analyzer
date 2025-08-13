@echo off
setlocal
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
)

uvicorn app.main:app --host %HOST% --port %PORT% --reload
endlocal
