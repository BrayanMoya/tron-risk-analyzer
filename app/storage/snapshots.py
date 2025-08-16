import os, json, hashlib, time
from pathlib import Path
from typing import Any, Optional

SNAPSHOT_DIR = Path(os.getenv("SNAPSHOT_DIR", "/tmp/tron_risk_snapshots"))
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

TTL_MIN = int(os.getenv("SNAPSHOT_TTL_MINUTES", "120"))  # 2h por defecto

def _fname(address: str) -> Path:
    # archivo solo por hash para evitar problemas con caracteres
    h = hashlib.sha256(address.strip().encode("utf-8")).hexdigest()
    return SNAPSHOT_DIR / f"{h}.json"

def save_snapshot(address: str, payload: dict) -> str:
    path = _fname(address)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), default=str)
    os.replace(tmp, path)  # atómico
    return str(path)

def _is_fresh(path: Path) -> bool:
    if TTL_MIN <= 0:
        return True
    try:
        age = time.time() - path.stat().st_mtime
        return age <= TTL_MIN * 60
    except FileNotFoundError:
        return False

def load_snapshot(address: str) -> Optional[dict]:
    path = _fname(address)
    print(f"snapshot path: {path}")
    if not path.exists():
        return None
    if not _is_fresh(path):
        try: path.unlink(missing_ok=True)
        except Exception: pass
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def clear_snapshot(address: str) -> None:
    path = _fname(address)
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
