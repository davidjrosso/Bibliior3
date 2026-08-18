from app.models import security_model


def admin_key_from_request(handler) -> str:
    return security_model.admin_key_from_request(handler)


def require_admin_key(conn, admin_key: str, action: str, detail: str = "") -> None:
    if not security_model.verify_admin_key(conn, admin_key):
        raise PermissionError("Esta accion requiere clave de administrador.")
    security_model.audit(conn, action, detail)


def session_info(handler, conn) -> dict:
    return {
        "autenticado": security_model.is_authenticated(handler, conn),
        "usuario": security_model.session_user(handler, conn),
    }


def login(conn, usuario: str, clave: str) -> dict:
    usuario = str(usuario or "").strip()
    if not security_model.verify_login(conn, usuario, str(clave or "")):
        raise PermissionError("Usuario o contrasena incorrectos.")
    security_model.audit(conn, "auth.login", f"Ingreso de {usuario}")
    return {
        "usuario": usuario,
        "cookie": security_model.build_session_cookie(conn, usuario),
    }


def logout(conn, usuario: str | None) -> str:
    usuario = str(usuario or "")
    if usuario:
        security_model.audit(conn, "auth.logout", f"Salida de {usuario}")
    return security_model.clear_session_cookie()


def set_login_credentials(conn, admin_key: str, data: dict) -> None:
    require_admin_key(conn, admin_key, "seguridad.acceso", "Cambio de usuario o contrasena de ingreso")
    security_model.set_login_credentials(conn, data.get("usuario", ""), data.get("clave_nueva", ""))


def set_admin_key(conn, current_key: str, new_key: str) -> None:
    security_model.set_admin_key(conn, current_key, new_key)


def is_authenticated(handler, conn) -> bool:
    return security_model.is_authenticated(handler, conn)


def session_user(handler, conn) -> str | None:
    return security_model.session_user(handler, conn)


def listar_auditoria(conn, limit: int = 20) -> list[dict]:
    return security_model.listar_auditoria(conn, limit)
