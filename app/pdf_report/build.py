from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, green, yellow, black, HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

TRONSCAN_ADDR = "https://tronscan.org/#/address/"
TRONSCAN_TX   = "https://tronscan.org/#/transaction/"

def _wrap(c, text, x, y, max_chars=95, step=14):
    """Imprime texto con wrap simple por caracteres."""
    if not text:
        return y
    line = ""
    for ch in text:
        if len(line) >= max_chars and ch == " ":
            c.drawString(x, y, line)
            y = _line(c, y, step)
            line = ""
        else:
            line += ch
    if line:
        c.drawString(x, y, line)
        y = _line(c, y, step)
    return y


def _fmt_dt(ms):
    from datetime import datetime, timezone
    if not ms: return "N/A"
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def draw_linked_text(c, text, x, y, max_width, *, url, font_name="Helvetica", start_size=10, min_size=7):
    """
    Dibuja 'text' completo ajustando tamaño para que quepa en max_width
    y crea un link clicable a 'url' sobre el bounding box del texto.
    Devuelve (used_width, used_size).
    """
    size = start_size
    width = stringWidth(text, font_name, size)
    while size >= min_size and width > max_width:
        size -= 0.5
        width = stringWidth(text, font_name, size)

    # dibuja texto
    c.setFont(font_name, size)
    c.drawString(x, y, text)

    # zona clicable (ligeramente mayor que el texto)
    pad_y = 2
    c.linkURL(url, (x, y - pad_y, x + min(width, max_width), y + size + pad_y), relative=0, thickness=0)

    # vuelve al tamaño normal para lo siguiente
    c.setFont(font_name, start_size)
    return width, size

def risk_color(score: int):
    return red if score >= 70 else (yellow if score >= 30 else green)

def _line(c, y, step=16):
    """Baja el cursor y hace salto de página si hace falta."""
    if y < 80:
        c.showPage()
        c.setFont("Helvetica", 12)
        return A4[1] - 60
    return y - step

def build_pdf(address: str, result: dict, out_path: str):
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4

    # Encabezado
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, h-60, "TRON Wallet Risk Report")

    c.setFont("Helvetica", 12)
    y = h-90
    c.drawString(40, y, f"Address: {address}"); y = _line(c, y, 15)

    score = int(result.get('risk_score', 0))
    c.drawString(40, y, f"Risk Score: {score} / 100"); y = _line(c, y, 15)
    bar_h = 15       # alto de la barra
    pad = 1  # separación mínima bajo el texto
    bar_y = y - bar_h - pad
    c.setFillColor(risk_color(score))
    c.rect(40, y-14, width=max(0, min(100, score)) * 4, height=bar_h, fill=1, stroke=0)
    c.setFillColor(black); y = _line(c, y, 15)
    c.drawString(40, y, f"Risk Level: {result.get('risk_level', 'N/A')}")

    y = bar_y - 12
    y = _line(c, y, 30)
    # Resumen
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Resumen"); y = _line(c, y, 20)
    c.setFont("Helvetica", 12)
    summary = result.get("summary","")[:200]  # si quieres, aumenta y haz wrap real
    c.drawString(40, y, summary)
    y = _line(c, y, 24)

    # Básicos
    bi = result.get("basic_info", {})
    c.drawString(40, y, f"Entradas (TRC20 USDT aprox): {bi.get('inflow_usdt','N/A')}"); y = _line(c, y, 15)
    c.drawString(40, y, f"Salidas (TRC20 USDT aprox): {bi.get('outflow_usdt','N/A')}"); y = _line(c, y, 15)
    c.drawString(40, y, f"Primera transferencia: {bi.get('first_transfer','N/A')}"); y = _line(c, y, 15)
    c.drawString(40, y, f"Última transferencia: {bi.get('last_transfer','N/A')}"); y = _line(c, y, 15)
    c.drawString(40, y, f"Dust In: {bi.get('dust_in_events',0)}  Dust Out: {bi.get('dust_out_events',0)}  Total: {bi.get('dust_total',0)}"); y = _line(c, y, 24)

    # Exposición
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Exposición"); y = _line(c, y, 16)
    c.setFont("Helvetica", 11)
    for ex in result.get("exposure", []):
        c.drawString(50, y, f"- {ex['category']}: {ex['share']}%"); y = _line(c, y, 14)

    y = _line(c, y, 10)  # pequeño espacio antes de Razones

    # Razones
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Razones:"); y = _line(c, y, 18)
    c.setFont("Helvetica", 11)
    for r in result.get("reasons", []):
        line = f"- [{r.get('code')}] +{r.get('weight')} : {r.get('detail')}"
        c.drawString(50, y, line[:110])
        y = _line(c, y, 16)

    # -------- Evidencia Blacklist (USDT) --------
    bl = result.get("blacklist_report")
    if bl and bl.get("is_blacklisted_usdt"):
        y = _line(c, y, 20)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Evidencia de Blacklist (USDT)");
        y = _line(c, y, 18)
        c.setFont("Helvetica", 11)

        txh = bl.get("tx_hash", "N/A")
        label = f"Tx hash: {txh}"
        c.drawString(50, y, label)
        # añade un link “Ver en TronScan” a la derecha
        view_txt = "  [Ver en TronScan]"
        vw_w = stringWidth(view_txt, "Helvetica", 11)
        c.drawString(50 + stringWidth(label, "Helvetica", 11), y, view_txt)
        c.linkURL(TRONSCAN_TX + txh, (
            50 + stringWidth(label, "Helvetica", 11),
            y - 2,
            50 + stringWidth(label + view_txt, "Helvetica", 11),
            y + 11 + 2
        ), relative=0, thickness=0)

        y = _line(c, y, 14)
        c.drawString(50, y, f"Fecha/Hora: {_fmt_dt(bl.get('timestamp_ms'))}");
        y = _line(c, y, 14)
        c.drawString(50, y, f"Ejecutor: {bl.get('executor_contract', 'N/A')} (MultiSigWallet)");
        y = _line(c, y, 18)
        y = _wrap(c, f"Nota: {bl.get('note', '')}", 50, y, max_chars=90, step=14)

        # Tabla de transacciones relevantes
        rows = bl.get("related_transfers") or []
        if rows:
            y = _line(c, y, 6)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "Transacciones relevantes alrededor del bloqueo (≥ umbral)");
            y = _line(c, y, 16)
            c.setFont("Helvetica", 10)
            # encabezado
            c.drawString(50, y, "Fecha (UTC)")
            c.drawString(150, y, "Dir")
            c.drawString(175, y, "From")
            c.drawString(355, y, "To")
            c.drawString(525, y, "USDT")
            y = _line(c, y, 14)

            # límites de ancho para cada columna (en puntos)
            FROM_X = 175
            TO_X = 355
            AMT_XR = 570
            FROM_W = 170  # ~170 pt ≈ ~2.4 in
            TO_W = 170

            for r in rows:
                if y < 90:
                    c.showPage();
                    c.setFont("Helvetica", 10);
                    y = A4[1] - 80
                    # reimprime encabezado si hiciste salto de página
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(50, y, "Fecha (UTC)")
                    c.drawString(150, y, "Dir")
                    c.drawString(175, y, "From")
                    c.drawString(355, y, "To")
                    c.drawString(525, y, "USDT")
                    y = _line(c, y, 14)
                    c.setFont("Helvetica", 10)

                dt = _fmt_dt(r.get("timestamp"))
                direction = r.get("direction", "")
                frm = r.get("from", "")  # <- sin cortar
                to = r.get("to", "")  # <- sin cortar
                amt = r.get("amount_usdt", "0")
                suspect = r.get("suspect", False)

                if suspect:
                    c.setFillColor(HexColor("#b30000"))
                    c.circle(42, y + 3, 2.2, fill=1, stroke=0)
                    c.setFillColor(black)

                c.drawString(50, y, dt)
                c.drawString(150, y, direction)
                # Dibuja direcciones completas, ajustando tamaño si hace falta:
                draw_linked_text(
                    c, frm, FROM_X, y, FROM_W,
                    url=TRONSCAN_ADDR + frm if frm else TRONSCAN_ADDR
                )
                draw_linked_text(
                    c, to, TO_X, y, TO_W,
                    url=TRONSCAN_ADDR + to if to else TRONSCAN_ADDR
                )
                c.drawRightString(570, y, amt)
                y = _line(c, y, 13)

            y = _line(c, y, 10)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(50, y,
                         "• Las filas marcadas indican contrapartes sospechosas o causa probable del bloqueo.")
            y = _line(c, y, 14)


    c.showPage()
    c.save()
