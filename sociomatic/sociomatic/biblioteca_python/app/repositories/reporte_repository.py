from sqlite3 import Connection, Row


def list_socios(conn: Connection, where_sql: str, params: list[object], limit: int) -> list[Row]:
    return conn.execute(
        f"""
        SELECT
            s.id,
            s.nro_socio,
            s.dni,
            s.apellido,
            s.nombre,
            s.telefono,
            s.email,
            s.direccion,
            s.barrio,
            s.localidad,
            s.estado,
            s.cobrador,
            s.fecha_alta,
            s.fecha_baja,
            COALESCE(SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END), 0) AS cuotas_impagas,
            COALESCE(SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END), 0) AS deuda,
            COALESCE(SUM(CASE WHEN c.estado = 'pagada' THEN 1 ELSE 0 END), 0) AS cuotas_pagas
        FROM socios s
        LEFT JOIN cuotas c ON c.socio_id = s.id
        WHERE {where_sql}
        GROUP BY s.id
        ORDER BY s.fecha_baja IS NOT NULL, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()


def count_socios(conn: Connection, where_sql: str, params: list[object]) -> Row:
    return conn.execute(
        f"""
        SELECT COUNT(*) AS cantidad
        FROM socios s
        WHERE {where_sql}
        """,
        params,
    ).fetchone()


def totals_socios(conn: Connection, where_sql: str, params: list[object]) -> Row:
    return conn.execute(
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END), 0) AS cuotas_impagas,
            COALESCE(SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END), 0) AS deuda
        FROM socios s
        LEFT JOIN cuotas c ON c.socio_id = s.id
        WHERE {where_sql}
        """,
        params,
    ).fetchone()


def list_cuotas(conn: Connection, where_sql: str, params: list[object], limit: int) -> list[Row]:
    return conn.execute(
        f"""
        SELECT
            c.id,
            c.periodo,
            c.monto,
            c.estado,
            c.fecha_pago,
            c.observacion,
            s.nro_socio,
            s.dni,
            s.apellido,
            s.nombre,
            s.telefono,
            s.email,
            s.direccion,
            s.barrio,
            s.localidad,
            s.estado AS estado_socio,
            s.cobrador,
            m.medio_pago
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        LEFT JOIN caja_movimientos m ON m.cuota_id = c.id
        WHERE {where_sql}
        ORDER BY c.periodo ASC, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE, c.id ASC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()


def totals_cuotas(conn: Connection, where_sql: str, params: list[object]) -> Row:
    return conn.execute(
        f"""
        SELECT
            COUNT(*) AS cantidad,
            COALESCE(SUM(c.monto), 0) AS monto
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        LEFT JOIN caja_movimientos m ON m.cuota_id = c.id
        WHERE {where_sql}
        """,
        params,
    ).fetchone()


def list_caja_movimientos(conn: Connection, where_sql: str, params: list[object], limit: int) -> list[Row]:
    return conn.execute(
        f"""
        SELECT
            m.id,
            m.fecha,
            m.tipo,
            m.concepto,
            m.descripcion,
            m.monto,
            m.medio_pago,
            m.referencia,
            c.periodo,
            s.nro_socio,
            s.apellido,
            s.nombre
        FROM caja_movimientos m
        LEFT JOIN cuotas c ON c.id = m.cuota_id
        LEFT JOIN socios s ON s.id = c.socio_id
        WHERE {where_sql}
        ORDER BY m.fecha ASC, m.id ASC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()


def totals_caja_movimientos(conn: Connection, where_sql: str, params: list[object]) -> Row:
    return conn.execute(
        f"""
        SELECT
            COUNT(*) AS cantidad,
            COALESCE(SUM(CASE WHEN m.tipo = 'ingreso' THEN m.monto ELSE 0 END), 0) AS ingresos,
            COALESCE(SUM(CASE WHEN m.tipo = 'egreso' THEN m.monto ELSE 0 END), 0) AS egresos
        FROM caja_movimientos m
        LEFT JOIN cuotas c ON c.id = m.cuota_id
        LEFT JOIN socios s ON s.id = c.socio_id
        WHERE {where_sql}
        """,
        params,
    ).fetchone()
