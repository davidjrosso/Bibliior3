from app.controllers.base_controller import json_response
from app.services import reporte_service


def listados(handler, conn, query):
    json_response(handler, {"exito": True, **reporte_service.generar_listado(conn, query)})
