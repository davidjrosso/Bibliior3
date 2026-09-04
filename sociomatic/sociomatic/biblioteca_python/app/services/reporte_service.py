from app.models import reporte_model


def generar_listado(conn, query: dict) -> dict:
    return reporte_model.generar_listado(conn, query)
