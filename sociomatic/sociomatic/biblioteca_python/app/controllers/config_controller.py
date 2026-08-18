from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.services import config_service, security_service


def get(handler, conn, _query):
    json_response(handler, {"exito": True, **config_service.get(conn)})


def update(handler, conn, _query):
    config_service.update(conn, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def update_security(handler, conn, _query):
    config_service.update_security(conn, read_json(handler))
    json_response(handler, {"exito": True})


def create_tipo_socio(handler, conn, _query):
    result = config_service.create_tipo_socio(conn, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, "id": result["id"]}, HTTPStatus.CREATED)


def update_tipo_socio(handler, conn, _query, tipo_id: str):
    config_service.update_tipo_socio(conn, tipo_id, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def delete_tipo_socio(handler, conn, _query, tipo_id: str):
    config_service.delete_tipo_socio(conn, tipo_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def create_cobrador(handler, conn, _query):
    result = config_service.create_cobrador(conn, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, "id": result["id"]}, HTTPStatus.CREATED)


def update_cobrador(handler, conn, _query, cobrador_id: int):
    config_service.update_cobrador(conn, cobrador_id, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def delete_cobrador(handler, conn, _query, cobrador_id: int):
    config_service.delete_cobrador(conn, cobrador_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})
