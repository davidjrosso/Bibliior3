from http import HTTPStatus

from app.controllers.base_controller import json_response, read_json
from app.models import cuota_model


def index(handler, conn, query):
    json_response(handler, {"exito": True, "cuotas": cuota_model.listar(conn, query)})


def create(handler, conn, _query):
    cuota_id = cuota_model.crear(conn, read_json(handler))
    json_response(handler, {"exito": True, "id": cuota_id}, HTTPStatus.CREATED)


def generate(handler, conn, _query):
    result = cuota_model.generar(conn, read_json(handler))
    json_response(
        handler,
        {"exito": True, "periodo": result["periodo"], "cuotas_creadas": result["cuotas_creadas"]},
    )


def update(handler, conn, _query, cuota_id: int):
    cuota_model.actualizar(conn, cuota_id, read_json(handler))
    json_response(handler, {"exito": True})


def delete(handler, conn, _query, cuota_id: int):
    cuota_model.eliminar(conn, cuota_id)
    json_response(handler, {"exito": True})


def pay(handler, conn, _query, cuota_id: int):
    cuota_model.marcar_pagada(conn, cuota_id)
    json_response(handler, {"exito": True})


def pending(handler, conn, _query, cuota_id: int):
    cuota_model.marcar_pendiente(conn, cuota_id)
    json_response(handler, {"exito": True})

