from app.models import cuota_model
from app.models.helpers import today_iso
from app.services import caja_service, security_service


def crear(conn, data: dict) -> int:
    return cuota_model.crear(conn, data)


def listar(conn, query: dict) -> list[dict]:
    return cuota_model.listar(conn, query)


def generar(conn, data: dict, admin_key: str = "") -> dict:
    if data.get("forzar"):
        periodo = data.get("periodo", "")
        security_service.require_admin_key(conn, admin_key, "cuota.generar_forzado", f"Periodo {periodo}")
    return cuota_model.generar(conn, data)


def control_generacion(conn, periodo: str) -> dict:
    return cuota_model.control_generacion(conn, periodo)


def listar_faltantes_generacion(conn, query: dict) -> dict:
    return cuota_model.listar_faltantes_generacion(conn, query)


def pago_adelantado(conn, data: dict, admin_key: str = "") -> dict:
    fecha_pago = data.get("fecha_pago") or today_iso()
    caja_service.require_admin_if_closed(conn, fecha_pago, admin_key, "cuota.adelanto_caja_cerrada")
    return cuota_model.pago_adelantado(conn, data)


def actualizar(conn, cuota_id: int, data: dict, admin_key: str = "") -> None:
    security_service.require_admin_key(conn, admin_key, "cuota.editar", f"Cuota {cuota_id}")
    cuota_model.actualizar(conn, cuota_id, data)


def eliminar(conn, cuota_id: int, admin_key: str = "") -> None:
    security_service.require_admin_key(conn, admin_key, "cuota.eliminar", f"Cuota {cuota_id}")
    cuota_model.eliminar(conn, cuota_id)


def pagar(conn, cuota_id: int, fecha_pago: str | None = None, medio_pago: str = "efectivo", admin_key: str = "") -> None:
    caja_service.require_admin_if_closed(
        conn,
        fecha_pago or today_iso(),
        admin_key,
        "cuota.pagar_caja_cerrada",
        f"Cuota {cuota_id}",
    )
    cuota_model.marcar_pagada(conn, cuota_id, fecha_pago, medio_pago)


def pagar_varias(conn, data: dict, admin_key: str = "") -> dict:
    fecha_pago = data.get("fecha_pago") or today_iso()
    caja_service.require_admin_if_closed(conn, fecha_pago, admin_key, "cuota.pagar_caja_cerrada")
    return cuota_model.marcar_pagadas(conn, data)


def despagar(conn, cuota_id: int, admin_key: str = "") -> None:
    security_service.require_admin_key(conn, admin_key, "cuota.despagar", f"Cuota {cuota_id}")
    cuota_model.marcar_pendiente(conn, cuota_id)
