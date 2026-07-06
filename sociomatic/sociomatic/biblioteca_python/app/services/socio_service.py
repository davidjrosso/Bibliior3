from app.models import socio_model


def crear(conn, data: dict) -> dict:
    return socio_model.crear(conn, data)


def actualizar(conn, socio_id: int, data: dict) -> None:
    socio_model.actualizar(conn, socio_id, data)


def baja(conn, socio_id: int) -> int:
    return socio_model.baja(conn, socio_id)


def listar_morosos(conn) -> list[dict]:
    return socio_model.listar_morosos(conn)
