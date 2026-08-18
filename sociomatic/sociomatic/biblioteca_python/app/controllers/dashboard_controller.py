from app.controllers.base_controller import json_response
from app.services import dashboard_service


def get(handler, conn, query):
    periodo = (query.get("periodo", [""])[0] or "").strip() or None
    json_response(handler, {"exito": True, "dashboard": dashboard_service.obtener(conn, periodo)})
