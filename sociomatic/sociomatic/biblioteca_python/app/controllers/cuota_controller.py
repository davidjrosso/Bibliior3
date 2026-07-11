from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import caja_model, cuota_model, security_model
from app.models.helpers import today_iso
from app.services import cuota_service


def index(handler, conn, query):
    json_response(handler, {"exito": True, "cuotas": cuota_model.listar(conn, query)})


def create(handler, conn, _query):
    cuota_id = cuota_service.crear(conn, read_json(handler))
    json_response(handler, {"exito": True, "id": cuota_id}, HTTPStatus.CREATED)


def generate(handler, conn, _query):
    result = cuota_service.generar(conn, read_json(handler))
    json_response(
        handler,
        {"exito": True, "periodo": result["periodo"], "cuotas_creadas": result["cuotas_creadas"]},
    )


def generate_control(handler, conn, query):
    periodo = (query.get("periodo", [""])[0] or "").strip()
    json_response(handler, {"exito": True, "control": cuota_service.control_generacion(conn, periodo)})


def advance_payment(handler, conn, _query):
    data = read_json(handler)
    fecha_pago = data.get("fecha_pago") or today_iso()
    caja_dia = caja_model.obtener(conn, fecha_pago)["dia"]
    if caja_dia and int(caja_dia["cerrado"] or 0) == 1:
        security_model.require_admin(handler, conn, "cuota.adelanto_caja_cerrada", f"Caja {fecha_pago}")
    result = cuota_service.pago_adelantado(conn, data)
    json_response(handler, {"exito": True, **result})


def update(handler, conn, _query, cuota_id: int):
    security_model.require_admin(handler, conn, "cuota.editar", f"Cuota {cuota_id}")
    cuota_service.actualizar(conn, cuota_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, cuota_id: int):
    security_model.require_admin(handler, conn, "cuota.eliminar", f"Cuota {cuota_id}")
    cuota_service.eliminar(conn, cuota_id)
    json_response(handler, {"exito": True})


def pay(handler, conn, _query, cuota_id: int):
    data = read_json(handler)
    fecha_pago = data.get("fecha_pago") or today_iso()
    caja_dia = caja_model.obtener(conn, fecha_pago)["dia"]
    if caja_dia and int(caja_dia["cerrado"] or 0) == 1:
        security_model.require_admin(handler, conn, "cuota.pagar_caja_cerrada", f"Cuota {cuota_id}")
    cuota_service.pagar(conn, cuota_id, fecha_pago, data.get("medio_pago", "efectivo"))
    json_response(handler, {"exito": True})


def pay_many(handler, conn, _query):
    data = read_json(handler)
    fecha_pago = data.get("fecha_pago") or today_iso()
    caja_dia = caja_model.obtener(conn, fecha_pago)["dia"]
    if caja_dia and int(caja_dia["cerrado"] or 0) == 1:
        security_model.require_admin(handler, conn, "cuota.pagar_caja_cerrada", f"Caja {fecha_pago}")
    result = cuota_model.marcar_pagadas(conn, data)
    json_response(handler, {"exito": True, **result})


def pending(handler, conn, _query, cuota_id: int):
    security_model.require_admin(handler, conn, "cuota.despagar", f"Cuota {cuota_id}")
    cuota_service.despagar(conn, cuota_id)
    json_response(handler, {"exito": True})
