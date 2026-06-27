import sqlite3

from app.settings import DATA_DIR, DB_PATH


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
                estado TEXT NOT NULL CHECK (estado IN ('activo', 'jubilado')),
                cobrador INTEGER NOT NULL CHECK (cobrador IN (1, 2, 3, 4, 5)),
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
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(socios)").fetchall()}
        if "telefono" not in columns:
            conn.execute("ALTER TABLE socios ADD COLUMN telefono TEXT NOT NULL DEFAULT ''")
        if "email" not in columns:
            conn.execute("ALTER TABLE socios ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        for key, value in {"monto_activo": "1000", "monto_jubilado": "700"}.items():
            conn.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                (key, value),
            )
