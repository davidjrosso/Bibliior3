from sqlite3 import Connection, Row


def active_member_numbers(conn: Connection) -> set[int]:
    rows = conn.execute("SELECT nro_socio FROM socios WHERE fecha_baja IS NULL").fetchall()
    return {int(row["nro_socio"]) for row in rows}


def find_by_id(conn: Connection, socio_id: int) -> Row | None:
    return conn.execute("SELECT * FROM socios WHERE id = ?", (socio_id,)).fetchone()


def list_ids(conn: Connection, busqueda: str = "", incluir_bajas: bool = False) -> list[int]:
    where = ["1=1"]
    params: list[object] = []
    if not incluir_bajas:
        where.append("fecha_baja IS NULL")
    if busqueda:
        where.append(
            "(CAST(nro_socio AS TEXT) = ? OR apellido LIKE ? OR nombre LIKE ? OR dni LIKE ? OR telefono LIKE ? OR email LIKE ?)"
        )
        like = f"%{busqueda}%"
        params.extend([busqueda, like, like, like, like, like])
    rows = conn.execute(
        f"""
        SELECT id FROM socios
        WHERE {' AND '.join(where)}
        ORDER BY fecha_baja IS NOT NULL, apellido COLLATE NOCASE, nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()
    return [int(row["id"]) for row in rows]


def cuota_summary(conn: Connection, socio_id: int, periodo_actual: str) -> Row:
    return conn.execute(
        """
        SELECT
            SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) AS cuotas_debe,
            SUM(CASE WHEN estado = 'pagada' AND periodo > ? THEN 1 ELSE 0 END) AS cuotas_adelantadas
        FROM cuotas
        WHERE socio_id = ?
        """,
        (periodo_actual, socio_id),
    ).fetchone()


def list_cuotas(conn: Connection, socio_id: int) -> list[Row]:
    return conn.execute(
        "SELECT * FROM cuotas WHERE socio_id = ? ORDER BY periodo ASC",
        (socio_id,),
    ).fetchall()


def insert(conn: Connection, data: dict, timestamp: str) -> int:
    cursor = conn.execute(
        """
        INSERT INTO socios (
            nro_socio, dni, apellido, nombre, telefono, email, direccion, barrio, localidad,
            fecha_nacimiento, ocupacion, estado, cobrador, fecha_alta,
            creado_en, actualizado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nro_socio"],
            data["dni"],
            data["apellido"],
            data["nombre"],
            data["telefono"],
            data["email"],
            data["direccion"],
            data["barrio"],
            data["localidad"],
            data["fecha_nacimiento"],
            data["ocupacion"],
            data["estado"],
            data["cobrador"],
            data["fecha_alta"],
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def update(conn: Connection, socio_id: int, data: dict, timestamp: str) -> None:
    conn.execute(
        """
        UPDATE socios
        SET nro_socio = ?, dni = ?, apellido = ?, nombre = ?, telefono = ?, email = ?,
            direccion = ?, barrio = ?, localidad = ?,
            fecha_nacimiento = ?, ocupacion = ?, estado = ?, cobrador = ?, fecha_alta = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (
            data["nro_socio"],
            data["dni"],
            data["apellido"],
            data["nombre"],
            data["telefono"],
            data["email"],
            data["direccion"],
            data["barrio"],
            data["localidad"],
            data["fecha_nacimiento"],
            data["ocupacion"],
            data["estado"],
            data["cobrador"],
            data["fecha_alta"],
            timestamp,
            socio_id,
        ),
    )


def mark_deleted(conn: Connection, socio_id: int, fecha_baja: str, timestamp: str) -> None:
    conn.execute(
        "UPDATE socios SET fecha_baja = ?, actualizado_en = ? WHERE id = ?",
        (fecha_baja, timestamp, socio_id),
    )


def delete_caja_movimientos_for_socio(conn: Connection, socio_id: int) -> None:
    conn.execute(
        """
        DELETE FROM caja_movimientos
        WHERE cuota_id IN (SELECT id FROM cuotas WHERE socio_id = ?)
        """,
        (socio_id,),
    )


def delete_cuotas(conn: Connection, socio_id: int) -> None:
    conn.execute("DELETE FROM cuotas WHERE socio_id = ?", (socio_id,))


def list_morosos(conn: Connection, limite: int) -> list[Row]:
    return conn.execute(
        """
        SELECT
            s.id,
            s.nro_socio,
            s.apellido,
            s.nombre,
            s.dni,
            s.telefono,
            s.email,
            s.direccion,
            s.localidad,
            s.cobrador,
            COUNT(c.id) AS cuotas_impagas,
            COALESCE(SUM(c.monto), 0) AS deuda
        FROM socios s
        JOIN cuotas c ON c.socio_id = s.id AND c.estado = 'pendiente'
        WHERE s.fecha_baja IS NULL
        GROUP BY s.id
        HAVING COUNT(c.id) > ?
        ORDER BY cuotas_impagas DESC, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        """,
        (limite,),
    ).fetchall()


def count_generation_targets(conn: Connection, periodo: str) -> int:
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


def list_generation_targets(conn: Connection, periodo_hasta: str) -> list[Row]:
    return conn.execute(
        """
        SELECT s.id, s.nro_socio, s.apellido, s.nombre, s.dni, s.telefono, s.cobrador, s.fecha_alta, s.estado
        FROM socios s
        WHERE s.fecha_baja IS NULL
          AND s.cobrador IN (1, 3)
          AND s.fecha_alta <= ?
        ORDER BY s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE, s.nro_socio
        """,
        (f"{periodo_hasta}-31",),
    ).fetchall()
