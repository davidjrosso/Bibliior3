from sqlite3 import Connection, Row


def socios_summary(conn: Connection) -> Row:
    return conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = 'activo' THEN 1 ELSE 0 END) AS activos,
            SUM(CASE WHEN estado = 'jubilado' THEN 1 ELSE 0 END) AS jubilados,
            SUM(CASE WHEN cobrador = 1 THEN 1 ELSE 0 END) AS cobrador_1,
            SUM(CASE WHEN cobrador = 3 THEN 1 ELSE 0 END) AS cobrador_3
        FROM socios
        WHERE fecha_baja IS NULL
        """
    ).fetchone()


def cuotas_period_summary(conn: Connection, periodo: str) -> Row:
    return conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN c.estado = 'pagada' THEN 1 ELSE 0 END) AS pagadas,
            SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
          AND c.periodo = ?
        """,
        (periodo,),
    ).fetchone()


def cuotas_global_summary(conn: Connection) -> Row:
    return conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN c.estado = 'pagada' THEN 1 ELSE 0 END) AS pagadas,
            SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
        """
    ).fetchone()


def cuotas_by_cobrador(conn: Connection, periodo: str) -> list[Row]:
    return conn.execute(
        """
        SELECT
            s.cobrador,
            COUNT(c.id) AS cuotas,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
          AND c.periodo = ?
        GROUP BY s.cobrador
        ORDER BY s.cobrador
        """,
        (periodo,),
    ).fetchall()
