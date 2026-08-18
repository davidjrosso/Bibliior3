from sqlite3 import Connection, Row


def list_config(conn: Connection) -> list[Row]:
    return conn.execute("SELECT clave, valor FROM configuracion").fetchall()


def get_config_value(conn: Connection, clave: str) -> Row | None:
    return conn.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()


def upsert_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute(
        "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )


def insert_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute("INSERT INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))


def insert_or_replace_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))


def cuota_monto(conn: Connection, estado: str) -> Row | None:
    return conn.execute("SELECT monto FROM tipos_socio WHERE id = ?", (estado,)).fetchone()


def list_tipos_socio(conn: Connection, solo_activos: bool = False) -> list[Row]:
    where = "WHERE activo = 1" if solo_activos else ""
    return conn.execute(
        f"SELECT id, nombre, monto, activo FROM tipos_socio {where} ORDER BY nombre COLLATE NOCASE"
    ).fetchall()


def insert_tipo_socio(conn: Connection, tipo_id: str, nombre: str, monto: float, timestamp: str) -> None:
    conn.execute(
        """
        INSERT INTO tipos_socio (id, nombre, monto, activo, creado_en, actualizado_en)
        VALUES (?, ?, ?, 1, ?, ?)
        """,
        (tipo_id, nombre, monto, timestamp, timestamp),
    )


def update_tipo_socio(
    conn: Connection,
    tipo_id: str,
    nombre: str,
    monto: float,
    activo: int,
    timestamp: str,
) -> int:
    cursor = conn.execute(
        """
        UPDATE tipos_socio
        SET nombre = ?, monto = ?, activo = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (nombre, monto, activo, timestamp, tipo_id),
    )
    return int(cursor.rowcount)


def count_socios_by_tipo(conn: Connection, tipo_id: str) -> int:
    return int(conn.execute("SELECT COUNT(*) AS total FROM socios WHERE estado = ?", (tipo_id,)).fetchone()["total"] or 0)


def deactivate_tipo_socio(conn: Connection, tipo_id: str, timestamp: str) -> None:
    conn.execute("UPDATE tipos_socio SET activo = 0, actualizado_en = ? WHERE id = ?", (timestamp, tipo_id))


def delete_tipo_socio(conn: Connection, tipo_id: str) -> int:
    cursor = conn.execute("DELETE FROM tipos_socio WHERE id = ?", (tipo_id,))
    return int(cursor.rowcount)


def list_cobradores(conn: Connection, solo_activos: bool = False) -> list[Row]:
    where = "WHERE activo = 1" if solo_activos else ""
    return conn.execute(f"SELECT id, nombre, activo FROM cobradores {where} ORDER BY id").fetchall()


def insert_cobrador(conn: Connection, nombre: str, timestamp: str) -> int:
    cursor = conn.execute(
        "INSERT INTO cobradores (nombre, activo, creado_en, actualizado_en) VALUES (?, 1, ?, ?)",
        (nombre, timestamp, timestamp),
    )
    return int(cursor.lastrowid)


def update_cobrador(conn: Connection, cobrador_id: int, nombre: str, activo: int, timestamp: str) -> int:
    cursor = conn.execute(
        "UPDATE cobradores SET nombre = ?, activo = ?, actualizado_en = ? WHERE id = ?",
        (nombre, activo, timestamp, cobrador_id),
    )
    return int(cursor.rowcount)


def count_socios_by_cobrador(conn: Connection, cobrador_id: int) -> int:
    return int(
        conn.execute("SELECT COUNT(*) AS total FROM socios WHERE cobrador = ?", (cobrador_id,)).fetchone()["total"] or 0
    )


def deactivate_cobrador(conn: Connection, cobrador_id: int, timestamp: str) -> None:
    conn.execute("UPDATE cobradores SET activo = 0, actualizado_en = ? WHERE id = ?", (timestamp, cobrador_id))


def delete_cobrador(conn: Connection, cobrador_id: int) -> int:
    cursor = conn.execute("DELETE FROM cobradores WHERE id = ?", (cobrador_id,))
    return int(cursor.rowcount)
