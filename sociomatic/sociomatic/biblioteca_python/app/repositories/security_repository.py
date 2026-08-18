from sqlite3 import Connection, Row


def get_config_value(conn: Connection, clave: str) -> Row | None:
    return conn.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()


def insert_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute("INSERT INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))


def insert_or_replace_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))


def upsert_config_value(conn: Connection, clave: str, valor: str) -> None:
    conn.execute(
        "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )


def insert_audit(conn: Connection, action: str, detail: str, timestamp: str) -> None:
    conn.execute(
        """
        INSERT INTO auditoria (accion, detalle, creado_en)
        VALUES (?, ?, ?)
        """,
        (action, detail, timestamp),
    )


def list_audit(conn: Connection, limit: int) -> list[Row]:
    return conn.execute(
        "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
