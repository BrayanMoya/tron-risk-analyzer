from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, green, yellow, black

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

    c.showPage()
    c.save()
