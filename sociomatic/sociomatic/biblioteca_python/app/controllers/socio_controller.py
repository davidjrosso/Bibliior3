from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import config_model, security_model, socio_model
from app.services import socio_service


def index(handler, conn, query):
    busqueda = (query.get("q", [""])[0] or "").strip()
    incluir_bajas = query.get("incluir_bajas", ["0"])[0] == "1"
    json_response(
        handler,
        {
            "exito": True,
            "socios": socio_model.listar(conn, busqueda, incluir_bajas),
            "proximo_nro_socio": socio_model.proximo_nro_socio(conn),
            "cobradores": config_model.listar_cobradores(conn),
            "tipos_socio": config_model.listar_tipos_socio(conn),
        },
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
    socio = socio_model.obtener(conn, socio_id)
    if not socio:
        json_response(handler, {"error": "Socio no encontrado"}, HTTPStatus.NOT_FOUND)
        return
    json_response(
        handler,
        {"exito": True, "socio": socio, "cuotas": socio_model.obtener_cuotas(conn, socio_id)},
    )


def update(handler, conn, _query, socio_id: int):
    socio_service.actualizar(conn, socio_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, socio_id: int):
    security_model.require_admin(handler, conn, "socio.baja", f"Socio {socio_id}")
    nro_liberado = socio_service.baja(conn, socio_id)
    json_response(handler, {"exito": True, "nro_liberado": nro_liberado})
