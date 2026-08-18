from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.services import cuota_service, security_service


def index(handler, conn, query):
    json_response(handler, {"exito": True, "cuotas": cuota_service.listar(conn, query)})


def create(handler, conn, _query):
    cuota_id = cuota_service.crear(conn, read_json(handler))
    json_response(handler, {"exito": True, "id": cuota_id}, HTTPStatus.CREATED)


def generate(handler, conn, _query):
    data = read_json(handler)
    result = cuota_service.generar(conn, data, security_service.admin_key_from_request(handler))
    json_response(
        handler,
        {
            "exito": True,
            "periodo": result["periodo"],
            "cuotas_creadas": result["cuotas_creadas"],
            "forzada": result["forzada"],
        },
    )


def generate_control(handler, conn, query):
    periodo = (query.get("periodo", [""])[0] or "").strip()
    json_response(handler, {"exito": True, "control": cuota_service.control_generacion(conn, periodo)})


def generation_missing(handler, conn, query):
    json_response(handler, {"exito": True, **cuota_service.listar_faltantes_generacion(conn, query)})


def advance_payment(handler, conn, _query):
    data = read_json(handler)
    result = cuota_service.pago_adelantado(conn, data, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, **result})


def update(handler, conn, _query, cuota_id: int):
    cuota_service.actualizar(conn, cuota_id, read_json(handler), security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, cuota_id: int):
    cuota_service.eliminar(conn, cuota_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})


def pay(handler, conn, _query, cuota_id: int):
    data = read_json(handler)
    cuota_service.pagar(
        conn,
        cuota_id,
        data.get("fecha_pago"),
        data.get("medio_pago", "efectivo"),
        security_service.admin_key_from_request(handler),
    )
    json_response(handler, {"exito": True})


def pay_many(handler, conn, _query):
    data = read_json(handler)
    result = cuota_service.pagar_varias(conn, data, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True, **result})


def pending(handler, conn, _query, cuota_id: int):
    cuota_service.despagar(conn, cuota_id, security_service.admin_key_from_request(handler))
    json_response(handler, {"exito": True})
