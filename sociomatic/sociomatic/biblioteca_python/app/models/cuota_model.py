from app.models import config_model, socio_model
from app.models.helpers import next_period, now_iso, today_iso, valid_period
from app.settings import COBRADORES


def generar(conn, data: dict) -> dict:
    periodo = data.get("periodo") or next_period()
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    socios = conn.execute(
        "SELECT * FROM socios WHERE fecha_baja IS NULL AND cobrador IN (1, 3)"
    ).fetchall()
    creadas = 0
    for socio in socios:
        monto = config_model.cuota_monto(conn, socio["estado"])
        try:
            conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, creado_en, actualizado_en)
                VALUES (?, ?, ?, 'pendiente', ?, ?)
                """,
                (socio["id"], periodo, monto, now_iso(), now_iso()),
            )
            creadas += 1
        except Exception:
            continue
    return {"periodo": periodo, "cuotas_creadas": creadas}


def crear(conn, data: dict) -> int:
    socio_id = int(data.get("socio_id"))
    periodo = data.get("periodo")
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    socio = socio_model.obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise ValueError("Socio activo no encontrado.")
    monto = float(data.get("monto") or config_model.cuota_monto(conn, socio["estado"]))
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO cuotas (socio_id, periodo, monto, estado, observacion, creado_en, actualizado_en)
        VALUES (?, ?, ?, 'pendiente', ?, ?, ?)
        """,
        (socio_id, periodo, monto, str(data.get("observacion", "")), timestamp, timestamp),
    )
    return cursor.lastrowid


def listar(conn, query: dict) -> list[dict]:
    periodo = (query.get("periodo", [""])[0] or "").strip()
    estado = (query.get("estado", [""])[0] or "").strip()
    cobrador = (query.get("cobrador", [""])[0] or "").strip()
    busqueda = (query.get("q", [""])[0] or "").strip()
    where = ["s.fecha_baja IS NULL"]
    params = []
    if periodo:
        if not valid_period(periodo):
            raise ValueError("Periodo invalido. Use AAAA-MM.")
        where.append("c.periodo = ?")
        params.append(periodo)
    if estado in {"pendiente", "pagada"}:
        where.append("c.estado = ?")
        params.append(estado)
    if cobrador:
        where.append("s.cobrador = ?")
        params.append(int(cobrador))
    if busqueda:
        where.append(
            "(CAST(s.nro_socio AS TEXT) = ? OR s.apellido LIKE ? OR s.nombre LIKE ? OR s.dni LIKE ? OR s.direccion LIKE ?)"
        )
        like = f"%{busqueda}%"
        params.extend([busqueda, like, like, like, like])
    rows = conn.execute(
        f"""
        SELECT c.*, s.nro_socio, s.apellido, s.nombre, s.dni, s.direccion,
               s.localidad, s.cobrador, s.estado AS estado_socio
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE {' AND '.join(where)}
        ORDER BY c.periodo DESC, c.estado, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()
    cuotas = []
    for row in rows:
        cuota = dict(row)
        cuota["socio"] = f"{row['apellido']}, {row['nombre']}"
        cuota["cobrador_texto"] = COBRADORES.get(row["cobrador"], "")
        cuotas.append(cuota)
    return cuotas


def actualizar(conn, cuota_id: int, data: dict) -> None:
    periodo = data.get("periodo")
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    monto = float(data.get("monto"))
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")
    estado = data.get("estado", "pendiente")
    if estado not in {"pendiente", "pagada"}:
        raise ValueError("Estado de cuota invalido.")
    fecha_pago = data.get("fecha_pago") or None
    if estado == "pendiente":
        fecha_pago = None
    elif not fecha_pago:
        fecha_pago = today_iso()
    cursor = conn.execute(
        """
        UPDATE cuotas
        SET periodo = ?, monto = ?, estado = ?, fecha_pago = ?, observacion = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (periodo, monto, estado, fecha_pago, str(data.get("observacion", "")), now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")


def eliminar(conn, cuota_id: int) -> None:
    cursor = conn.execute("DELETE FROM cuotas WHERE id = ?", (cuota_id,))
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")


def marcar_pagada(conn, cuota_id: int) -> None:
    conn.execute(
        "UPDATE cuotas SET estado = 'pagada', fecha_pago = ?, actualizado_en = ? WHERE id = ?",
        (today_iso(), now_iso(), cuota_id),
    )


def marcar_pendiente(conn, cuota_id: int) -> None:
    conn.execute(
        "UPDATE cuotas SET estado = 'pendiente', fecha_pago = NULL, actualizado_en = ? WHERE id = ?",
        (now_iso(), cuota_id),
    )


def cuotas_para_imprimir(conn, periodo: str, cobrador: int):
    order = "s.direccion COLLATE NOCASE, s.apellido COLLATE NOCASE" if cobrador == 1 else "s.nro_socio"
    return conn.execute(
        f"""
        SELECT c.*, s.nro_socio, s.apellido, s.nombre, s.direccion, s.barrio,
               s.localidad, s.dni, s.cobrador
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE c.periodo = ?
          AND s.fecha_baja IS NULL
          AND s.cobrador = ?
          AND c.estado = 'pendiente'
        ORDER BY {order}
        """,
        (periodo, cobrador),
    ).fetchall()
