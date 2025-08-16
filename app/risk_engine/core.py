from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Set
from decimal import Decimal, InvalidOperation
import os

from ..sources.tronscan import check_account_security, check_stablecoin_blacklist, trc20_transfers
from ..sources.trongrid import account_overview, account_trc20_transfers, USDT_CONTRACT
from .weights import W


CACHE_MINUTES = int(os.getenv("CACHE_MINUTES", "15"))
DUST_MICRO_USDT = Decimal(os.getenv("DUST_MICRO_USDT", "0.1"))
DUST_SMALL_USDT = Decimal(os.getenv("DUST_SMALL_USDT", "1.0"))
DUST_MIN_EVENTS = int(os.getenv("DUST_MIN_EVENTS", "3"))
USDT_CONTRACT_UP = USDT_CONTRACT.upper()
USDT_MAX_EVENT = Decimal("1e12")  # umbral sanitario por evento


def fmt_amount(d: Decimal, places=2) -> str:
    # 2 decimales + separador de miles, sin notación científica
    q = Decimal(10) ** -places
    try:
        val = d.quantize(q)
        return format(val, ",f")  # p.ej. 359,011.06
    except Exception:
        return "0.00"

def fmt_time(ms: int | None) -> str | None:
    if not ms:
        return None
    dt = datetime.fromtimestamp(ms/1000, tz=timezone.utc)
    hour = dt.strftime("%I").lstrip("0") or "0"      # 03 -> 3
    minute = dt.strftime("%M")                       # 05
    ampm = dt.strftime("%p").lower()                 # am/pm
    return f"{dt.strftime('%Y-%m-%d')}, {hour}:{minute} {ampm}"

def build_basic_info(tron_account: dict) -> dict:
    def pick(d: dict) -> dict:
        if not isinstance(d, dict):
            return {}
        if "data" in d:
            inner = d.get("data")
            if isinstance(inner, dict):
                return inner
            if isinstance(inner, list) and inner:
                return inner[0]
        return d  # ya es objeto plano

    obj = pick(tron_account or {})
    balance = obj.get("balance")
    create_ts = obj.get("create_time") or obj.get("createTime")
    last_op_ts = obj.get("latest_opration_time") or obj.get("latest_operation_time")

    return {
        "balance_trx_raw": balance,
        "created_at": fmt_time(create_ts) if create_ts else None,
        "last_operation_at": fmt_time(last_op_ts) if last_op_ts else None,
    }

def build_summary(level: str, reasons: List[Dict[str, Any]]) -> str:
    if not reasons:
        return "No se detectaron señales de riesgo en las verificaciones básicas."
    top = ", ".join(sorted({r["code"] for r in reasons}))
    return f"Nivel {level}. Señales principales: {top}."

def _extract_counterparties_trc20(items: List[dict], self_addr: str) -> Tuple[Set[str], Set[str]]:
    ins, outs = set(), set()
    for it in items:
        frm = (it.get("from") or it.get("transfer_from") or "").strip()
        to = (it.get("to") or it.get("transfer_to") or "").strip()
        if frm and frm != self_addr: ins.add(frm)  # desde otros hacia mí
        if to and to != self_addr: outs.add(to)  # desde mí hacia otros
    return ins, outs

async def _batch_security_check(addresses: Set[str]) -> Set[str]:
    risky = set()
    for a in addresses:
        try:
            sec = await check_account_security(a)
            if sec.get("is_black_list") or sec.get("has_fraud_transaction"):
                risky.add(a); continue
            bl = await check_stablecoin_blacklist(a)
            if bl.get("total", 0) > 0:
                risky.add(a)
        except Exception:
            pass
    return risky

def _is_usdt_trc20(it: dict) -> bool:
    addr = (it.get("token_info", {}) or {}).get("address") or it.get("contract_address")
    return (addr or "").upper() == USDT_CONTRACT_UP

def _normalize_amount_usdt(it) -> Decimal:
    try:
        val = Decimal(str(it.get("value", "0")))
        dec = int((it.get("token_info", {}) or {}).get("decimals") or it.get("decimals") or 6)
        amt = val / (Decimal(10) ** dec)
        # descarta outliers imposibles
        if amt <= 0 or amt > USDT_MAX_EVENT:
            raise InvalidOperation("USDT outlier")
        return amt
    except Exception:
        return Decimal("0")

def _aggregate_flows_trc20(items: List[dict], self_addr: str):
    inflow = Decimal("0"); outflow = Decimal("0")
    first_ts = None; last_ts = None
    for it in items:
        ts = it.get("block_timestamp") or it.get("timestamp")
        if ts is not None:
            first_ts = ts if not first_ts or ts < first_ts else first_ts
            last_ts  = ts if not last_ts  or ts > last_ts  else last_ts

        # *** SOLO USDT contrato oficial ***
        if not _is_usdt_trc20(it):
            continue

        amt = _normalize_amount_usdt(it)
        if amt == 0:
            continue

        frm = (it.get("from") or it.get("transfer_from") or "").strip()
        to  = (it.get("to")   or it.get("transfer_to")   or "").strip()
        if to == self_addr: inflow += amt
        if frm == self_addr: outflow += amt
    return inflow, outflow, first_ts, last_ts

def _dust_counters_trc20_usdt(items: List[dict], self_addr: str):
    micro_in = micro_out = small_in = small_out = 0
    uniq_src, uniq_dst = set(), set()
    for it in items:
        if not _is_usdt_trc20(it):
            continue

        amt = _normalize_amount_usdt(it)
        if amt == 0:
            continue

        frm = (it.get("from") or it.get("transfer_from") or "").strip()
        to  = (it.get("to")   or it.get("transfer_to")   or "").strip()

        if amt <= DUST_MICRO_USDT:
            if to == self_addr: micro_in += 1; uniq_src.add(frm)
            if frm == self_addr: micro_out += 1; uniq_dst.add(to)
        elif amt <= DUST_SMALL_USDT:
            if to == self_addr: small_in += 1; uniq_src.add(frm)
            if frm == self_addr: small_out += 1; uniq_dst.add(to)
    return {
        "micro_in": micro_in, "micro_out": micro_out,
        "small_in": small_in, "small_out": small_out,
        "unique_sources": len(uniq_src), "unique_dests": len(uniq_dst),
    }

def _exposure_breakdown(risky_in_cnt, risky_out_cnt, dust_in_cnt, dust_out_cnt, dex_hits=0, cex_hits=0):
    total = max(1, risky_in_cnt + risky_out_cnt + dust_in_cnt + dust_out_cnt + dex_hits + cex_hits)
    expo = []

    def add(cat, v):
        if v > 0: expo.append({"category": cat, "share": round(100.0 * v / total, 1)})

    add("Blacklist Indirect In", risky_in_cnt)
    add("Blacklist Indirect Out", risky_out_cnt)
    add("Dust In (USDT)", dust_in_cnt)
    add("Dust Out (USDT)", dust_out_cnt)
    if dex_hits: add("DEX", dex_hits)
    if cex_hits: add("Exchange", cex_hits)
    return expo


# ------------------- FUNCIÓN PRINCIPAL -------------------
async def score_wallet(address_b58: str) -> dict:
    reasons: List[Dict[str, Any]] = []
    score = 0

    # Direct flags (TRONSCAN)
    sec = await check_account_security(address_b58)
    if sec.get("is_black_list"):
        reasons.append({"code": "BLACKLIST_USDT", "weight": W.BLACKLIST_USDT, "detail": "TRONSCAN: is_black_list=true"})
        score = max(score, W.BLACKLIST_USDT)
    if sec.get("has_fraud_transaction"):
        reasons.append({"code": "FRAUD_FLAG", "weight": W.FRAUD_FLAG, "detail": "TRONSCAN: has_fraud_transaction"})
        score += W.FRAUD_FLAG

    # Evidencia extra (stablecoin blacklist)
    bl = await check_stablecoin_blacklist(address_b58)
    if bl.get("total", 0) > 0 and not any(r["code"] == "BLACKLIST_USDT" for r in reasons):
        reasons.append({"code": "BLACKLIST_USDT_EVIDENCE", "weight": W.BLACKLIST_USDT_EVIDENCE,
                        "detail": "stableCoin/blackList reportó coincidencia"})
        score = max(score, W.BLACKLIST_USDT)

    # Info básica y TRC20
    acct = await account_overview(address_b58)
    trc20 = await account_trc20_transfers(address_b58, limit=200)
    items = trc20.get("data", []) or []
    if not isinstance(items, list):
        items = []

    # 1-hop counterparties
    ins, outs = _extract_counterparties_trc20(items, address_b58)

    risky_in = await _batch_security_check(ins)
    risky_out = await _batch_security_check(outs)

    # Sumar puntos por contrapartes riesgosas (tope)
    hits = len(risky_in | risky_out)
    if hits:
        add = min(hits * W.COUNTERPARTY_HIT, W.COUNTERPARTY_CAP)
        reasons.append({"code": "COUNTERPARTY_HIGH", "weight": add,
                        "detail": f"{hits} contrapartes 1-hop con señales de riesgo"})
        score += add

    # DUST (USDT)
    dust = _dust_counters_trc20_usdt(items, address_b58)
    dust_in  = dust["micro_in"]  + dust["small_in"]
    dust_out = dust["micro_out"] + dust["small_out"]
    dust_events = dust_in + dust_out
    if dust_events >= DUST_MIN_EVENTS:
        add = min(W.DUST_BASE + (dust_events - DUST_MIN_EVENTS) * W.DUST_PER_EVENT, W.DUST_CAP)
        reasons.append({
            "code": "DUST_ACTIVITY",
            "weight": int(add),
            "detail": f"{dust_events} eventos dust USDT (micro≤${DUST_MICRO_USDT}, small≤${DUST_SMALL_USDT}) in:{dust_in} out:{dust_out} src_uni:{dust['unique_sources']} dst_uni:{dust['unique_dests']}"
        })
        score += int(add)

    # Flujos + first/last
    inflow, outflow, first_ts, last_ts = _aggregate_flows_trc20(items, address_b58)

    score = int(min(score, 100))
    level = "High" if score >= 70 else ("Medium" if score >= 30 else "Low")

    basic = build_basic_info(acct) if isinstance(acct, dict) else {}
    basic.update({
        "inflow_usdt": fmt_amount(inflow),
        "outflow_usdt": fmt_amount(outflow),
        "first_transfer": fmt_time(first_ts) if first_ts else None,
        "last_transfer": fmt_time(last_ts) if last_ts else None,
        "dust_in_events": dust_in,
        "dust_out_events": dust_out,
        "dust_total": dust_events,
    })

    result = {
        "address": address_b58,
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "summary": build_summary(level, reasons),
        "basic_info": basic,
        "evidence": {
            "tronscan_security": sec,
            "tronscan_blacklist": bl,
        },
        "exposure": _exposure_breakdown(len(risky_in), len(risky_out), dust_in, dust_out),
    }

    return result
