from datetime import datetime, timedelta

from app.models.helpers import now_iso, today_iso


MEDIOS_PAGO = {"efectivo", "transferencia", "tarjeta", "cheque", "otro"}
TIPOS = {"ingreso", "egreso"}


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def asegurar_dia(conn, fecha: str) -> None:
    if not valid_date(fecha):
        raise ValueError("Fecha invalida. Use AAAA-MM-DD.")
    timestamp = now_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO caja_dias (fecha, saldo_inicial, observacion, cerrado, creado_en, actualizado_en)
        VALUES (?, 0, '', 0, ?, ?)
        """,
        (fecha, timestamp, timestamp),
    )


def obtener(conn, fecha: str | None = None) -> dict:
    fecha = fecha or today_iso()
    asegurar_dia(conn, fecha)
    dia = dict(conn.execute("SELECT * FROM caja_dias WHERE fecha = ?", (fecha,)).fetchone())
    rows = conn.execute(
        """
        SELECT *
        FROM caja_movimientos
        WHERE fecha = ?
          AND medio_pago = 'efectivo'
        ORDER BY id DESC
        """,
        (fecha,),
    ).fetchall()
    movimientos = [dict(row) for row in rows]
    ingresos = sum(float(row["monto"]) for row in movimientos if row["tipo"] == "ingreso")
    egresos = sum(float(row["monto"]) for row in movimientos if row["tipo"] == "egreso")
    saldo_inicial = float(dia["saldo_inicial"] or 0)
    return {
        "dia": dia,
        "movimientos": movimientos,
        "resumen": {
            "saldo_inicial": saldo_inicial,
            "ingresos": ingresos,
            "egresos": egresos,
            "saldo_final": saldo_inicial + ingresos - egresos,
            "cantidad_movimientos": len(movimientos),
        },
    }


def listado_diario(conn, desde: str | None = None, hasta: str | None = None) -> dict:
    hasta = (hasta or today_iso()).strip()
    desde = (desde or _dias_antes(hasta, 30)).strip()
    if not valid_date(desde) or not valid_date(hasta):
        raise ValueError("Fechas invalidas. Use AAAA-MM-DD.")
    if desde > hasta:
        raise ValueError("La fecha desde no puede ser mayor a hasta.")
    rows = conn.execute(
        """
        SELECT
            d.fecha,
            d.saldo_inicial,
            d.cerrado,
            d.observacion,
            COALESCE(SUM(CASE WHEN m.tipo = 'ingreso' THEN m.monto ELSE 0 END), 0) AS ingresos,
            COALESCE(SUM(CASE WHEN m.tipo = 'egreso' THEN m.monto ELSE 0 END), 0) AS egresos,
            COUNT(m.id) AS movimientos
        FROM caja_dias d
        LEFT JOIN caja_movimientos m
          ON m.fecha = d.fecha
         AND m.medio_pago = 'efectivo'
        WHERE d.fecha BETWEEN ? AND ?
        GROUP BY d.fecha
        ORDER BY d.fecha DESC
        """,
        (desde, hasta),
    ).fetchall()
    dias = []
    total_ingresos = 0.0
    total_egresos = 0.0
    for row in rows:
        ingresos = float(row["ingresos"] or 0)
        egresos = float(row["egresos"] or 0)
        saldo_inicial = float(row["saldo_inicial"] or 0)
        total_ingresos += ingresos
        total_egresos += egresos
        dias.append(
            {
                "fecha": row["fecha"],
                "saldo_inicial": saldo_inicial,
                "ingresos": ingresos,
                "egresos": egresos,
                "saldo_final": saldo_inicial + ingresos - egresos,
                "movimientos": int(row["movimientos"] or 0),
                "cerrado": int(row["cerrado"] or 0),
                "observacion": row["observacion"] or "",
            }
        )
    return {
        "dias": dias,
        "resumen": {
            "desde": desde,
            "hasta": hasta,
            "ingresos": total_ingresos,
            "egresos": total_egresos,
            "neto": total_ingresos - total_egresos,
            "dias": len(dias),
        },
    }


def _dias_antes(fecha: str, dias: int) -> str:
    return (datetime.strptime(fecha, "%Y-%m-%d") - timedelta(days=dias)).strftime("%Y-%m-%d")


def actualizar_dia(conn, data: dict) -> None:
    fecha = str(data.get("fecha") or today_iso()).strip()
    asegurar_dia(conn, fecha)
    saldo_inicial = float(data.get("saldo_inicial") or 0)
    cerrado = 1 if str(data.get("cerrado", "0")) in {"1", "true", "on", "si"} else 0
    conn.execute(
        """
        UPDATE caja_dias
        SET saldo_inicial = ?, observacion = ?, cerrado = ?, actualizado_en = ?
        WHERE fecha = ?
        """,
        (saldo_inicial, str(data.get("observacion", "")).strip(), cerrado, now_iso(), fecha),
    )


def validar_movimiento(data: dict) -> dict:
    fecha = str(data.get("fecha") or today_iso()).strip()
    if not valid_date(fecha):
        raise ValueError("Fecha invalida. Use AAAA-MM-DD.")
    tipo = str(data.get("tipo", "")).strip()
    if tipo not in TIPOS:
        raise ValueError("Tipo de movimiento invalido.")
    monto = float(data.get("monto") or 0)
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    medio_pago = str(data.get("medio_pago", "efectivo")).strip()
    if medio_pago not in MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    concepto = str(data.get("concepto", "")).strip()
    if not concepto:
        raise ValueError("El concepto es obligatorio.")
    return {
        "fecha": fecha,
        "tipo": tipo,
        "concepto": concepto,
        "descripcion": str(data.get("descripcion", "")).strip(),
        "monto": monto,
        "medio_pago": medio_pago,
        "referencia": str(data.get("referencia", "")).strip(),
    }


def crear_movimiento(conn, data: dict) -> int:
    clean = validar_movimiento(data)
    asegurar_dia(conn, clean["fecha"])
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO caja_movimientos (
            fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            clean["fecha"],
            clean["tipo"],
            clean["concepto"],
            clean["descripcion"],
            clean["monto"],
            clean["medio_pago"],
            clean["referencia"],
            data.get("cuota_id"),
            timestamp,
            timestamp,
        ),
    )
    return cursor.lastrowid


def actualizar_movimiento(conn, movimiento_id: int, data: dict) -> None:
    clean = validar_movimiento(data)
    asegurar_dia(conn, clean["fecha"])
    cursor = conn.execute(
        """
        UPDATE caja_movimientos
        SET fecha = ?, tipo = ?, concepto = ?, descripcion = ?, monto = ?, medio_pago = ?,
            referencia = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (
            clean["fecha"],
            clean["tipo"],
            clean["concepto"],
            clean["descripcion"],
            clean["monto"],
            clean["medio_pago"],
            clean["referencia"],
            now_iso(),
            movimiento_id,
        ),
    )
    if cursor.rowcount == 0:
        raise LookupError("Movimiento de caja no encontrado")


def eliminar_movimiento(conn, movimiento_id: int) -> None:
    cursor = conn.execute("DELETE FROM caja_movimientos WHERE id = ?", (movimiento_id,))
    if cursor.rowcount == 0:
        raise LookupError("Movimiento de caja no encontrado")


def registrar_cobro_cuota(conn, cuota_id: int, medio_pago: str = "efectivo") -> None:
    if medio_pago not in MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    if medio_pago != "efectivo":
        eliminar_cobro_cuota(conn, cuota_id)
        return
    row = conn.execute(
        """
        SELECT c.id, c.periodo, c.monto, c.fecha_pago, s.nro_socio, s.apellido, s.nombre
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE c.id = ?
        """,
        (cuota_id,),
    ).fetchone()
    if not row:
        raise LookupError("Cuota no encontrada")
    fecha = row["fecha_pago"] or today_iso()
    asegurar_dia(conn, fecha)
    concepto = "Cobro de cuota"
    descripcion = f"Cuota {row['periodo']} - Socio #{row['nro_socio']} {row['apellido']}, {row['nombre']}"
    referencia = f"cuota:{row['id']}"
    timestamp = now_iso()
    existente = conn.execute(
        "SELECT id FROM caja_movimientos WHERE cuota_id = ?",
        (cuota_id,),
    ).fetchone()
    if existente:
        conn.execute(
            """
            UPDATE caja_movimientos
            SET fecha = ?, tipo = 'ingreso', concepto = ?, descripcion = ?, monto = ?,
                medio_pago = ?, referencia = ?, actualizado_en = ?
            WHERE cuota_id = ?
            """,
            (fecha, concepto, descripcion, float(row["monto"]), medio_pago, referencia, timestamp, cuota_id),
        )
        return
    conn.execute(
        """
        INSERT INTO caja_movimientos (
            fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
        ) VALUES (?, 'ingreso', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (fecha, concepto, descripcion, float(row["monto"]), medio_pago, referencia, cuota_id, timestamp, timestamp),
    )


def eliminar_cobro_cuota(conn, cuota_id: int) -> None:
    conn.execute("DELETE FROM caja_movimientos WHERE cuota_id = ?", (cuota_id,))
