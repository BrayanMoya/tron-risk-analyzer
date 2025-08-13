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

if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8000"

echo Iniciando en http://%HOST%:%PORT% ...
uvicorn app.main:app --host %HOST% --port %PORT% --reload

endlocal
