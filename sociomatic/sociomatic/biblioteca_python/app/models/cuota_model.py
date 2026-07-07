from app.models import caja_model, config_model, socio_model
from app.models.helpers import add_months, next_period, now_iso, today_iso, valid_date, valid_period
from app.settings import COBRADORES


def generar(conn, data: dict) -> dict:
    periodo = data.get("periodo") or next_period()
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    control = control_generacion(conn, periodo)
    if not control["puede_generar"]:
        raise ValueError(control["motivo"])
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
    return {"periodo": periodo, "cuotas_creadas": creadas, "control": control}


def control_generacion(conn, periodo: str) -> dict:
    if not valid_period(periodo):
        raise ValueError("Periodo invalido. Use AAAA-MM.")
    periodo_anterior = add_months(periodo, -1)
    total_cuotas = conn.execute("SELECT COUNT(*) AS total FROM cuotas").fetchone()["total"]
    cuotas_periodo = conn.execute(
        "SELECT COUNT(*) AS total FROM cuotas WHERE periodo = ?",
        (periodo,),
    ).fetchone()["total"]
    cuotas_anterior = conn.execute(
        "SELECT COUNT(*) AS total FROM cuotas WHERE periodo = ?",
        (periodo_anterior,),
    ).fetchone()["total"]
    socios_objetivo = _contar_socios_objetivo(conn, periodo)
    socios_anterior_objetivo = _contar_socios_objetivo(conn, periodo_anterior)
    faltantes_estimadas = max(int(socios_objetivo or 0) - int(cuotas_periodo or 0), 0)
    puede_generar = True
    motivo = ""
    if total_cuotas and cuotas_anterior < socios_anterior_objetivo:
        puede_generar = False
        motivo = (
            f"No se puede generar {periodo}. El periodo anterior ({periodo_anterior}) no esta completo: "
            f"tiene {cuotas_anterior} de {socios_anterior_objetivo} cuota(s) esperada(s)."
        )
    elif socios_objetivo == 0:
        puede_generar = False
        motivo = "No hay socios activos para generar cuotas."
    elif faltantes_estimadas == 0:
        puede_generar = False
        motivo = f"Las cuotas de {periodo} ya estan generadas para los socios alcanzados."
    return {
        "periodo": periodo,
        "periodo_anterior": periodo_anterior,
        "puede_generar": puede_generar,
        "motivo": motivo,
        "socios_objetivo": int(socios_objetivo or 0),
        "socios_anterior_objetivo": int(socios_anterior_objetivo or 0),
        "cuotas_periodo": int(cuotas_periodo or 0),
        "cuotas_anterior": int(cuotas_anterior or 0),
        "faltantes_estimadas": faltantes_estimadas,
        "primera_generacion": int(total_cuotas or 0) == 0,
    }


def _contar_socios_objetivo(conn, periodo: str) -> int:
    return int(
        conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM socios
            WHERE fecha_baja IS NULL
              AND cobrador IN (1, 3)
              AND fecha_alta <= ?
            """,
            (f"{periodo}-31",),
        ).fetchone()["total"]
        or 0
    )


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
        cuota["cobrador_texto"] = config_model.cobrador_nombre(conn, row["cobrador"])
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
    if estado == "pagada":
        caja_model.registrar_cobro_cuota(conn, cuota_id)
    else:
        caja_model.eliminar_cobro_cuota(conn, cuota_id)


def eliminar(conn, cuota_id: int) -> None:
    caja_model.eliminar_cobro_cuota(conn, cuota_id)
    cursor = conn.execute("DELETE FROM cuotas WHERE id = ?", (cuota_id,))
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")


def marcar_pagada(conn, cuota_id: int) -> None:
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pagada', fecha_pago = ?, actualizado_en = ? WHERE id = ?",
        (today_iso(), now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")
    caja_model.registrar_cobro_cuota(conn, cuota_id)


def pago_adelantado(conn, data: dict) -> dict:
    socio_id = int(data.get("socio_id"))
    desde_periodo = data.get("desde_periodo")
    cantidad = int(data.get("cantidad") or 0)
    medio_pago = str(data.get("medio_pago", "efectivo")).strip()
    fecha_pago = str(data.get("fecha_pago", "")).strip() or today_iso()
    if not valid_period(desde_periodo):
        raise ValueError("Periodo inicial invalido. Use AAAA-MM.")
    if cantidad < 1 or cantidad > 60:
        raise ValueError("La cantidad de meses debe estar entre 1 y 60.")
    if not valid_date(fecha_pago):
        raise ValueError("Fecha de pago invalida.")
    socio = socio_model.obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise ValueError("Socio activo no encontrado.")
    creadas = 0
    pagadas = 0
    ids = []
    timestamp = now_iso()
    for offset in range(cantidad):
        periodo = add_months(desde_periodo, offset)
        monto = config_model.cuota_monto(conn, socio["estado"])
        row = conn.execute(
            "SELECT id FROM cuotas WHERE socio_id = ? AND periodo = ?",
            (socio_id, periodo),
        ).fetchone()
        if row:
            cuota_id = row["id"]
            conn.execute(
                """
                UPDATE cuotas
                SET monto = ?, estado = 'pagada', fecha_pago = ?, observacion = ?, actualizado_en = ?
                WHERE id = ?
                """,
                (monto, fecha_pago, "Pago adelantado", timestamp, cuota_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, fecha_pago, observacion, creado_en, actualizado_en)
                VALUES (?, ?, ?, 'pagada', ?, 'Pago adelantado', ?, ?)
                """,
                (socio_id, periodo, monto, fecha_pago, timestamp, timestamp),
            )
            cuota_id = cursor.lastrowid
            creadas += 1
        caja_model.registrar_cobro_cuota(conn, cuota_id, medio_pago)
        ids.append(cuota_id)
        pagadas += 1
    return {"cuotas_creadas": creadas, "cuotas_pagadas": pagadas, "ids": ids}


def marcar_pendiente(conn, cuota_id: int) -> None:
    cursor = conn.execute(
        "UPDATE cuotas SET estado = 'pendiente', fecha_pago = NULL, actualizado_en = ? WHERE id = ?",
        (now_iso(), cuota_id),
    )
    if cursor.rowcount == 0:
        raise LookupError("Cuota no encontrada")
    caja_model.eliminar_cobro_cuota(conn, cuota_id)


def cuotas_para_imprimir(conn, periodo: str, cobrador: int):
    order = "s.direccion COLLATE NOCASE, s.apellido COLLATE NOCASE" if cobrador == 1 else "s.nro_socio"
    limite_moroso = int(config_model.get_config(conn).get("moroso_cuotas_limite", "4"))
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
          AND (
            SELECT COUNT(*)
            FROM cuotas cx
            WHERE cx.socio_id = s.id
              AND cx.estado = 'pendiente'
          ) <= ?
        ORDER BY {order}
        """,
        (periodo, cobrador, limite_moroso),
    ).fetchall()
