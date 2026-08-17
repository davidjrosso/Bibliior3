def format_number(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_money(value) -> str:
    text = f"{float(value):,.2f}"
    return "$ " + text.replace(",", "_").replace(".", ",").replace("_", ".")


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
            <span>Monto: {format_money(row['monto'])}</span>
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
    <div><strong>Periodo:</strong> {periodo} | <strong>Cobrador:</strong> {cobrador_nombre} | <strong>Total:</strong> {format_number(total)}</div>
    <button onclick="window.print()">Imprimir</button>
  </div>
  <main class="hoja">{body}</main>
</body>
</html>"""


def render_morosos(rows, limite: int) -> str:
    items = []
    for row in rows:
        items.append(
            f"""
            <tr>
              <td>{row['nro_socio']}</td>
              <td>{row['apellido']}, {row['nombre']}</td>
              <td>{row['dni']}</td>
              <td>{row['telefono'] or '-'}</td>
              <td>{row['direccion']} - {row['localidad']}</td>
              <td>{format_number(row['cuotas_impagas'])}</td>
              <td>{format_money(row['deuda'])}</td>
            </tr>
            """
        )
    body = "\n".join(items) or "<tr><td colspan='7'>No hay socios morosos.</td></tr>"
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Socios morosos</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111; }}
    .barra {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #bbb; text-align: left; padding: 6px; }}
    th {{ background: #eee; }}
    @media print {{ .barra {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="barra">
    <div><strong>Socios morosos</strong> | Mas de {format_number(limite)} cuota(s) impaga(s) | Total: {format_number(len(rows))}</div>
    <button onclick="window.print()">Imprimir</button>
  </div>
  <table>
    <thead>
      <tr><th>Nro.</th><th>Socio</th><th>DNI</th><th>Telefono</th><th>Direccion</th><th>Impagas</th><th>Deuda</th></tr>
    </thead>
    <tbody>{body}</tbody>
  </table>
</body>
</html>"""
