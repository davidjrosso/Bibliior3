from app.settings import COBRADORES
from app.models.helpers import now_iso, parse_decimal
from app.repositories import config_repository


CONFIG_DEFAULTS = {
    "socio_estado_default": "activo",
    "socio_cobrador_default": "1",
    "impresion_cobrador_default": "1",
    "periodo_default": "siguiente",
    "moroso_cuotas_limite": "4",
}


def get_config(conn) -> dict:
    rows = config_repository.list_config(conn)
    config = CONFIG_DEFAULTS.copy()
    hidden = {
        "admin_key_hash",
        "admin_key_salt",
        "catalogos_migrados_desde_config",
        "login_password_hash",
        "login_password_salt",
        "session_secret",
    }
    config.update({row["clave"]: row["valor"] for row in rows if row["clave"] not in hidden})
    tipos = listar_tipos_socio(conn)
    cobradores = listar_cobradores(conn)
    activo = next((tipo for tipo in tipos if tipo["id"] == "activo"), None)
    jubilado = next((tipo for tipo in tipos if tipo["id"] == "jubilado"), None)
    config["monto_activo"] = str(activo["monto"] if activo else config.get("monto_activo", "0"))
    config["monto_jubilado"] = str(jubilado["monto"] if jubilado else config.get("monto_jubilado", "0"))
    for cobrador in cobradores:
        config[f"cobrador_{cobrador['id']}"] = cobrador["nombre"]
    config["tipos_socio"] = tipos
    config["cobradores"] = cobradores
    return config


def get_cobradores(conn) -> dict[int, str]:
    return {row["id"]: row["nombre"] for row in listar_cobradores(conn, solo_activos=False)}


def cobrador_nombre(conn, number: int) -> str:
    return get_cobradores(conn).get(number, COBRADORES.get(number, ""))


def update_config(conn, data: dict) -> None:
    values = {}
    if "monto_activo" in data:
        actualizar_tipo_socio(conn, "activo", {"nombre": "Activo", "monto": data.get("monto_activo"), "activo": 1})
    if "monto_jubilado" in data:
        actualizar_tipo_socio(conn, "jubilado", {"nombre": "Jubilado", "monto": data.get("monto_jubilado"), "activo": 1})

    estado_default = str(data.get("socio_estado_default", "activo")).strip()
    tipos_activos = {row["id"] for row in listar_tipos_socio(conn, solo_activos=True)}
    if estado_default not in tipos_activos:
        raise ValueError("Estado predeterminado invalido.")
    values["socio_estado_default"] = estado_default

    cobradores_activos = {row["id"] for row in listar_cobradores(conn, solo_activos=True)}
    for key in ("socio_cobrador_default", "impresion_cobrador_default"):
        value = int(data.get(key, 1))
        if value not in cobradores_activos:
            raise ValueError("Cobrador predeterminado invalido.")
        values[key] = str(value)

    periodo_default = str(data.get("periodo_default", "siguiente")).strip()
    if periodo_default not in {"actual", "siguiente"}:
        raise ValueError("Periodo predeterminado invalido.")
    values["periodo_default"] = periodo_default

    moroso_cuotas_limite = int(data.get("moroso_cuotas_limite", 4))
    if moroso_cuotas_limite < 1:
        raise ValueError("El limite de cuotas para moroso debe ser mayor a cero.")
    values["moroso_cuotas_limite"] = str(moroso_cuotas_limite)

    for key, value in values.items():
        config_repository.upsert_config_value(conn, key, value)


def cuota_monto(conn, estado: str) -> float:
    row = config_repository.cuota_monto(conn, estado)
    if row:
        return float(row["monto"] or 0)
    return 0.0


def listar_tipos_socio(conn, solo_activos: bool = False) -> list[dict]:
    return [dict(row) for row in config_repository.list_tipos_socio(conn, solo_activos)]


def listar_cobradores(conn, solo_activos: bool = False) -> list[dict]:
    return [dict(row) for row in config_repository.list_cobradores(conn, solo_activos)]


def _slug(value: str) -> str:
    text = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    text = "_".join(part for part in text.split("_") if part)
    if not text:
        raise ValueError("El nombre es obligatorio.")
    return text[:40]


def crear_tipo_socio(conn, data: dict) -> dict:
    nombre = str(data.get("nombre", "")).strip()
    monto = parse_decimal(data.get("monto", 0))
    if not nombre:
        raise ValueError("El nombre del tipo de socio es obligatorio.")
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")
    tipo_id = _slug(str(data.get("id") or nombre))
    config_repository.insert_tipo_socio(conn, tipo_id, nombre, monto, now_iso())
    return {"id": tipo_id}


def actualizar_tipo_socio(conn, tipo_id: str, data: dict) -> None:
    nombre = str(data.get("nombre", "")).strip()
    monto = parse_decimal(data.get("monto", 0))
    activo = 1 if str(data.get("activo", "1")) in {"1", "true", "on", "si"} else 0
    if not nombre:
        raise ValueError("El nombre del tipo de socio es obligatorio.")
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")
    if config_repository.update_tipo_socio(conn, tipo_id, nombre, monto, activo, now_iso()) == 0:
        raise LookupError("Tipo de socio no encontrado")


def baja_tipo_socio(conn, tipo_id: str) -> None:
    usados = config_repository.count_socios_by_tipo(conn, tipo_id)
    if usados:
        config_repository.deactivate_tipo_socio(conn, tipo_id, now_iso())
        return
    if config_repository.delete_tipo_socio(conn, tipo_id) == 0:
        raise LookupError("Tipo de socio no encontrado")


def crear_cobrador(conn, data: dict) -> dict:
    nombre = str(data.get("nombre", "")).strip()
    if not nombre:
        raise ValueError("El nombre del cobrador es obligatorio.")
    return {"id": config_repository.insert_cobrador(conn, nombre, now_iso())}


def actualizar_cobrador(conn, cobrador_id: int, data: dict) -> None:
    nombre = str(data.get("nombre", "")).strip()
    activo = 1 if str(data.get("activo", "1")) in {"1", "true", "on", "si"} else 0
    if not nombre:
        raise ValueError("El nombre del cobrador es obligatorio.")
    if config_repository.update_cobrador(conn, cobrador_id, nombre, activo, now_iso()) == 0:
        raise LookupError("Cobrador no encontrado")


def baja_cobrador(conn, cobrador_id: int) -> None:
    usados = config_repository.count_socios_by_cobrador(conn, cobrador_id)
    if usados:
        config_repository.deactivate_cobrador(conn, cobrador_id, now_iso())
        return
    if config_repository.delete_cobrador(conn, cobrador_id) == 0:
        raise LookupError("Cobrador no encontrado")
