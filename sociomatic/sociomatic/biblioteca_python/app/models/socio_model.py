from app.models.helpers import current_period, now_iso, row_to_dict, today_iso, valid_date
from app.models import config_model


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
    usados = {
        row["nro_socio"]
        for row in conn.execute("SELECT nro_socio FROM socios WHERE fecha_baja IS NULL")
    }
    nro = 1
    while nro in usados:
        nro += 1
    return nro


def socio_con_resumen(conn, socio_id: int) -> dict | None:
    socio = row_to_dict(conn.execute("SELECT * FROM socios WHERE id = ?", (socio_id,)).fetchone())
    if not socio:
        return None
    resumen = conn.execute(
        """
        SELECT
            SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) AS cuotas_debe,
            SUM(CASE WHEN estado = 'pagada' AND periodo > ? THEN 1 ELSE 0 END) AS cuotas_adelantadas
        FROM cuotas
        WHERE socio_id = ?
        """,
        (current_period(), socio_id),
    ).fetchone()
    socio["cuotas_debe"] = int(resumen["cuotas_debe"] or 0)
    socio["cuotas_adelantadas"] = int(resumen["cuotas_adelantadas"] or 0)
    socio["cobrador_texto"] = config_model.cobrador_nombre(conn, socio["cobrador"])
    return socio


def listar(conn, busqueda: str = "", incluir_bajas: bool = False) -> list[dict]:
    where = ["1=1"]
    params = []
    if not incluir_bajas:
        where.append("fecha_baja IS NULL")
    if busqueda:
        where.append("(CAST(nro_socio AS TEXT) = ? OR apellido LIKE ? OR nombre LIKE ? OR dni LIKE ? OR telefono LIKE ? OR email LIKE ?)")
        like = f"%{busqueda}%"
        params.extend([busqueda, like, like, like, like, like])
    rows = conn.execute(
        f"""
        SELECT id FROM socios
        WHERE {' AND '.join(where)}
        ORDER BY fecha_baja IS NOT NULL, apellido COLLATE NOCASE, nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()
    return [socio for row in rows if (socio := socio_con_resumen(conn, row["id"]))]


def obtener(conn, socio_id: int) -> dict | None:
    return socio_con_resumen(conn, socio_id)


def obtener_cuotas(conn, socio_id: int) -> list[dict]:
    return [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM cuotas WHERE socio_id = ? ORDER BY periodo DESC",
            (socio_id,),
        )
    ]


def crear(conn, data: dict) -> dict:
    clean = validate_socio(data)
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO socios (
            nro_socio, dni, apellido, nombre, telefono, email, direccion, barrio, localidad,
            fecha_nacimiento, ocupacion, estado, cobrador, fecha_alta,
            creado_en, actualizado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            clean["nro_socio"],
            clean["dni"],
            clean["apellido"],
            clean["nombre"],
            clean["telefono"],
            clean["email"],
            clean["direccion"],
            clean["barrio"],
            clean["localidad"],
            clean["fecha_nacimiento"],
            clean["ocupacion"],
            clean["estado"],
            clean["cobrador"],
            clean["fecha_alta"],
            timestamp,
            timestamp,
        ),
    )
    return {"id": cursor.lastrowid, "nro_socio": clean["nro_socio"]}


def actualizar(conn, socio_id: int, data: dict) -> None:
    socio = obtener(conn, socio_id)
    if not socio or socio["fecha_baja"]:
        raise LookupError("Socio activo no encontrado")
    clean = validate_socio(data, editing=True)
    conn.execute(
        """
        UPDATE socios
        SET nro_socio = ?, dni = ?, apellido = ?, nombre = ?, telefono = ?, email = ?,
            direccion = ?, barrio = ?, localidad = ?,
            fecha_nacimiento = ?, ocupacion = ?, estado = ?, cobrador = ?, fecha_alta = ?, actualizado_en = ?
        WHERE id = ?
        """,
        (
            clean["nro_socio"],
            clean["dni"],
            clean["apellido"],
            clean["nombre"],
            clean["telefono"],
            clean["email"],
            clean["direccion"],
            clean["barrio"],
            clean["localidad"],
            clean["fecha_nacimiento"],
            clean["ocupacion"],
            clean["estado"],
            clean["cobrador"],
            clean["fecha_alta"],
            now_iso(),
            socio_id,
        ),
    )


def listar_morosos(conn) -> list[dict]:
    limite = int(config_model.get_config(conn).get("moroso_cuotas_limite", "4"))
    rows = conn.execute(
        """
        SELECT
            s.id,
            s.nro_socio,
            s.apellido,
            s.nombre,
            s.dni,
            s.telefono,
            s.email,
            s.direccion,
            s.localidad,
            s.cobrador,
            COUNT(c.id) AS cuotas_impagas,
            COALESCE(SUM(c.monto), 0) AS deuda
        FROM socios s
        JOIN cuotas c ON c.socio_id = s.id AND c.estado = 'pendiente'
        WHERE s.fecha_baja IS NULL
        GROUP BY s.id
        HAVING COUNT(c.id) > ?
        ORDER BY cuotas_impagas DESC, s.apellido COLLATE NOCASE, s.nombre COLLATE NOCASE
        """,
        (limite,),
    ).fetchall()
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
    conn.execute(
        "UPDATE socios SET fecha_baja = ?, actualizado_en = ? WHERE id = ?",
        (today_iso(), now_iso(), socio_id),
    )
    conn.execute(
        """
        DELETE FROM caja_movimientos
        WHERE cuota_id IN (SELECT id FROM cuotas WHERE socio_id = ?)
        """,
        (socio_id,),
    )
    conn.execute("DELETE FROM cuotas WHERE socio_id = ?", (socio_id,))
    return socio["nro_socio"]
