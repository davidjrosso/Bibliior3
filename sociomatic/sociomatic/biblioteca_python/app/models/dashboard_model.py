from app.models.helpers import current_period
from app.models import config_model
from app.repositories import dashboard_repository


def obtener(conn, periodo: str | None = None) -> dict:
    periodo = periodo or current_period()

    socios = dashboard_repository.socios_summary(conn)
    cuotas_periodo = dashboard_repository.cuotas_period_summary(conn, periodo)
    cuotas_global = dashboard_repository.cuotas_global_summary(conn)
    por_cobrador = dashboard_repository.cuotas_by_cobrador(conn, periodo)

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
                "nombre": config_model.cobrador_nombre(conn, row["cobrador"]),
                "cuotas": row["cuotas"] or 0,
                "recaudado": float(row["recaudado"] or 0),
                "pendiente": float(row["pendiente"] or 0),
            }
            for row in por_cobrador
        ],
    }
