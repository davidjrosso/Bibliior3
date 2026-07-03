import sqlite3

from app.settings import COBRADORES, DATA_DIR, DB_PATH


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tipos_socio (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                monto REAL NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cobradores (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS socios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nro_socio INTEGER NOT NULL,
                dni TEXT NOT NULL,
                apellido TEXT NOT NULL,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                direccion TEXT NOT NULL DEFAULT '',
                barrio TEXT NOT NULL DEFAULT '',
                localidad TEXT NOT NULL DEFAULT '',
                fecha_nacimiento TEXT,
                ocupacion TEXT NOT NULL DEFAULT '',
                estado TEXT NOT NULL,
                cobrador INTEGER NOT NULL,
                fecha_alta TEXT NOT NULL,
                fecha_baja TEXT,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ux_socios_nro_activo
                ON socios(nro_socio)
                WHERE fecha_baja IS NULL;

            CREATE UNIQUE INDEX IF NOT EXISTS ux_socios_dni_activo
                ON socios(dni)
                WHERE fecha_baja IS NULL;

            CREATE TABLE IF NOT EXISTS cuotas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
                periodo TEXT NOT NULL,
                monto REAL NOT NULL,
                estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'pagada')),
                fecha_pago TEXT,
                observacion TEXT NOT NULL DEFAULT '',
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL,
                UNIQUE(socio_id, periodo)
            );

            CREATE TABLE IF NOT EXISTS caja_dias (
                fecha TEXT PRIMARY KEY,
                saldo_inicial REAL NOT NULL DEFAULT 0,
                observacion TEXT NOT NULL DEFAULT '',
                cerrado INTEGER NOT NULL DEFAULT 0,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS caja_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
                concepto TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                monto REAL NOT NULL,
                medio_pago TEXT NOT NULL DEFAULT 'efectivo',
                referencia TEXT NOT NULL DEFAULT '',
                cuota_id INTEGER REFERENCES cuotas(id) ON DELETE SET NULL,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL,
                FOREIGN KEY (fecha) REFERENCES caja_dias(fecha) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                accion TEXT NOT NULL,
                detalle TEXT NOT NULL DEFAULT '',
                creado_en TEXT NOT NULL
            );
            """
        )
        _migrar_socios_sin_checks(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(socios)").fetchall()}
        if "telefono" not in columns:
            conn.execute("ALTER TABLE socios ADD COLUMN telefono TEXT NOT NULL DEFAULT ''")
        if "email" not in columns:
            conn.execute("ALTER TABLE socios ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        caja_columns = {row["name"] for row in conn.execute("PRAGMA table_info(caja_movimientos)").fetchall()}
        if "cuota_id" not in caja_columns:
            conn.execute("ALTER TABLE caja_movimientos ADD COLUMN cuota_id INTEGER REFERENCES cuotas(id) ON DELETE SET NULL")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_caja_movimientos_cuota
                ON caja_movimientos(cuota_id)
                WHERE cuota_id IS NOT NULL
            """
        )
        _migrar_cobros_cuotas_pagadas(conn)
        from app.models.config_model import CONFIG_DEFAULTS
        from app.models.helpers import now_iso

        for key, value in CONFIG_DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                (key, value),
            )
        timestamp = now_iso()
        for tipo_id, nombre, monto in (("activo", "Activo", 1000), ("jubilado", "Jubilado", 700)):
            conn.execute(
                """
                INSERT OR IGNORE INTO tipos_socio (id, nombre, monto, activo, creado_en, actualizado_en)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (tipo_id, nombre, monto, timestamp, timestamp),
            )
        for cobrador_id, nombre in COBRADORES.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO cobradores (id, nombre, activo, creado_en, actualizado_en)
                VALUES (?, ?, 1, ?, ?)
                """,
                (cobrador_id, nombre, timestamp, timestamp),
            )
        _migrar_config_vieja_a_catalogos(conn)
        from app.models.security_model import ensure_default_admin_key

        ensure_default_admin_key(conn)


def _migrar_socios_sin_checks(conn: sqlite3.Connection) -> None:
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'socios'"
    ).fetchone()
    if not sql or "CHECK (estado IN" not in sql["sql"]:
        return
    conn.executescript(
        """
        DROP INDEX IF EXISTS ux_socios_nro_activo;
        DROP INDEX IF EXISTS ux_socios_dni_activo;

        CREATE TABLE socios_migracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_socio INTEGER NOT NULL,
            dni TEXT NOT NULL,
            apellido TEXT NOT NULL,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            direccion TEXT NOT NULL DEFAULT '',
            barrio TEXT NOT NULL DEFAULT '',
            localidad TEXT NOT NULL DEFAULT '',
            fecha_nacimiento TEXT,
            ocupacion TEXT NOT NULL DEFAULT '',
            estado TEXT NOT NULL,
            cobrador INTEGER NOT NULL,
            fecha_alta TEXT NOT NULL,
            fecha_baja TEXT,
            creado_en TEXT NOT NULL,
            actualizado_en TEXT NOT NULL
        );

        INSERT INTO socios_migracion (
            id, nro_socio, dni, apellido, nombre, telefono, email, direccion, barrio, localidad,
            fecha_nacimiento, ocupacion, estado, cobrador, fecha_alta, fecha_baja, creado_en, actualizado_en
        )
        SELECT
            id, nro_socio, dni, apellido, nombre,
            COALESCE(telefono, ''), COALESCE(email, ''), direccion, barrio, localidad,
            fecha_nacimiento, ocupacion, estado, cobrador, fecha_alta, fecha_baja, creado_en, actualizado_en
        FROM socios;

        DROP TABLE socios;
        ALTER TABLE socios_migracion RENAME TO socios;

        CREATE UNIQUE INDEX IF NOT EXISTS ux_socios_nro_activo
            ON socios(nro_socio)
            WHERE fecha_baja IS NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS ux_socios_dni_activo
            ON socios(dni)
            WHERE fecha_baja IS NULL;
        """
    )


def _migrar_config_vieja_a_catalogos(conn: sqlite3.Connection) -> None:
    from app.models.helpers import now_iso

    flag = conn.execute(
        "SELECT valor FROM configuracion WHERE clave = 'catalogos_migrados_desde_config'"
    ).fetchone()
    if flag:
        return
    rows = conn.execute("SELECT clave, valor FROM configuracion").fetchall()
    config = {row["clave"]: row["valor"] for row in rows}
    if "monto_activo" in config:
        conn.execute(
            "UPDATE tipos_socio SET monto = ?, actualizado_en = ? WHERE id = 'activo'",
            (float(config["monto_activo"]), now_iso()),
        )
    if "monto_jubilado" in config:
        conn.execute(
            "UPDATE tipos_socio SET monto = ?, actualizado_en = ? WHERE id = 'jubilado'",
            (float(config["monto_jubilado"]), now_iso()),
        )
    for number in COBRADORES:
        key = f"cobrador_{number}"
        if key in config and config[key].strip():
            conn.execute(
                "UPDATE cobradores SET nombre = ?, actualizado_en = ? WHERE id = ?",
                (config[key].strip(), now_iso(), number),
            )
    conn.execute(
        "INSERT INTO configuracion (clave, valor) VALUES ('catalogos_migrados_desde_config', '1')"
    )


def _migrar_cobros_cuotas_pagadas(conn: sqlite3.Connection) -> None:
    from app.models import caja_model

    rows = conn.execute(
        """
        SELECT c.id
        FROM cuotas c
        LEFT JOIN caja_movimientos m ON m.cuota_id = c.id
        WHERE c.estado = 'pagada'
          AND m.id IS NULL
        """
    ).fetchall()
    for row in rows:
        caja_model.registrar_cobro_cuota(conn, row["id"])
