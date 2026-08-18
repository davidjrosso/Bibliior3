from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.services import security_service, socio_service


def index(handler, conn, query):
    busqueda = (query.get("q", [""])[0] or "").strip()
    incluir_bajas = query.get("incluir_bajas", ["0"])[0] == "1"
    json_response(
        handler,
        {"exito": True, **socio_service.index_data(conn, busqueda, incluir_bajas)},
    )


def morosos(handler, conn, _query):
    json_response(handler, {"exito": True, "morosos": socio_service.listar_morosos(conn)})


def create(handler, conn, _query):
    result = socio_service.crear(conn, read_json(handler))
    json_response(
        handler,
        {"exito": True, "id": result["id"], "nro_socio": result["nro_socio"]},
        HTTPStatus.CREATED,
    )


def show(handler, conn, _query, socio_id: int):
    detalle = socio_service.detalle(conn, socio_id)
    if not detalle:
        json_response(handler, {"error": "Socio no encontrado"}, HTTPStatus.NOT_FOUND)
        return
    json_response(handler, {"exito": True, **detalle})


def update(handler, conn, _query, socio_id: int):
    socio_service.actualizar(conn, socio_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, socio_id: int):
    nro_liberado = socio_service.baja(conn, socio_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, "nro_liberado": nro_liberado})
