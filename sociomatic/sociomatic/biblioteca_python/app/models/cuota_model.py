from app.models import caja_model, config_model, socio_model
from app.models.helpers import add_months, current_period, next_period, now_iso, parse_decimal, today_iso, valid_date, valid_period
from app.settings import COBRADORES


def generar(conn, data: dict) -> dict:
    periodo = data.get("periodo") or next_period()
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    forzar = bool(data.get("forzar"))
    control = control_generacion(conn, periodo)
    if not control["puede_generar"] and not (forzar and control["forzable"]):
        raise ValueError(control["motivo"])
    socios = conn.execute(
        """
        SELECT *
        FROM socios
        WHERE fecha_baja IS NULL
          AND cobrador IN (1, 3)
          AND fecha_alta <= ?
        """,
        (f"{periodo}-31",),
    ).fetchall()
    creadas = 0
    for socio in socios:
        monto = config_model.cuota_monto(conn, socio["estado"])
        try:
            conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, creado_en, actualizado_en)
                VALUES (?, ?, ?, 'pendiente', ?, ?)
                """,
                (socio["id"], periodo, monto, now_iso(), now_iso()),
            )
            creadas += 1
        except Exception:
            continue
    return {"periodo": periodo, "cuotas_creadas": creadas, "control": control, "forzada": forzar}


def control_generacion(conn, periodo: str) -> dict:
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    periodo_anterior = add_months(periodo, -1)
    total_cuotas = conn.execute("SELECT COUNT(*) AS total FROM cuotas").fetchone()["total"]
    cuotas_periodo = _contar_cuotas_objetivo(conn, periodo)
    cuotas_anterior = _contar_cuotas_objetivo(conn, periodo_anterior)
    socios_objetivo = _contar_socios_objetivo(conn, periodo)
    socios_anterior_objetivo = _contar_socios_objetivo(conn, periodo_anterior)
    faltantes_estimadas = max(int(socios_objetivo or 0) - int(cuotas_periodo or 0), 0)
    puede_generar = True
    forzable = False
    motivo = ""
    if total_cuotas and cuotas_anterior < socios_anterior_objetivo:
        puede_generar = False
        forzable = True
        motivo = (
            f"Advertencia para generar {periodo}. El periodo anterior ({periodo_anterior}) no esta completo: "
            f"tiene {cuotas_anterior} de {socios_anterior_objetivo} cuota(s) esperada(s)."
        )
    elif socios_objetivo == 0:
        puede_generar = False
        motivo = "No hay socios activos para generar cuotas."
    elif faltantes_estimadas == 0:
        puede_generar = False
        motivo = f"Las cuotas de {periodo} ya estan generadas para los socios alcanzados."
    return {
        "periodo": periodo,
        "periodo_anterior": periodo_anterior,
        "puede_generar": puede_generar,
        "forzable": forzable,
        "motivo": motivo,
        "socios_objetivo": int(socios_objetivo or 0),
        "socios_anterior_objetivo": int(socios_anterior_objetivo or 0),
        "cuotas_periodo": int(cuotas_periodo or 0),
        "cuotas_anterior": int(cuotas_anterior or 0),
        "faltantes_estimadas": faltantes_estimadas,
        "primera_generacion": int(total_cuotas or 0) == 0,
    }


def _contar_socios_objetivo(conn, periodo: str) -> int:
    return int(
        conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM socios
            WHERE fecha_baja IS NULL
              AND cobrador IN (1, 3)
              AND fecha_alta <= ?
            """,
            (f"{periodo}-31",),
        ).fetchone()["total"]
        or 0
    )


def _contar_cuotas_objetivo(conn, periodo: str) -> int:
    return int(
        conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM cuotas c
            JOIN socios s ON s.id = c.socio_id
            WHERE c.periodo = ?
              AND s.fecha_baja IS NULL
              AND s.cobrador IN (1, 3)
              AND s.fecha_alta <= ?
            """,
            (periodo, f"{periodo}-31"),
        ).fetchone()["total"]
        or 0
    )


def periodos_entre(desde: str, hasta: str) -> list[str]:
    periodos = []
    periodo = desde
    while periodo <= hasta:
        periodos.append(periodo)
        periodo = add_months(periodo, 1)
    return periodos


def listar_faltantes_generacion(conn, query: dict) -> dict:
    hasta = (query.get("hasta", [""])[0] or "").strip() or add_months(current_period(), -1)
    desde = (query.get("desde", [""])[0] or "").strip() or f"{hasta[:4]}-01"
    try:
        limite = int((query.get("limite", ["500"])[0] or "500").strip())
    except ValueError:
        limite = 500
    limite = max(1, min(limite, 5000))
    if not valid_period(desde) or not valid_period(hasta):
        raise ValueError("Periodos invalidos. Use AAAA-MM.")
    if desde > hasta:
        raise ValueError("El periodo desde no puede ser mayor al periodo hasta.")

    socios = conn.execute(
        """
        SELECT s.id, s.nro_socio, s.apellido, s.nombre, s.dni, s.telefono, s.cobrador, s.fecha_alta
        FROM socios s
        WHERE s.fecha_baja IS NULL
          AND s.cobrador IN (1, 3)
          AND s.fecha_alta <= ?
        ORDER BY s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE, s.nro_socio
        """,
        (f"{hasta}-31",),
    ).fetchall()
    existentes = {
        (row["socio_id"], row["periodo"])
        for row in conn.execute(
            """
            SELECT c.socio_id, c.periodo
            FROM cuotas c
            JOIN socios s ON s.id = c.socio_id
            WHERE c.periodo BETWEEN ? AND ?
              AND s.fecha_baja IS NULL
              AND s.cobrador IN (1, 3)
            """,
            (desde, hasta),
        ).fetchall()
    }
    resumen = {periodo: 0 for periodo in periodos_entre(desde, hasta)}
    detalle = []
    total = 0
    for periodo in sorted(resumen, reverse=True):
        fecha_corte = f"{periodo}-31"
        for socio in socios:
            if socio["fecha_alta"] > fecha_corte:
                continue
            if (socio["id"], periodo) in existentes:
                continue
            total += 1
            resumen[periodo] += 1
            if len(detalle) < limite:
                detalle.append(
                    {
                        "periodo": periodo,
                        "socio_id": socio["id"],
                        "nro_socio": socio["nro_socio"],
                        "apellido": socio["apellido"],
                        "nombre": socio["nombre"],
                        "dni": socio["dni"],
                        "telefono": socio["telefono"],
                        "cobrador": socio["cobrador"],
                    }
                )
    return {
        "desde": desde,
        "hasta": hasta,
        "limite": limite,
        "total": total,
        "mostrados": len(detalle),
        "resumen": [
            {"periodo": periodo, "faltantes": cantidad}
            for periodo, cantidad in sorted(resumen.items(), reverse=True)
            if cantidad
        ],
        "faltantes": detalle,
    }


def crear(conn, data: dict) -> int:
    socio_id = int(data.get("socio_id"))
    periodo = data.get("periodo")
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    socio = socio_model.obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise ValueError("Socio activo no encontrado.")
    monto = parse_decimal(data.get("monto") or config_model.cuota_monto(conn, socio["estado"]))
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO cuotas (socio_id, periodo, monto, estado, observacion, creado_en, actualizado_en)
        VALUES (?, ?, ?, 'pendiente', ?, ?, ?)
        """,
        (socio_id, periodo, monto, str(data.get("observacion", "")), timestamp, timestamp),
    )
    return cursor.lastrowid


def listar(conn, query: dict) -> list[dict]:
    periodo = (query.get("periodo", [""])[0] or "").strip()
    estado = (query.get("estado", [""])[0] or "").strip()
    cobrador = (query.get("cobrador", [""])[0] or "").strip()
    busqueda = (query.get("q", [""])[0] or "").strip()
    where = ["s.fecha_baja IS NULL"]
    params = []
    if periodo:
        if not valid_period(periodo):
            raise ValueError("Periodo invalido. Use AAAA-MM.")
        where.append("c.periodo = ?")
        params.append(periodo)
    if estado in {"pendiente", "pagada"}:
        where.append("c.estado = ?")
        params.append(estado)
    if cobrador:
        where.append("s.cobrador = ?")
        params.append(int(cobrador))
    if busqueda:
        where.append(
            "(CAST(s.nro_socio AS TEXT) = ? OR s.apellido LIKE ? OR s.nombre LIKE ? OR s.dni LIKE ? OR s.direccion LIKE ?)"
        )
        like = f"%{busqueda}%"
        params.extend([busqueda, like, like, like, like])
    rows = conn.execute(
        f"""
        SELECT c.*, s.nro_socio, s.apellido, s.nombre, s.dni, s.direccion,
               s.localidad, s.cobrador, s.estado AS estado_socio
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE {' AND '.join(where)}
        ORDER BY c.periodo DESC, c.estado, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()
    cuotas = []
    for row in rows:
        cuota = dict(row)
        cuota["socio"] = f"{row['apellido']}, {row['nombre']}"
        cuota["cobrador_texto"] = config_model.cobrador_nombre(conn, row["cobrador"])
        cuotas.append(cuota)
    return cuotas


def actualizar(conn, cuota_id: int, data: dict) -> None:
    periodo = data.get("periodo")
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    monto = parse_decimal(data.get("monto"))
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")
    estado = data.get("estado", "pendiente")
    if estado not in {"pendiente", "pagada"}:
        raise ValueError("Estado de cuota invalido.")
    fecha_pago = data.get("fecha_pago") or None
    if estado == "pendiente":
        fecha_pago = None
    elif not fecha_pago:
        fecha_pago = today_iso()
    cursor = conn.execute(
        """
        UPDATE cuotas
        SET periodo = ?, monto = ?, estado = ?, fecha_pago = ?, observacion = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (periodo, monto, estado, fecha_pago, str(data.get("observacion", "")), now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")
    if estado == "pagada":
        caja_model.registrar_cobro_cuota(conn, cuota_id)
    else:
        caja_model.eliminar_cobro_cuota(conn, cuota_id)


def eliminar(conn, cuota_id: int) -> None:
    caja_model.eliminar_cobro_cuota(conn, cuota_id)
    cursor = conn.execute("DELETE FROM cuotas WHERE id = ?", (cuota_id,))
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")


def marcar_pagada(conn, cuota_id: int, fecha_pago: str | None = None, medio_pago: str = "efectivo") -> None:
    fecha = fecha_pago or today_iso()
    if not valid_date(fecha):
        raise ValueError("Fecha de pago invalida.")
    if medio_pago not in caja_model.MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    row = conn.execute("SELECT estado FROM cuotas WHERE id = ?", (cuota_id,)).fetchone()
    if not row:
        raise LookupError("Cuota no encontrada")
    if row["estado"] == "pagada":
        raise ValueError("La cuota ya esta pagada.")
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pagada', fecha_pago = ?, actualizado_en = ? WHERE id = ?",
        (fecha, now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")
    caja_model.registrar_cobro_cuota(conn, cuota_id, medio_pago)


def marcar_pagadas(conn, data: dict) -> dict:
    ids = list(dict.fromkeys(int(cuota_id) for cuota_id in data.get("ids", [])))
    if not ids:
        raise ValueError("Seleccione al menos una cuota para pagar.")
    fecha_pago = str(data.get("fecha_pago", "")).strip() or today_iso()
    medio_pago = str(data.get("medio_pago", "efectivo")).strip()
    if not valid_date(fecha_pago):
        raise ValueError("Fecha de pago invalida.")
    if medio_pago not in caja_model.MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT id, periodo, estado FROM cuotas WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    if len(rows) != len(set(ids)):
        raise LookupError("Una o mas cuotas no fueron encontradas.")
    ya_pagadas = [row["periodo"] for row in rows if row["estado"] == "pagada"]
    if ya_pagadas:
        raise ValueError(f"No se puede cobrar: ya estan pagadas las cuota(s) {', '.join(ya_pagadas)}.")
    pagadas = 0
    for cuota_id in ids:
        marcar_pagada(conn, cuota_id, fecha_pago, medio_pago)
        pagadas += 1
    return {"cuotas_pagadas": pagadas, "ids": ids}


def pago_adelantado(conn, data: dict) -> dict:
    socio_id = int(data.get("socio_id"))
    desde_periodo = data.get("desde_periodo")
    cantidad = int(data.get("cantidad") or 0)
    medio_pago = str(data.get("medio_pago", "efectivo")).strip()
    fecha_pago = str(data.get("fecha_pago", "")).strip() or today_iso()
    if not valid_period(desde_periodo):
        raise ValueError("Periodo inicial invalido. Use AAAA-MM.")
    if cantidad < 1 or cantidad > 60:
        raise ValueError("La cantidad de meses debe estar entre 1 y 60.")
    if not valid_date(fecha_pago):
        raise ValueError("Fecha de pago invalida.")
    if medio_pago not in caja_model.MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    socio = socio_model.obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise ValueError("Socio activo no encontrado.")
    periodos = [add_months(desde_periodo, offset) for offset in range(cantidad)]
    placeholders = ",".join("?" for _ in periodos)
    pagadas_existentes = conn.execute(
        f"""
        SELECT periodo
        FROM cuotas
        WHERE socio_id = ?
          AND estado = 'pagada'
          AND periodo IN ({placeholders})
        ORDER BY periodo
        """,
        [socio_id, *periodos],
    ).fetchall()
    if pagadas_existentes:
        periodos_pagados = ", ".join(row["periodo"] for row in pagadas_existentes)
        raise ValueError(
            "No se puede hacer el pago adelantado: ya hay cuota(s) pagada(s) en "
            f"estos periodo(s): {periodos_pagados}. Revise el socio y elija otro rango."
        )
    creadas = 0
    pagadas = 0
    ids = []
    timestamp = now_iso()
    for periodo in periodos:
        monto = config_model.cuota_monto(conn, socio["estado"])
        row = conn.execute(
            "SELECT id, estado FROM cuotas WHERE socio_id = ? AND periodo = ?",
            (socio_id, periodo),
        ).fetchone()
        if row:
            cuota_id = row["id"]
            conn.execute(
                """
                UPDATE cuotas
                SET monto = ?, estado = 'pagada', fecha_pago = ?, observacion = ?, actualizado_en = ?
                WHERE id = ?
                """,
                (monto, fecha_pago, "Pago adelantado", timestamp, cuota_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, fecha_pago, observacion, creado_en, actualizado_en)
                VALUES (?, ?, ?, 'pagada', ?, 'Pago adelantado', ?, ?)
                """,
                (socio_id, periodo, monto, fecha_pago, timestamp, timestamp),
            )
            cuota_id = cursor.lastrowid
            creadas += 1
        caja_model.registrar_cobro_cuota(conn, cuota_id, medio_pago)
        ids.append(cuota_id)
        pagadas += 1
    return {"cuotas_creadas": creadas, "cuotas_pagadas": pagadas, "ids": ids}


def marcar_pendiente(conn, cuota_id: int) -> None:
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pendiente', fecha_pago = NULL, actualizado_en = ? WHERE id = ?",
        (now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")
    caja_model.eliminar_cobro_cuota(conn, cuota_id)


def cuotas_para_imprimir(conn, periodo: str, cobrador: int):
    order = "s.direccion COLLATE NOCASE, s.apellido COLLATE NOCASE" if cobrador == 1 else "s.nro_socio"
    limite_moroso = int(config_model.get_config(conn).get("moroso_cuotas_limite", "4"))
    return conn.execute(
        f"""
        SELECT c.*, s.nro_socio, s.apellido, s.nombre, s.direccion, s.barrio,
               s.localidad, s.dni, s.cobrador
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE c.periodo = ?
          AND s.fecha_baja IS NULL
          AND s.cobrador = ?
          AND c.estado = 'pendiente'
          AND (
            SELECT COUNT(*)
            FROM cuotas cx
            WHERE cx.socio_id = s.id
              AND cx.estado = 'pendiente'
          ) <= ?
        ORDER BY {order}
        """,
        (periodo, cobrador, limite_moroso),
    ).fetchall()
