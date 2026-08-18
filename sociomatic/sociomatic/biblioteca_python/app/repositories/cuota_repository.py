from sqlite3 import Connection, Row


def count_all(conn: Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS total FROM cuotas").fetchone()["total"] or 0)


def count_generation_period(conn: Connection, periodo: str) -> int:
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


def insert_pending(conn: Connection, socio_id: int, periodo: str, monto: float, timestamp: str) -> int:
    cursor = conn.execute(
        """
        INSERT INTO cuotas (socio_id, periodo, monto, estado, creado_en, actualizado_en)
        VALUES (?, ?, ?, 'pendiente', ?, ?)
        """,
        (socio_id, periodo, monto, timestamp, timestamp),
    )
    return int(cursor.lastrowid)


def insert_custom_pending(
    conn: Connection,
    socio_id: int,
    periodo: str,
    monto: float,
    observacion: str,
    timestamp: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO cuotas (socio_id, periodo, monto, estado, observacion, creado_en, actualizado_en)
        VALUES (?, ?, ?, 'pendiente', ?, ?, ?)
        """,
        (socio_id, periodo, monto, observacion, timestamp, timestamp),
    )
    return int(cursor.lastrowid)


def update_details(
    conn: Connection,
    cuota_id: int,
    periodo: str,
    monto: float,
    estado: str,
    fecha_pago: str | None,
    observacion: str,
    timestamp: str,
) -> int:
    cursor = conn.execute(
        """
        UPDATE cuotas
        SET periodo = ?, monto = ?, estado = ?, fecha_pago = ?, observacion = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (periodo, monto, estado, fecha_pago, observacion, timestamp, cuota_id),
    )
    return int(cursor.rowcount)


def mark_paid(conn: Connection, cuota_id: int, fecha_pago: str, timestamp: str) -> int:
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pagada', fecha_pago = ?, actualizado_en = ? WHERE id = ?",
        (fecha_pago, timestamp, cuota_id),
    )
    return int(cursor.rowcount)


def mark_pending(conn: Connection, cuota_id: int, timestamp: str) -> int:
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pendiente', fecha_pago = NULL, actualizado_en = ? WHERE id = ?",
        (timestamp, cuota_id),
    )
    return int(cursor.rowcount)


def list_statuses(conn: Connection, cuota_ids: list[int]) -> list[Row]:
    if not cuota_ids:
        return []
    placeholders = ",".join("?" for _ in cuota_ids)
    return conn.execute(
        f"SELECT id, periodo, estado FROM cuotas WHERE id IN ({placeholders})",
        cuota_ids,
    ).fetchall()


def list_existing_generation_pairs(conn: Connection, desde: str, hasta: str) -> set[tuple[int, str]]:
    rows = conn.execute(
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
    return {(int(row["socio_id"]), str(row["periodo"])) for row in rows}


def list_with_socios(conn: Connection, where_sql: str, params: list[object]) -> list[Row]:
    return conn.execute(
        f"""
        SELECT c.*, s.nro_socio, s.apellido, s.nombre, s.dni, s.direccion,
               s.localidad, s.cobrador, s.estado AS estado_socio
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE {where_sql}
        ORDER BY c.periodo DESC, c.estado, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()


def find_by_id(conn: Connection, cuota_id: int) -> Row | None:
    return conn.execute("SELECT * FROM cuotas WHERE id = ?", (cuota_id,)).fetchone()


def find_by_socio_period(conn: Connection, socio_id: int, periodo: str) -> Row | None:
    return conn.execute(
        "SELECT id, estado FROM cuotas WHERE socio_id = ? AND periodo = ?",
        (socio_id, periodo),
    ).fetchone()


def list_paid_periods(conn: Connection, socio_id: int, periodos: list[str]) -> list[Row]:
    if not periodos:
        return []
    placeholders = ",".join("?" for _ in periodos)
    return conn.execute(
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


def mark_existing_as_paid_advance(
    conn: Connection,
    cuota_id: int,
    monto: float,
    fecha_pago: str,
    timestamp: str,
) -> int:
    cursor = conn.execute(
        """
        UPDATE cuotas
        SET monto = ?, estado = 'pagada', fecha_pago = ?, observacion = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (monto, fecha_pago, "Pago adelantado", timestamp, cuota_id),
    )
    return int(cursor.rowcount)


def insert_paid_advance(
    conn: Connection,
    socio_id: int,
    periodo: str,
    monto: float,
    fecha_pago: str,
    timestamp: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO cuotas (socio_id, periodo, monto, estado, fecha_pago, observacion, creado_en, actualizado_en)
        VALUES (?, ?, ?, 'pagada', ?, 'Pago adelantado', ?, ?)
        """,
        (socio_id, periodo, monto, fecha_pago, timestamp, timestamp),
    )
    return int(cursor.lastrowid)


def delete(conn: Connection, cuota_id: int) -> int:
    cursor = conn.execute("DELETE FROM cuotas WHERE id = ?", (cuota_id,))
    return int(cursor.rowcount)


def list_for_print(conn: Connection, periodo: str, cobrador: int, limite_moroso: int, order_sql: str) -> list[Row]:
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
        ORDER BY {order_sql}
        """,
        (periodo, cobrador, limite_moroso),
    ).fetchall()
