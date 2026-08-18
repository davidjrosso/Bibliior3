import hashlib
import hmac
import secrets
import time
from http import cookies

from app.models.helpers import now_iso
from app.repositories import security_repository


DEFAULT_ADMIN_KEY = "1234"
DEFAULT_LOGIN_USER = "admin"
DEFAULT_LOGIN_PASSWORD = "1234"
ITERATIONS = 120_000
SESSION_COOKIE = "biblioteca_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


def _hash_key(key: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", key.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return digest.hex()


def ensure_default_admin_key(conn) -> None:
    exists = security_repository.get_config_value(conn, "admin_key_hash")
    if exists:
        return
    salt = secrets.token_hex(16)
    security_repository.insert_config_value(conn, "admin_key_salt", salt)
    security_repository.insert_config_value(conn, "admin_key_hash", _hash_key(DEFAULT_ADMIN_KEY, salt))


def ensure_default_login(conn) -> None:
    user = security_repository.get_config_value(conn, "login_user")
    password_hash = security_repository.get_config_value(conn, "login_password_hash")
    secret = security_repository.get_config_value(conn, "session_secret")
    if not user:
        security_repository.insert_config_value(conn, "login_user", DEFAULT_LOGIN_USER)
    if not password_hash:
        salt = secrets.token_hex(16)
        security_repository.insert_or_replace_config_value(conn, "login_password_salt", salt)
        security_repository.insert_config_value(conn, "login_password_hash", _hash_key(DEFAULT_LOGIN_PASSWORD, salt))
    if not secret:
        security_repository.insert_config_value(conn, "session_secret", secrets.token_hex(32))


def verify_login(conn, usuario: str, clave: str) -> bool:
    ensure_default_login(conn)
    user_row = security_repository.get_config_value(conn, "login_user")
    salt_row = security_repository.get_config_value(conn, "login_password_salt")
    hash_row = security_repository.get_config_value(conn, "login_password_hash")
    if not user_row or not salt_row or not hash_row:
        return False
    if not hmac.compare_digest(str(usuario or ""), user_row["valor"]):
        return False
    given = _hash_key(str(clave or ""), salt_row["valor"])
    return hmac.compare_digest(given, hash_row["valor"])


def set_login_credentials(conn, usuario: str, clave_nueva: str) -> None:
    usuario = str(usuario or "").strip()
    clave_nueva = str(clave_nueva or "").strip()
    if len(usuario) < 3:
        raise ValueError("El usuario debe tener al menos 3 caracteres.")
    if "|" in usuario:
        raise ValueError("El usuario no puede contener el caracter |.")
    if len(clave_nueva) < 4:
        raise ValueError("La contrasena debe tener al menos 4 caracteres.")
    salt = secrets.token_hex(16)
    values = {
        "login_user": usuario,
        "login_password_salt": salt,
        "login_password_hash": _hash_key(clave_nueva, salt),
        "session_secret": secrets.token_hex(32),
    }
    for key, value in values.items():
        security_repository.upsert_config_value(conn, key, value)


def build_session_cookie(conn, usuario: str) -> str:
    ensure_default_login(conn)
    expires = int(time.time()) + SESSION_TTL_SECONDS
    nonce = secrets.token_urlsafe(16)
    payload = f"{usuario}|{expires}|{nonce}"
    token = f"{payload}|{_sign_session(conn, payload)}"
    return f"{SESSION_COOKIE}={token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; HttpOnly; SameSite=Lax"


def clear_session_cookie() -> str:
    return f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"


def is_authenticated(handler, conn) -> bool:
    return session_user(handler, conn) is not None


def session_user(handler, conn) -> str | None:
    token = _cookie_value(handler, SESSION_COOKIE)
    if not token:
        return None
    parts = token.split("|")
    if len(parts) != 4:
        return None
    usuario, expires_text, nonce, signature = parts
    try:
        expires = int(expires_text)
    except ValueError:
        return None
    if expires < int(time.time()) or not nonce:
        return None
    payload = f"{usuario}|{expires}|{nonce}"
    if not hmac.compare_digest(signature, _sign_session(conn, payload)):
        return None
    user_row = security_repository.get_config_value(conn, "login_user")
    if not user_row or not hmac.compare_digest(usuario, user_row["valor"]):
        return None
    return usuario


def _sign_session(conn, payload: str) -> str:
    ensure_default_login(conn)
    secret = security_repository.get_config_value(conn, "session_secret")["valor"]
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _cookie_value(handler, name: str) -> str:
    header = handler.headers.get("Cookie", "")
    jar = cookies.SimpleCookie()
    try:
        jar.load(header)
    except cookies.CookieError:
        return ""
    return jar[name].value if name in jar else ""


def verify_admin_key(conn, key: str) -> bool:
    salt_row = security_repository.get_config_value(conn, "admin_key_salt")
    hash_row = security_repository.get_config_value(conn, "admin_key_hash")
    if not salt_row or not hash_row:
        ensure_default_admin_key(conn)
        salt_row = security_repository.get_config_value(conn, "admin_key_salt")
        hash_row = security_repository.get_config_value(conn, "admin_key_hash")
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
        security_repository.upsert_config_value(conn, key, value)
    audit(conn, "seguridad.clave", "Cambio de clave de administrador")


def admin_key_from_request(handler) -> str:
    return handler.headers.get("X-Admin-Key", "")


def require_admin(handler, conn, action: str, detail: str = "") -> None:
    if not verify_admin_key(conn, admin_key_from_request(handler)):
        raise PermissionError("Esta accion requiere clave de administrador.")
    audit(conn, action, detail)


def audit(conn, action: str, detail: str = "") -> None:
    security_repository.insert_audit(conn, action, detail, now_iso())


def listar_auditoria(conn, limit: int = 20) -> list[dict]:
    return [dict(row) for row in security_repository.list_audit(conn, limit)]
