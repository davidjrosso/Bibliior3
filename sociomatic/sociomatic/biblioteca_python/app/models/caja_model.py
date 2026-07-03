from datetime import datetime

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


def registrar_cobro_cuota(conn, cuota_id: int) -> None:
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
                referencia = ?, actualizado_en = ?
            WHERE cuota_id = ?
            """,
            (fecha, concepto, descripcion, float(row["monto"]), referencia, timestamp, cuota_id),
        )
        return
    conn.execute(
        """
        INSERT INTO caja_movimientos (
            fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
        ) VALUES (?, 'ingreso', ?, ?, ?, 'efectivo', ?, ?, ?, ?)
        """,
        (fecha, concepto, descripcion, float(row["monto"]), referencia, cuota_id, timestamp, timestamp),
    )


def eliminar_cobro_cuota(conn, cuota_id: int) -> None:
    conn.execute("DELETE FROM caja_movimientos WHERE cuota_id = ?", (cuota_id,))
