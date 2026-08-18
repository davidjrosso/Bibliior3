from app.models import config_model, socio_model
from app.services import security_service


def listar(conn, busqueda: str = "", incluir_bajas: bool = False) -> list[dict]:
    return socio_model.listar(conn, busqueda, incluir_bajas)


def proximo_nro_socio(conn) -> int:
    return socio_model.proximo_nro_socio(conn)


def index_data(conn, busqueda: str = "", incluir_bajas: bool = False) -> dict:
    return {
        "socios": listar(conn, busqueda, incluir_bajas),
        "proximo_nro_socio": proximo_nro_socio(conn),
        "cobradores": config_model.listar_cobradores(conn),
        "tipos_socio": config_model.listar_tipos_socio(conn),
    }


def obtener(conn, socio_id: int) -> dict | None:
    return socio_model.obtener(conn, socio_id)


def detalle(conn, socio_id: int) -> dict | None:
    socio = obtener(conn, socio_id)
    if not socio:
        return None
    return {"socio": socio, "cuotas": socio_model.obtener_cuotas(conn, socio_id)}


def crear(conn, data: dict) -> dict:
    return socio_model.crear(conn, data)


def actualizar(conn, socio_id: int, data: dict) -> None:
    socio_model.actualizar(conn, socio_id, data)


def baja(conn, socio_id: int, admin_key: str = "") -> int:
    security_service.require_admin_key(conn, admin_key, "socio.baja", f"Socio {socio_id}")
    return socio_model.baja(conn, socio_id)


def listar_morosos(conn) -> list[dict]:
    return socio_model.listar_morosos(conn)
