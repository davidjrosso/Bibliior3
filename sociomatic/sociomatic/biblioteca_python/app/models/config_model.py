def get_config(conn) -> dict:
    rows = conn.execute("SELECT clave, valor FROM configuracion").fetchall()
    return {row["clave"]: row["valor"] for row in rows}


def update_config(conn, data: dict) -> None:
    for key in ("monto_activo", "monto_jubilado"):
        value = str(float(data.get(key, 0)))
        conn.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (key, value),
        )


def cuota_monto(conn, estado: str) -> float:
    config = get_config(conn)
    key = "monto_jubilado" if estado == "jubilado" else "monto_activo"
    return float(config.get(key, "0") or 0)

