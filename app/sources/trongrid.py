import httpx

TRONGRID = "https://api.trongrid.io"
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


async def account_overview(address_b58: str) -> dict:
    url = f"{TRONGRID}/v1/accounts/{address_b58}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def account_transactions(address_b58: str, limit=50, fingerprint=None) -> dict:
    params = {"limit": limit}
    if fingerprint:
        params["fingerprint"] = fingerprint
    url = f"{TRONGRID}/v1/accounts/{address_b58}/transactions"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def account_trc20_transfers(address_b58: str, limit=200, min_timestamp=None, max_timestamp=None) -> dict:
    params = {"limit": limit}
    if min_timestamp is not None: params["min_timestamp"] = min_timestamp
    if max_timestamp is not None: params["max_timestamp"] = max_timestamp
    url = f"{TRONGRID}/v1/accounts/{address_b58}/transactions/trc20"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()
