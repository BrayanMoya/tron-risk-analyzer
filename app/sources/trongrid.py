import asyncio
import os
import httpx

TRONGRID = "https://api.trongrid.io"
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "").strip()


def _build_headers() -> dict:
    headers = {}
    if TRONGRID_API_KEY:
        headers["TRON-PRO-API-KEY"] = TRONGRID_API_KEY
    return headers


async def _get(url: str, params: dict | None = None) -> dict:
    headers = _build_headers()
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        r = await client.get(url, params=params)
        if r.status_code == 429 and TRONGRID_API_KEY:
            await asyncio.sleep(0.8)
            r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def account_overview(address_b58: str) -> dict:
    url = f"{TRONGRID}/v1/accounts/{address_b58}"
    return await _get(url)


async def account_transactions(address_b58: str, limit=50, fingerprint=None) -> dict:
    params = {"limit": limit}
    if fingerprint:
        params["fingerprint"] = fingerprint
    url = f"{TRONGRID}/v1/accounts/{address_b58}/transactions"
    return await _get(url, params=params)


async def account_trc20_transfers(address_b58: str, limit=200, min_timestamp=None, max_timestamp=None) -> dict:
    params = {"limit": limit}
    if min_timestamp is not None: params["min_timestamp"] = min_timestamp
    if max_timestamp is not None: params["max_timestamp"] = max_timestamp
    url = f"{TRONGRID}/v1/accounts/{address_b58}/transactions/trc20"
    j = await _get(url, params=params) or {}
    data = j.get("data")
    if not isinstance(data, list):
        data = j.get("token_transfers")
        if not isinstance(data, list):
            data = []
    j["data"] = data
    return j
