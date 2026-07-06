from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import security_model


def session(handler, conn, _query):
    json_response(
        handler,
        {
            "exito": True,
            "autenticado": security_model.is_authenticated(handler, conn),
            "usuario": security_model.session_user(handler, conn),
        },
    )


def login(handler, conn, _query):
    data = read_json(handler)
    usuario = str(data.get("usuario", "")).strip()
    clave = str(data.get("clave", ""))
    if not security_model.verify_login(conn, usuario, clave):
        json_response(handler, {"exito": False, "error": "Usuario o contrasena incorrectos."}, HTTPStatus.UNAUTHORIZED)
        return
    security_model.audit(conn, "auth.login", f"Ingreso de {usuario}")
    json_response(
        handler,
        {"exito": True, "usuario": usuario},
        headers={"Set-Cookie": security_model.build_session_cookie(conn, usuario)},
    )


def logout(handler, conn, _query):
    usuario = security_model.session_user(handler, conn) or ""
    if usuario:
        security_model.audit(conn, "auth.logout", f"Salida de {usuario}")
    json_response(handler, {"exito": True}, headers={"Set-Cookie": security_model.clear_session_cookie()})


def update_login(handler, conn, _query):
    security_model.require_admin(handler, conn, "seguridad.acceso", "Cambio de usuario o contrasena de ingreso")
    data = read_json(handler)
    security_model.set_login_credentials(
        conn,
        data.get("usuario", ""),
        data.get("clave_nueva", ""),
    )
    json_response(handler, {"exito": True})
