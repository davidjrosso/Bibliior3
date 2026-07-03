import hashlib
import hmac
import secrets

from app.models.helpers import now_iso


DEFAULT_ADMIN_KEY = "1234"
ITERATIONS = 120_000


def _hash_key(key: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", key.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return digest.hex()


def ensure_default_admin_key(conn) -> None:
    exists = conn.execute("SELECT valor FROM configuracion WHERE clave = 'admin_key_hash'").fetchone()
    if exists:
        return
    salt = secrets.token_hex(16)
    conn.execute("INSERT INTO configuracion (clave, valor) VALUES ('admin_key_salt', ?)", (salt,))
    conn.execute(
        "INSERT INTO configuracion (clave, valor) VALUES ('admin_key_hash', ?)",
        (_hash_key(DEFAULT_ADMIN_KEY, salt),),
    )


def verify_admin_key(conn, key: str) -> bool:
    salt_row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'admin_key_salt'").fetchone()
    hash_row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'admin_key_hash'").fetchone()
    if not salt_row or not hash_row:
        ensure_default_admin_key(conn)
        salt_row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'admin_key_salt'").fetchone()
        hash_row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'admin_key_hash'").fetchone()
    given = _hash_key(str(key or ""), salt_row["valor"])
    return hmac.compare_digest(given, hash_row["valor"])


def set_admin_key(conn, current_key: str, new_key: str) -> None:
    if not verify_admin_key(conn, current_key):
        raise PermissionError("Clave de administrador incorrecta.")
    new_key = str(new_key or "").strip()
    if len(new_key) < 4:
        raise ValueError("La nueva clave debe tener al menos 4 caracteres.")
    salt = secrets.token_hex(16)
    for key, value in {"admin_key_salt": salt, "admin_key_hash": _hash_key(new_key, salt)}.items():
        conn.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (key, value),
        )
    audit(conn, "seguridad.clave", "Cambio de clave de administrador")


def admin_key_from_request(handler) -> str:
    return handler.headers.get("X-Admin-Key", "")


def require_admin(handler, conn, action: str, detail: str = "") -> None:
    if not verify_admin_key(conn, admin_key_from_request(handler)):
        raise PermissionError("Esta accion requiere clave de administrador.")
    audit(conn, action, detail)


def audit(conn, action: str, detail: str = "") -> None:
    conn.execute(
        """
        INSERT INTO auditoria (accion, detalle, creado_en)
        VALUES (?, ?, ?)
        """,
        (action, detail, now_iso()),
    )


def listar_auditoria(conn, limit: int = 20) -> list[dict]:
    return [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    ]
