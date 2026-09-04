from app.models.helpers import valid_date, valid_period
from app.repositories import reporte_repository


LISTADOS = {"socios", "deuda", "pagadas", "caja_movimientos"}
MAX_LIMIT = 5000


def generar_listado(conn, query: dict) -> dict:
    tipo = _param(query, "tipo", "socios")
    if tipo not in LISTADOS:
        raise ValueError("Tipo de listado invalido.")
    limite = _limit(query)
    if tipo == "socios":
        return _socios(conn, query, limite)
    if tipo == "deuda":
        return _cuotas(conn, query, limite, "pendiente")
    if tipo == "pagadas":
        return _cuotas(conn, query, limite, "pagada")
    return _caja_movimientos(conn, query, limite)


def _socios(conn, query: dict, limite: int) -> dict:
    where = []
    params: list[object] = []
    estado = _param(query, "estado_socio", "activos")
    tipo_socio = _param(query, "tipo_socio")
    cobrador = _param(query, "cobrador")

    if estado == "activos":
        where.append("s.fecha_baja IS NULL")
    elif estado == "bajas":
        where.append("s.fecha_baja IS NOT NULL")
    elif estado == "morosos":
        where.append("s.fecha_baja IS NULL")
    elif estado != "todos":
        raise ValueError("Estado de socio invalido.")

    if tipo_socio:
        where.append("s.estado = ?")
        params.append(tipo_socio)
    if cobrador:
        where.append("s.cobrador = ?")
        params.append(int(cobrador))
    _add_socio_search(where, params, query, "s")

    where_sql = " AND ".join(where) if where else "1=1"
    if estado == "morosos":
        where_sql = f"{where_sql} AND (SELECT COUNT(*) FROM cuotas c2 WHERE c2.socio_id = s.id AND c2.estado = 'pendiente') > ?"
        params.append(_moroso_limite(conn))

    rows = reporte_repository.list_socios(conn, where_sql, params, limite)
    count = reporte_repository.count_socios(conn, where_sql, params)
    totals = reporte_repository.totals_socios(conn, where_sql, params)
    return {
        "tipo": "socios",
        "filas": [_socio_row(row) for row in rows],
        "resumen": {
            "cantidad": int(count["cantidad"] or 0),
            "mostrados": len(rows),
            "cuotas_impagas": int(totals["cuotas_impagas"] or 0),
            "deuda": float(totals["deuda"] or 0),
            "limite": limite,
        },
    }


def _cuotas(conn, query: dict, limite: int, estado: str) -> dict:
    where = ["s.fecha_baja IS NULL", "c.estado = ?"]
    params: list[object] = [estado]
    cobrador = _param(query, "cobrador")
    desde_periodo = _param(query, "desde_periodo")
    hasta_periodo = _param(query, "hasta_periodo")
    fecha_desde = _param(query, "fecha_desde")
    fecha_hasta = _param(query, "fecha_hasta")

    if cobrador:
        where.append("s.cobrador = ?")
        params.append(int(cobrador))
    if desde_periodo:
        _require_period(desde_periodo)
        where.append("c.periodo >= ?")
        params.append(desde_periodo)
    if hasta_periodo:
        _require_period(hasta_periodo)
        where.append("c.periodo <= ?")
        params.append(hasta_periodo)
    if estado == "pagada":
        if fecha_desde:
            _require_date(fecha_desde)
            where.append("c.fecha_pago >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            _require_date(fecha_hasta)
            where.append("c.fecha_pago <= ?")
            params.append(fecha_hasta)
    _add_socio_search(where, params, query, "s")

    where_sql = " AND ".join(where)
    rows = reporte_repository.list_cuotas(conn, where_sql, params, limite)
    totals = reporte_repository.totals_cuotas(conn, where_sql, params)
    return {
        "tipo": "deuda" if estado == "pendiente" else "pagadas",
        "filas": [_cuota_row(row) for row in rows],
        "resumen": {
            "cantidad": int(totals["cantidad"] or 0),
            "mostrados": len(rows),
            "monto": float(totals["monto"] or 0),
            "limite": limite,
        },
    }


def _caja_movimientos(conn, query: dict, limite: int) -> dict:
    where = ["m.medio_pago = 'efectivo'"]
    params: list[object] = []
    fecha_desde = _param(query, "fecha_desde")
    fecha_hasta = _param(query, "fecha_hasta")
    tipo_movimiento = _param(query, "tipo_movimiento")

    if fecha_desde:
        _require_date(fecha_desde)
        where.append("m.fecha >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        _require_date(fecha_hasta)
        where.append("m.fecha <= ?")
        params.append(fecha_hasta)
    if tipo_movimiento:
        if tipo_movimiento not in {"ingreso", "egreso"}:
            raise ValueError("Tipo de movimiento invalido.")
        where.append("m.tipo = ?")
        params.append(tipo_movimiento)
    _add_socio_search(where, params, query, "s")

    where_sql = " AND ".join(where)
    rows = reporte_repository.list_caja_movimientos(conn, where_sql, params, limite)
    totals = reporte_repository.totals_caja_movimientos(conn, where_sql, params)
    ingresos = float(totals["ingresos"] or 0)
    egresos = float(totals["egresos"] or 0)
    return {
        "tipo": "caja_movimientos",
        "filas": [_caja_row(row) for row in rows],
        "resumen": {
            "cantidad": int(totals["cantidad"] or 0),
            "mostrados": len(rows),
            "ingresos": ingresos,
            "egresos": egresos,
            "neto": ingresos - egresos,
            "limite": limite,
        },
    }


def _socio_row(row) -> dict:
    return {
        **dict(row),
        "socio": f"{row['apellido']}, {row['nombre']}",
        "cuotas_impagas": int(row["cuotas_impagas"] or 0),
        "cuotas_pagas": int(row["cuotas_pagas"] or 0),
        "deuda": float(row["deuda"] or 0),
    }


def _cuota_row(row) -> dict:
    item = dict(row)
    item["socio"] = f"{row['apellido']}, {row['nombre']}"
    item["monto"] = float(row["monto"] or 0)
    item["medio_pago"] = row["medio_pago"] or ""
    return item


def _caja_row(row) -> dict:
    item = dict(row)
    item["monto"] = float(row["monto"] or 0)
    item["socio"] = f"{row['apellido']}, {row['nombre']}" if row["apellido"] else ""
    return item


def _add_socio_search(where: list[str], params: list[object], query: dict, alias: str) -> None:
    busqueda = _param(query, "q")
    if not busqueda:
        return
    if _param(query, "modo_busqueda", "nro") == "todos":
        where.append(
            "("
            f"CAST({alias}.nro_socio AS TEXT) = ? OR {alias}.apellido LIKE ? OR {alias}.nombre LIKE ? "
            f"OR {alias}.dni LIKE ? OR {alias}.telefono LIKE ? OR {alias}.email LIKE ? "
            f"OR {alias}.direccion LIKE ? OR {alias}.barrio LIKE ? OR {alias}.localidad LIKE ?"
            ")"
        )
        like = f"%{busqueda}%"
        params.extend([busqueda, like, like, like, like, like, like, like, like])
        return
    where.append(f"{alias}.nro_socio = ?")
    params.append(int(busqueda) if busqueda.isdigit() else -1)


def _moroso_limite(conn) -> int:
    row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'moroso_cuotas_limite'").fetchone()
    try:
        return int(row["valor"]) if row else 4
    except ValueError:
        return 4


def _limit(query: dict) -> int:
    try:
        value = int(_param(query, "limite", "500"))
    except ValueError:
        value = 500
    return max(1, min(value, MAX_LIMIT))


def _param(query: dict, key: str, default: str = "") -> str:
    return (query.get(key, [default])[0] or default).strip()


def _require_period(value: str) -> None:
    if not valid_period(value):
        raise ValueError("Periodo invalido. Use AAAA-MM.")


def _require_date(value: str) -> None:
    if not valid_date(value):
        raise ValueError("Fecha invalida. Use AAAA-MM-DD.")
