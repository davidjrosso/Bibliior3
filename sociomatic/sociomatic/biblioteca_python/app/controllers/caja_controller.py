from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import caja_model, security_model


def get(handler, conn, query):
    fecha = (query.get("fecha", [""])[0] or "").strip() or None
    data = caja_model.obtener(conn, fecha)
    json_response(handler, {"exito": True, **data})


def update_day(handler, conn, _query):
    data = read_json(handler)
    actual = caja_model.obtener(conn, data.get("fecha"))["dia"]
    if actual and int(actual["cerrado"] or 0) == 1:
        security_model.require_admin(handler, conn, "caja.dia.editar_cerrada", f"Caja {actual['fecha']}")
    caja_model.actualizar_dia(conn, data)
    json_response(handler, {"exito": True})


def create_movement(handler, conn, _query):
    data = read_json(handler)
    actual = caja_model.obtener(conn, data.get("fecha"))["dia"]
    if actual and int(actual["cerrado"] or 0) == 1:
        security_model.require_admin(handler, conn, "caja.movimiento.crear_cerrada", f"Caja {actual['fecha']}")
    movimiento_id = caja_model.crear_movimiento(conn, data)
    json_response(handler, {"exito": True, "id": movimiento_id}, HTTPStatus.CREATED)


def update_movement(handler, conn, _query, movimiento_id: int):
    security_model.require_admin(handler, conn, "caja.movimiento.editar", f"Movimiento {movimiento_id}")
    caja_model.actualizar_movimiento(conn, movimiento_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete_movement(handler, conn, _query, movimiento_id: int):
    security_model.require_admin(handler, conn, "caja.movimiento.eliminar", f"Movimiento {movimiento_id}")
    caja_model.eliminar_movimiento(conn, movimiento_id)
    json_response(handler, {"exito": True})
