from app.models import config_model
from app.services import security_service


def get(conn) -> dict:
    return {
        "config": config_model.get_config(conn),
        "auditoria": security_service.listar_auditoria(conn),
    }


def update(conn, data: dict, admin_key: str) -> None:
    security_service.require_admin_key(conn, admin_key, "config.predeterminados", "Cambio de configuracion general")
    config_model.update_config(conn, data)


def update_security(conn, data: dict) -> None:
    security_service.set_admin_key(conn, data.get("clave_actual", ""), data.get("clave_nueva", ""))


def create_tipo_socio(conn, data: dict, admin_key: str) -> dict:
    security_service.require_admin_key(conn, admin_key, "config.tipo_socio.crear", "Alta de tipo de socio")
    return config_model.crear_tipo_socio(conn, data)


def update_tipo_socio(conn, tipo_id: str, data: dict, admin_key: str) -> None:
    security_service.require_admin_key(conn, admin_key, "config.tipo_socio.editar", f"Tipo {tipo_id}")
    config_model.actualizar_tipo_socio(conn, tipo_id, data)


def delete_tipo_socio(conn, tipo_id: str, admin_key: str) -> None:
    security_service.require_admin_key(conn, admin_key, "config.tipo_socio.baja", f"Tipo {tipo_id}")
    config_model.baja_tipo_socio(conn, tipo_id)


def create_cobrador(conn, data: dict, admin_key: str) -> dict:
    security_service.require_admin_key(conn, admin_key, "config.cobrador.crear", "Alta de cobrador")
    return config_model.crear_cobrador(conn, data)


def update_cobrador(conn, cobrador_id: int, data: dict, admin_key: str) -> None:
    security_service.require_admin_key(conn, admin_key, "config.cobrador.editar", f"Cobrador {cobrador_id}")
    config_model.actualizar_cobrador(conn, cobrador_id, data)


def delete_cobrador(conn, cobrador_id: int, admin_key: str) -> None:
    security_service.require_admin_key(conn, admin_key, "config.cobrador.baja", f"Cobrador {cobrador_id}")
    config_model.baja_cobrador(conn, cobrador_id)
