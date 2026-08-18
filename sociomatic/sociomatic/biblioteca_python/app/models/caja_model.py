from datetime import datetime, timedelta

from app.models.helpers import now_iso, parse_decimal, today_iso
from app.repositories import caja_repository


MEDIOS_PAGO = {"efectivo", "transferencia", "tarjeta", "cheque", "otro"}
TIPOS = {"ingreso", "egreso"}


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def asegurar_dia(conn, fecha: str) -> None:
    if not valid_date(fecha):
        raise ValueError("Fecha invalida. Use AAAA-MM-DD.")
    caja_repository.ensure_day(conn, fecha, now_iso())


def obtener(conn, fecha: str | None = None) -> dict:
    fecha = fecha or today_iso()
    asegurar_dia(conn, fecha)
    dia = dict(caja_repository.find_day(conn, fecha))
    rows = caja_repository.list_cash_movements(conn, fecha)
    movimientos = [dict(row) for row in rows]
    ingresos = sum(float(row["monto"]) for row in movimientos if row["tipo"] == "ingreso")
    egresos = sum(float(row["monto"]) for row in movimientos if row["tipo"] == "egreso")
    saldo_inicial = float(dia["saldo_inicial"] or 0)
    return {
        "dia": dia,
        "movimientos": movimientos,
        "resumen": {
            "saldo_inicial": saldo_inicial,
            "ingresos": ingresos,
            "egresos": egresos,
            "saldo_final": saldo_inicial + ingresos - egresos,
            "cantidad_movimientos": len(movimientos),
        },
    }


def listado_diario(conn, desde: str | None = None, hasta: str | None = None) -> dict:
    hasta = (hasta or today_iso()).strip()
    desde = (desde or _dias_antes(hasta, 30)).strip()
    if not valid_date(desde) or not valid_date(hasta):
        raise ValueError("Fechas invalidas. Use AAAA-MM-DD.")
    if desde > hasta:
        raise ValueError("La fecha desde no puede ser mayor a hasta.")
    rows = caja_repository.list_daily_summaries(conn, desde, hasta)
    dias = []
    total_ingresos = 0.0
    total_egresos = 0.0
    for row in rows:
        ingresos = float(row["ingresos"] or 0)
        egresos = float(row["egresos"] or 0)
        saldo_inicial = float(row["saldo_inicial"] or 0)
        total_ingresos += ingresos
        total_egresos += egresos
        dias.append(
            {
                "fecha": row["fecha"],
                "saldo_inicial": saldo_inicial,
                "ingresos": ingresos,
                "egresos": egresos,
                "saldo_final": saldo_inicial + ingresos - egresos,
                "movimientos": int(row["movimientos"] or 0),
                "cerrado": int(row["cerrado"] or 0),
                "observacion": row["observacion"] or "",
            }
        )
    return {
        "dias": dias,
        "resumen": {
            "desde": desde,
            "hasta": hasta,
            "ingresos": total_ingresos,
            "egresos": total_egresos,
            "neto": total_ingresos - total_egresos,
            "dias": len(dias),
        },
    }


def _dias_antes(fecha: str, dias: int) -> str:
    return (datetime.strptime(fecha, "%Y-%m-%d") - timedelta(days=dias)).strftime("%Y-%m-%d")


def actualizar_dia(conn, data: dict) -> None:
    fecha = str(data.get("fecha") or today_iso()).strip()
    asegurar_dia(conn, fecha)
    saldo_inicial = parse_decimal(data.get("saldo_inicial") or 0)
    cerrado = 1 if str(data.get("cerrado", "0")) in {"1", "true", "on", "si"} else 0
    caja_repository.update_day(
        conn,
        fecha,
        saldo_inicial,
        str(data.get("observacion", "")).strip(),
        cerrado,
        now_iso(),
    )


def validar_movimiento(data: dict) -> dict:
    fecha = str(data.get("fecha") or today_iso()).strip()
    if not valid_date(fecha):
        raise ValueError("Fecha invalida. Use AAAA-MM-DD.")
    tipo = str(data.get("tipo", "")).strip()
    if tipo not in TIPOS:
        raise ValueError("Tipo de movimiento invalido.")
    monto = parse_decimal(data.get("monto") or 0)
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    medio_pago = str(data.get("medio_pago", "efectivo")).strip()
    if medio_pago not in MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    concepto = str(data.get("concepto", "")).strip()
    if not concepto:
        raise ValueError("El concepto es obligatorio.")
    return {
        "fecha": fecha,
        "tipo": tipo,
        "concepto": concepto,
        "descripcion": str(data.get("descripcion", "")).strip(),
        "monto": monto,
        "medio_pago": medio_pago,
        "referencia": str(data.get("referencia", "")).strip(),
    }


def crear_movimiento(conn, data: dict) -> int:
    clean = validar_movimiento(data)
    asegurar_dia(conn, clean["fecha"])
    return caja_repository.insert_movement(conn, clean, data.get("cuota_id"), now_iso())


def actualizar_movimiento(conn, movimiento_id: int, data: dict) -> None:
    clean = validar_movimiento(data)
    asegurar_dia(conn, clean["fecha"])
    if caja_repository.update_movement(conn, movimiento_id, clean, now_iso()) == 0:
        raise LookupError("Movimiento de caja no encontrado")


def eliminar_movimiento(conn, movimiento_id: int) -> None:
    if caja_repository.delete_movement(conn, movimiento_id) == 0:
        raise LookupError("Movimiento de caja no encontrado")


def registrar_cobro_cuota(conn, cuota_id: int, medio_pago: str = "efectivo") -> None:
    if medio_pago not in MEDIOS_PAGO:
        raise ValueError("Medio de pago invalido.")
    if medio_pago != "efectivo":
        eliminar_cobro_cuota(conn, cuota_id)
        return
    row = caja_repository.cuota_collection_data(conn, cuota_id)
    if not row:
        raise LookupError("Cuota no encontrada")
    fecha = row["fecha_pago"] or today_iso()
    asegurar_dia(conn, fecha)
    concepto = "Cobro de cuota"
    descripcion = f"Cuota {row['periodo']} - Socio #{row['nro_socio']} {row['apellido']}, {row['nombre']}"
    referencia = f"cuota:{row['id']}"
    timestamp = now_iso()
    existente = caja_repository.find_movement_by_cuota(conn, cuota_id)
    if existente:
        caja_repository.update_cuota_collection(
            conn,
            cuota_id,
            fecha,
            concepto,
            descripcion,
            float(row["monto"]),
            medio_pago,
            referencia,
            timestamp,
        )
        return
    caja_repository.insert_cuota_collection(
        conn,
        cuota_id,
        fecha,
        concepto,
        descripcion,
        float(row["monto"]),
        medio_pago,
        referencia,
        timestamp,
    )


def eliminar_cobro_cuota(conn, cuota_id: int) -> None:
    caja_repository.delete_cuota_collection(conn, cuota_id)
