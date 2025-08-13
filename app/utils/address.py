import hashlib, base58

def tron_base58_to_hex(addr_b58: str) -> str:
    raw = base58.b58decode(addr_b58)
    body, checksum = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4] != checksum:
        raise ValueError("TRON address checksum inválido")
    if body[0] != 0x41:
        raise ValueError("Prefijo TRON inválido (0x41)")
    return body.hex()

def tron_hex_to_base58(hex_addr: str) -> str:
    hex_addr = hex_addr.lower()
    if hex_addr.startswith("0x"):
        hex_addr = hex_addr[2:]
    body = bytes.fromhex(hex_addr)
    if not body.startswith(b'\x41'):
        body = b'\x41' + body[-20:]
    checksum = hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4]
    return base58.b58encode(body + checksum).decode()
