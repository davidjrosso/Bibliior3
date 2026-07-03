def render_print(periodo: str, cobrador_nombre: str, rows) -> str:
    cards = []
    for row in rows:
        socio = f"{row['apellido']}, {row['nombre']}"
        base = f"""
        <div class="talon">
            <strong>Biblioteca - Cuota {periodo}</strong>
            <span>Socio #{row['nro_socio']} - DNI {row['dni']}</span>
            <span>{socio}</span>
            <span>{row['direccion']} - {row['localidad']}</span>
            <span>Monto: ${row['monto']:.2f}</span>
        </div>
        """
        cards.append(f"<section class='cupon'>{base}<div class='corte'></div>{base}</section>")
    total = len(cards)
    body = "\n".join(cards) or "<p>No hay cuotas para imprimir con esos criterios.</p>"
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Cuotas {periodo}</title>
  <style>
    @page {{ size: A4; margin: 10mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; margin: 0; color: #111; }}
    .barra {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    button {{ padding: 8px 12px; }}
    .hoja {{ display: grid; grid-template-columns: 1fr; gap: 6mm; }}
    .cupon {{
      border: 1px solid #111;
      min-height: 62mm;
      display: grid;
      grid-template-columns: 1fr 1px 1fr;
      page-break-inside: avoid;
    }}
    .talon {{ padding: 7mm; display: flex; flex-direction: column; gap: 4mm; font-size: 12pt; }}
    .corte {{ border-left: 1px dashed #333; }}
    @media print {{
      .barra {{ display: none; }}
      .cupon:nth-of-type(4n) {{ page-break-after: always; }}
    }}
  </style>
</head>
<body>
  <div class="barra">
    <div><strong>Periodo:</strong> {periodo} | <strong>Cobrador:</strong> {cobrador_nombre} | <strong>Total:</strong> {total}</div>
    <button onclick="window.print()">Imprimir</button>
  </div>
  <main class="hoja">{body}</main>
</body>
</html>"""
