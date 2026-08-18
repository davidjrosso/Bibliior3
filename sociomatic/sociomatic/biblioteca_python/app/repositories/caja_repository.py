from sqlite3 import Connection, Row


def ensure_day(conn: Connection, fecha: str, timestamp: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO caja_dias (fecha, saldo_inicial, observacion, cerrado, creado_en, actualizado_en)
        VALUES (?, 0, '', 0, ?, ?)
        """,
        (fecha, timestamp, timestamp),
    )


def find_day(conn: Connection, fecha: str) -> Row:
    return conn.execute("SELECT * FROM caja_dias WHERE fecha = ?", (fecha,)).fetchone()


def list_cash_movements(conn: Connection, fecha: str) -> list[Row]:
    return conn.execute(
        """
        SELECT *
        FROM caja_movimientos
        WHERE fecha = ?
          AND medio_pago = 'efectivo'
        ORDER BY id DESC
        """,
        (fecha,),
    ).fetchall()


def list_daily_summaries(conn: Connection, desde: str, hasta: str) -> list[Row]:
    return conn.execute(
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


def update_day(
    conn: Connection,
    fecha: str,
    saldo_inicial: float,
    observacion: str,
    cerrado: int,
    timestamp: str,
) -> None:
    conn.execute(
        """
        UPDATE caja_dias
        SET saldo_inicial = ?, observacion = ?, cerrado = ?, actualizado_en = ?
        WHERE fecha = ?
        """,
        (saldo_inicial, observacion, cerrado, timestamp, fecha),
    )


def insert_movement(conn: Connection, data: dict, cuota_id: int | None, timestamp: str) -> int:
    cursor = conn.execute(
        """
        INSERT INTO caja_movimientos (
            fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["fecha"],
            data["tipo"],
            data["concepto"],
            data["descripcion"],
            data["monto"],
            data["medio_pago"],
            data["referencia"],
            cuota_id,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def update_movement(conn: Connection, movimiento_id: int, data: dict, timestamp: str) -> int:
    cursor = conn.execute(
        """
        UPDATE caja_movimientos
        SET fecha = ?, tipo = ?, concepto = ?, descripcion = ?, monto = ?, medio_pago = ?,
            referencia = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (
            data["fecha"],
            data["tipo"],
            data["concepto"],
            data["descripcion"],
            data["monto"],
            data["medio_pago"],
            data["referencia"],
            timestamp,
            movimiento_id,
        ),
    )
    return int(cursor.rowcount)


def delete_movement(conn: Connection, movimiento_id: int) -> int:
    cursor = conn.execute("DELETE FROM caja_movimientos WHERE id = ?", (movimiento_id,))
    return int(cursor.rowcount)


def cuota_collection_data(conn: Connection, cuota_id: int) -> Row | None:
    return conn.execute(
        """
        SELECT c.id, c.periodo, c.monto, c.fecha_pago, s.nro_socio, s.apellido, s.nombre
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE c.id = ?
        """,
        (cuota_id,),
    ).fetchone()


def find_movement_by_cuota(conn: Connection, cuota_id: int) -> Row | None:
    return conn.execute(
        "SELECT id FROM caja_movimientos WHERE cuota_id = ?",
        (cuota_id,),
    ).fetchone()


def update_cuota_collection(
    conn: Connection,
    cuota_id: int,
    fecha: str,
    concepto: str,
    descripcion: str,
    monto: float,
    medio_pago: str,
    referencia: str,
    timestamp: str,
) -> None:
    conn.execute(
        """
        UPDATE caja_movimientos
        SET fecha = ?, tipo = 'ingreso', concepto = ?, descripcion = ?, monto = ?,
            medio_pago = ?, referencia = ?, actualizado_en = ?
        WHERE cuota_id = ?
        """,
        (fecha, concepto, descripcion, monto, medio_pago, referencia, timestamp, cuota_id),
    )


def insert_cuota_collection(
    conn: Connection,
    cuota_id: int,
    fecha: str,
    concepto: str,
    descripcion: str,
    monto: float,
    medio_pago: str,
    referencia: str,
    timestamp: str,
) -> None:
    conn.execute(
        """
        INSERT INTO caja_movimientos (
            fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
        ) VALUES (?, 'ingreso', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (fecha, concepto, descripcion, monto, medio_pago, referencia, cuota_id, timestamp, timestamp),
    )


def delete_cuota_collection(conn: Connection, cuota_id: int) -> None:
    conn.execute("DELETE FROM caja_movimientos WHERE cuota_id = ?", (cuota_id,))
