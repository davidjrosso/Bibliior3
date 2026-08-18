from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.services import caja_service, security_service


def get(handler, conn, query):
    fecha = (query.get("fecha", [""])[0] or "").strip() or None
    data = caja_service.obtener(conn, fecha)
    json_response(handler, {"exito": True, **data})


def daily_list(handler, conn, query):
    desde = (query.get("desde", [""])[0] or "").strip() or None
    hasta = (query.get("hasta", [""])[0] or "").strip() or None
    data = caja_service.listado_diario(conn, desde, hasta)
    json_response(handler, {"exito": True, **data})


def update_day(handler, conn, _query):
    data = read_json(handler)
    caja_service.actualizar_dia(conn, data, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def create_movement(handler, conn, _query):
    data = read_json(handler)
    movimiento_id = caja_service.crear_movimiento(conn, data, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, "id": movimiento_id}, HTTPStatus.CREATED)


def update_movement(handler, conn, _query, movimiento_id: int):
    caja_service.actualizar_movimiento(
        conn,
        movimiento_id,
        read_json(handler),
        security_service.admin_key_from_request(handler),
    )
    json_response(handler, {"exito": True})


def delete_movement(handler, conn, _query, movimiento_id: int):
    caja_service.eliminar_movimiento(conn, movimiento_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})
