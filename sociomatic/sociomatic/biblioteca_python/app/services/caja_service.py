from app.models import caja_model


def obtener(conn, fecha: str | None = None) -> dict:
    return caja_model.obtener(conn, fecha)


def listado_diario(conn, desde: str | None = None, hasta: str | None = None) -> dict:
    return caja_model.listado_diario(conn, desde, hasta)


def actualizar_dia(conn, data: dict) -> None:
    caja_model.actualizar_dia(conn, data)


def crear_movimiento(conn, data: dict) -> int:
    return caja_model.crear_movimiento(conn, data)


def actualizar_movimiento(conn, movimiento_id: int, data: dict) -> None:
    caja_model.actualizar_movimiento(conn, movimiento_id, data)


def eliminar_movimiento(conn, movimiento_id: int) -> None:
    caja_model.eliminar_movimiento(conn, movimiento_id)
