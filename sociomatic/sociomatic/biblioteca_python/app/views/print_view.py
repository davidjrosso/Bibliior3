from html import escape


def format_number(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_money(value) -> str:
    text = f"{float(value):,.2f}"
    return "$ " + text.replace(",", "_").replace(".", ",").replace("_", ".")


def period_label(periodo: str) -> str:
    meses = {
        "01": "Enero",
        "02": "Febrero",
        "03": "Marzo",
        "04": "Abril",
        "05": "Mayo",
        "06": "Junio",
        "07": "Julio",
        "08": "Agosto",
        "09": "Septiembre",
        "10": "Octubre",
        "11": "Noviembre",
        "12": "Diciembre",
    }
    try:
        year, month = periodo.split("-", 1)
        return f"{meses.get(month, month)} {year}"
    except ValueError:
        return periodo


def render_print(periodo: str, cobrador_nombre: str, rows) -> str:
    cards = []
    mes = period_label(periodo)
    for row in rows:
        socio = escape(f"{row['apellido']}, {row['nombre']}")
        direccion = escape(f"{row['direccion']} - {row['localidad']}")
        barrio = escape(row["barrio"] or "")
        monto = format_money(row["monto"])

        def talon(tipo: str) -> str:
            return f"""
        <div class="talon {tipo.lower()}">
            <img class="marca-agua" src="/assets/watermark-biblioteca.png?v=20260817" alt="">
            <img class="sello-logo" src="/assets/logo-biblioteca.png?v=20260825" alt="">
            <div class="talon-contenido">
                <div class="tipo">{tipo}</div>
                <header>
                    <strong>BIBLIOTECA POPULAR J.J. DE URQUIZA</strong>
                    <span>ALBERDI 75 - RIO TERCERO</span>
                    <span>TE: 3571-412148</span>
                </header>
                <div class="datos">
                    <section class="datos-socio">
                        <strong>Cuota {periodo}</strong>
                        <span>Socio #{format_number(row['nro_socio'])}</span>
                        <b>{socio}</b>
                        <span>{direccion}</span>
                        <span>Barrio: {barrio}</span>
                    </section>
                    <section class="datos-monto">
                        <span>Monto</span>
                        <strong>{monto}</strong>
                        <em>{mes}</em>
                    </section>
                </div>
                <footer>MUCHAS GRACIAS POR MANTENER SU CUOTA AL DIA</footer>
            </div>
        </div>
        """

        cards.append(f"<section class='cupon'>{talon('ORIGINAL')}<div class='corte'></div>{talon('DUPLICADO')}</section>")
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
    .hoja {{ display: grid; grid-template-columns: 1fr; gap: 0; }}
    .cupon {{
      border: 1px solid #111;
      height: 68mm;
      display: grid;
      grid-template-columns: 1fr 1px 1fr;
      page-break-inside: avoid;
    }}
    .talon {{
      padding: 3.8mm 5mm;
      position: relative;
      overflow: hidden;
      font-size: 9pt;
    }}
    .talon-contenido {{
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      min-height: 100%;
      gap: 2.2mm;
    }}
    .tipo {{ font-weight: 700; font-size: 9pt; letter-spacing: .3px; }}
    header {{ text-align: center; border-bottom: 1px solid #111; padding-bottom: 2.2mm; }}
    header strong {{ display: block; font-size: 10.8pt; margin-bottom: .6mm; }}
    header span {{ display: block; font-size: 8.2pt; line-height: 1.15; }}
    .datos {{ display: grid; grid-template-columns: 1fr 32mm; gap: 3mm; align-items: start; }}
    .datos-socio, .datos-monto {{ display: flex; flex-direction: column; gap: 1.1mm; }}
    .datos-socio strong, .datos-monto strong {{ font-size: 9.5pt; }}
    .datos-socio b {{ font-size: 9.8pt; }}
    .datos-monto {{ text-align: right; }}
    .datos-monto span {{ font-size: 7.8pt; text-transform: uppercase; }}
    em {{ font-style: normal; font-weight: 700; font-size: 8.3pt; }}
    footer {{ margin-top: auto; border-top: 1px solid #111; padding-top: 1.6mm; text-align: center; font-weight: 700; font-size: 7.6pt; }}
    .marca-agua {{
      position: absolute;
      left: 50%;
      top: 50%;
      width: 56mm;
      height: 56mm;
      object-fit: contain;
      opacity: 0.26;
      transform: translate(-50%, -50%);
      z-index: 0;
      pointer-events: none;
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
    }}
    .sello-logo {{
      position: absolute;
      top: 3.2mm;
      right: 4.6mm;
      width: 13mm;
      height: auto;
      object-fit: contain;
      opacity: 0.86;
      filter: grayscale(1) brightness(0);
      z-index: 2;
      pointer-events: none;
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
    }}
    .corte {{ border-left: 1px dashed #333; }}
    @media print {{
      .barra {{ display: none; }}
      body {{ margin: 0; }}
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
