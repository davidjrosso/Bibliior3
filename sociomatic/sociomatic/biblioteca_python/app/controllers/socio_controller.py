from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import socio_model
from app.settings import COBRADORES


def index(handler, conn, query):
    busqueda = (query.get("q", [""])[0] or "").strip()
    incluir_bajas = query.get("incluir_bajas", ["0"])[0] == "1"
    json_response(
        handler,
        {
            "exito": True,
            "socios": socio_model.listar(conn, busqueda, incluir_bajas),
            "proximo_nro_socio": socio_model.proximo_nro_socio(conn),
            "cobradores": COBRADORES,
        },
    )


def create(handler, conn, _query):
    result = socio_model.crear(conn, read_json(handler))
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
    socio_model.actualizar(conn, socio_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, socio_id: int):
    nro_liberado = socio_model.baja(conn, socio_id)
    json_response(handler, {"exito": True, "nro_liberado": nro_liberado})

