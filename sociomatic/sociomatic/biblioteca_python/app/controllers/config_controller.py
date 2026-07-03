from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import config_model, security_model


def get(handler, conn, _query):
    json_response(
        handler,
        {
            "exito": True,
            "config": config_model.get_config(conn),
            "auditoria": security_model.listar_auditoria(conn),
        },
    )


def update(handler, conn, _query):
    security_model.require_admin(handler, conn, "config.predeterminados", "Cambio de configuracion general")
    config_model.update_config(conn, read_json(handler))
    json_response(handler, {"exito": True})


def update_security(handler, conn, _query):
    data = read_json(handler)
    security_model.set_admin_key(conn, data.get("clave_actual", ""), data.get("clave_nueva", ""))
    json_response(handler, {"exito": True})


def create_tipo_socio(handler, conn, _query):
    security_model.require_admin(handler, conn, "config.tipo_socio.crear", "Alta de tipo de socio")
    result = config_model.crear_tipo_socio(conn, read_json(handler))
    json_response(handler, {"exito": True, "id": result["id"]}, HTTPStatus.CREATED)


def update_tipo_socio(handler, conn, _query, tipo_id: str):
    security_model.require_admin(handler, conn, "config.tipo_socio.editar", f"Tipo {tipo_id}")
    config_model.actualizar_tipo_socio(conn, tipo_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete_tipo_socio(handler, conn, _query, tipo_id: str):
    security_model.require_admin(handler, conn, "config.tipo_socio.baja", f"Tipo {tipo_id}")
    config_model.baja_tipo_socio(conn, tipo_id)
    json_response(handler, {"exito": True})


def create_cobrador(handler, conn, _query):
    security_model.require_admin(handler, conn, "config.cobrador.crear", "Alta de cobrador")
    result = config_model.crear_cobrador(conn, read_json(handler))
    json_response(handler, {"exito": True, "id": result["id"]}, HTTPStatus.CREATED)


def update_cobrador(handler, conn, _query, cobrador_id: int):
    security_model.require_admin(handler, conn, "config.cobrador.editar", f"Cobrador {cobrador_id}")
    config_model.actualizar_cobrador(conn, cobrador_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete_cobrador(handler, conn, _query, cobrador_id: int):
    security_model.require_admin(handler, conn, "config.cobrador.baja", f"Cobrador {cobrador_id}")
    config_model.baja_cobrador(conn, cobrador_id)
    json_response(handler, {"exito": True})
