from app.models import dashboard_model


def obtener(conn, periodo: str | None = None) -> dict:
    return dashboard_model.obtener(conn, periodo)
