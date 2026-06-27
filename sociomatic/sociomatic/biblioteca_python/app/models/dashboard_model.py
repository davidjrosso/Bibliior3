from app.models.helpers import current_period
from app.settings import COBRADORES


def obtener(conn, periodo: str | None = None) -> dict:
    periodo = periodo or current_period()

    socios = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = 'activo' THEN 1 ELSE 0 END) AS activos,
            SUM(CASE WHEN estado = 'jubilado' THEN 1 ELSE 0 END) AS jubilados,
            SUM(CASE WHEN cobrador = 1 THEN 1 ELSE 0 END) AS cobrador_1,
            SUM(CASE WHEN cobrador = 3 THEN 1 ELSE 0 END) AS cobrador_3
        FROM socios
        WHERE fecha_baja IS NULL
        """
    ).fetchone()

    cuotas_periodo = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN c.estado = 'pagada' THEN 1 ELSE 0 END) AS pagadas,
            SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
          AND c.periodo = ?
        """,
        (periodo,),
    ).fetchone()

    cuotas_global = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN c.estado = 'pagada' THEN 1 ELSE 0 END) AS pagadas,
            SUM(CASE WHEN c.estado = 'pendiente' THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
        """
    ).fetchone()

    por_cobrador = conn.execute(
        """
        SELECT
            s.cobrador,
            COUNT(c.id) AS cuotas,
            SUM(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) AS recaudado,
            SUM(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) AS pendiente
        FROM cuotas c
        JOIN socios s ON s.id = c.socio_id
        WHERE s.fecha_baja IS NULL
          AND c.periodo = ?
        GROUP BY s.cobrador
        ORDER BY s.cobrador
        """,
        (periodo,),
    ).fetchall()

    def number(row, key):
        return row[key] or 0

    return {
        "periodo": periodo,
        "socios": {
            "total": number(socios, "total"),
            "activos": number(socios, "activos"),
            "jubilados": number(socios, "jubilados"),
            "cobrador_1": number(socios, "cobrador_1"),
            "cobrador_3": number(socios, "cobrador_3"),
        },
        "cuotas_periodo": {
            "total": number(cuotas_periodo, "total"),
            "pagadas": number(cuotas_periodo, "pagadas"),
            "pendientes": number(cuotas_periodo, "pendientes"),
            "recaudado": float(number(cuotas_periodo, "recaudado")),
            "pendiente": float(number(cuotas_periodo, "pendiente")),
        },
        "cuotas_global": {
            "total": number(cuotas_global, "total"),
            "pagadas": number(cuotas_global, "pagadas"),
            "pendientes": number(cuotas_global, "pendientes"),
            "recaudado": float(number(cuotas_global, "recaudado")),
            "pendiente": float(number(cuotas_global, "pendiente")),
        },
        "por_cobrador": [
            {
                "cobrador": row["cobrador"],
                "nombre": COBRADORES.get(row["cobrador"], ""),
                "cuotas": row["cuotas"] or 0,
                "recaudado": float(row["recaudado"] or 0),
                "pendiente": float(row["pendiente"] or 0),
            }
            for row in por_cobrador
        ],
    }
