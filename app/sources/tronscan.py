import os, httpx

TRONSCAN_BASE = "https://apilist.tronscanapi.com"
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

def _headers():
    key = os.getenv("TRONSCAN_API_KEY", "")
    h = {}
    if key:
        h["TRON-PRO-API-KEY"] = key
    return h

async def check_account_security(address: str) -> dict:
    url = f"{TRONSCAN_BASE}/api/security/account/data"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params={"address": address}, headers=_headers())
        r.raise_for_status()
        return r.json()


async def check_stablecoin_blacklist(address: str) -> dict:
    url = f"{TRONSCAN_BASE}/api/stableCoin/blackList"
    params = {"blackAddress": address, "start": 0, "limit": 1, "sort": 2, "direction": 2}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params, headers=_headers())
        r.raise_for_status()
        return r.json()


async def trc20_transfers(address: str, start=0, limit=200) -> dict:
    url = f"{TRONSCAN_BASE}/api/transfer/trc20"
    params = {"address": address, "trc20Id": USDT_CONTRACT, "start": start, "limit": limit, "reverse": "true"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params, headers=_headers())
        r.raise_for_status()
        return r.json()
