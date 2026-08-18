from app.models import caja_model
from app.services import security_service


def require_admin_if_closed(conn, fecha: str | None, admin_key: str, action: str, detail_prefix: str = "Caja") -> None:
    actual = caja_model.obtener(conn, fecha)["dia"]
    if actual and int(actual["cerrado"] or 0) == 1:
        security_service.require_admin_key(conn, admin_key, action, f"{detail_prefix} {actual['fecha']}")


def obtener(conn, fecha: str | None = None) -> dict:
    return caja_model.obtener(conn, fecha)


def listado_diario(conn, desde: str | None = None, hasta: str | None = None) -> dict:
    return caja_model.listado_diario(conn, desde, hasta)


def actualizar_dia(conn, data: dict, admin_key: str = "") -> None:
    require_admin_if_closed(conn, data.get("fecha"), admin_key, "caja.dia.editar_cerrada")
    caja_model.actualizar_dia(conn, data)


def crear_movimiento(conn, data: dict, admin_key: str = "") -> int:
    require_admin_if_closed(conn, data.get("fecha"), admin_key, "caja.movimiento.crear_cerrada")
    return caja_model.crear_movimiento(conn, data)


def actualizar_movimiento(conn, movimiento_id: int, data: dict, admin_key: str = "") -> None:
    security_service.require_admin_key(conn, admin_key, "caja.movimiento.editar", f"Movimiento {movimiento_id}")
    caja_model.actualizar_movimiento(conn, movimiento_id, data)


def eliminar_movimiento(conn, movimiento_id: int, admin_key: str = "") -> None:
    security_service.require_admin_key(conn, admin_key, "caja.movimiento.eliminar", f"Movimiento {movimiento_id}")
    caja_model.eliminar_movimiento(conn, movimiento_id)
