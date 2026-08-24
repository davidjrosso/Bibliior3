from app.models.helpers import current_period, now_iso, row_to_dict, today_iso, valid_date
from app.models import config_model
from app.repositories import socio_repository


def validate_socio(data: dict, editing: bool = False) -> dict:
    required = ["nro_socio", "dni", "apellido", "nombre", "direccion", "estado", "cobrador"]
    if not editing:
        required.extend(["barrio", "localidad"])
    for field in required:
        if data.get(field) in (None, ""):
            raise ValueError(f"El campo {field} es obligatorio.")

    try:
        nro_socio = int(data.get("nro_socio"))
    except (TypeError, ValueError):
        raise ValueError("El nro. de socio debe ser numerico.")
    if nro_socio < 1:
        raise ValueError("El nro. de socio debe ser mayor a cero.")

    clean = {
        "nro_socio": nro_socio,
        "dni": str(data.get("dni", "")).strip(),
        "apellido": str(data.get("apellido", "")).strip(),
        "nombre": str(data.get("nombre", "")).strip(),
        "telefono": str(data.get("telefono", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "direccion": str(data.get("direccion", "")).strip(),
        "barrio": str(data.get("barrio", "")).strip(),
        "localidad": str(data.get("localidad", "")).strip(),
        "fecha_nacimiento": str(data.get("fecha_nacimiento", "")).strip() or None,
        "fecha_alta": str(data.get("fecha_alta", "")).strip() or today_iso(),
        "ocupacion": str(data.get("ocupacion", "")).strip(),
        "estado": str(data.get("estado", "activo")).strip(),
        "cobrador": int(data.get("cobrador", 1)),
    }
    if not valid_date(clean["fecha_alta"]):
        raise ValueError("Fecha de ingreso invalida.")
    if clean["estado"] == "":
        raise ValueError("Estado invalido.")
    if clean["cobrador"] < 1:
        raise ValueError("Cobrador invalido.")
    return clean


def proximo_nro_socio(conn) -> int:
    usados = socio_repository.active_member_numbers(conn)
    nro = 1
    while nro in usados:
        nro += 1
    return nro


def socio_con_resumen(conn, socio_id: int) -> dict | None:
    socio = row_to_dict(socio_repository.find_by_id(conn, socio_id))
    if not socio:
        return None
    resumen = socio_repository.cuota_summary(conn, socio_id, current_period())
    socio["cuotas_debe"] = int(resumen["cuotas_debe"] or 0)
    socio["cuotas_adelantadas"] = int(resumen["cuotas_adelantadas"] or 0)
    socio["cobrador_texto"] = config_model.cobrador_nombre(conn, socio["cobrador"])
    return socio


def listar(conn, busqueda: str = "", incluir_bajas: bool = False, buscar_todos: bool = False) -> list[dict]:
    ids = socio_repository.list_ids(conn, busqueda, incluir_bajas, buscar_todos)
    return [socio for socio_id in ids if (socio := socio_con_resumen(conn, socio_id))]


def obtener(conn, socio_id: int) -> dict | None:
    return socio_con_resumen(conn, socio_id)


def obtener_cuotas(conn, socio_id: int) -> list[dict]:
    return [dict(row) for row in socio_repository.list_cuotas(conn, socio_id)]


def crear(conn, data: dict) -> dict:
    clean = validate_socio(data)
    timestamp = now_iso()
    socio_id = socio_repository.insert(conn, clean, timestamp)
    return {"id": socio_id, "nro_socio": clean["nro_socio"]}


def actualizar(conn, socio_id: int, data: dict) -> None:
    socio = obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise LookupError("Socio activo no encontrado")
    clean = validate_socio(data, editing=True)
    socio_repository.update(conn, socio_id, clean, now_iso())


def listar_morosos(conn) -> list[dict]:
    limite = int(config_model.get_config(conn).get("moroso_cuotas_limite", "4"))
    rows = socio_repository.list_morosos(conn, limite)
    morosos = []
    for row in rows:
        item = dict(row)
        item["cobrador_texto"] = config_model.cobrador_nombre(conn, item["cobrador"])
        morosos.append(item)
    return morosos


def baja(conn, socio_id: int) -> int:
    socio = obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise LookupError("Socio activo no encontrado")
    socio_repository.mark_deleted(conn, socio_id, today_iso(), now_iso())
    socio_repository.delete_caja_movimientos_for_socio(conn, socio_id)
    socio_repository.delete_cuotas(conn, socio_id)
    return socio["nro_socio"]
