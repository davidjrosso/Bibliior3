from app.models import cuota_model


def crear(conn, data: dict) -> int:
    return cuota_model.crear(conn, data)


def generar(conn, data: dict) -> dict:
    return cuota_model.generar(conn, data)


def control_generacion(conn, periodo: str) -> dict:
    return cuota_model.control_generacion(conn, periodo)


def listar_faltantes_generacion(conn, query: dict) -> dict:
    return cuota_model.listar_faltantes_generacion(conn, query)


def pago_adelantado(conn, data: dict) -> dict:
    return cuota_model.pago_adelantado(conn, data)


def actualizar(conn, cuota_id: int, data: dict) -> None:
    cuota_model.actualizar(conn, cuota_id, data)


def eliminar(conn, cuota_id: int) -> None:
    cuota_model.eliminar(conn, cuota_id)


def pagar(conn, cuota_id: int, fecha_pago: str | None = None, medio_pago: str = "efectivo") -> None:
    cuota_model.marcar_pagada(conn, cuota_id, fecha_pago, medio_pago)


def despagar(conn, cuota_id: int) -> None:
    cuota_model.marcar_pendiente(conn, cuota_id)
