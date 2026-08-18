from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.services import security_service


def session(handler, conn, _query):
    json_response(handler, {"exito": True, **security_service.session_info(handler, conn)})


def login(handler, conn, _query):
    data = read_json(handler)
    usuario = str(data.get("usuario", "")).strip()
    clave = str(data.get("clave", ""))
    try:
        result = security_service.login(conn, usuario, clave)
    except PermissionError:
        json_response(handler, {"exito": False, "error": "Usuario o contrasena incorrectos."}, HTTPStatus.UNAUTHORIZED)
        return
    json_response(
        handler,
        {"exito": True, "usuario": result["usuario"]},
        headers={"Set-Cookie": result["cookie"]},
    )


def logout(handler, conn, _query):
    cookie = security_service.logout(conn, security_service.session_user(handler, conn))
    json_response(handler, {"exito": True}, headers={"Set-Cookie": cookie})


def update_login(handler, conn, _query):
    security_service.set_login_credentials(conn, security_service.admin_key_from_request(handler), read_json(handler))
    json_response(handler, {"exito": True})
