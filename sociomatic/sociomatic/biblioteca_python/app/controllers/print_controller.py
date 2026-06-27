from http import HTTPStatus

from app.controllers.base_controller import html_response
from app.models import cuota_model
from app.models.helpers import next_period
from app.views.print_view import render_print


def print_cuotas(handler, conn, query):
    periodo = query.get("periodo", [next_period()])[0]
    cobrador = int(query.get("cobrador", ["1"])[0])
    if cobrador not in {1, 3}:
        handler.send_error(HTTPStatus.BAD_REQUEST, "Solo se imprimen cobrador 1 o 3.")
        return
    rows = cuota_model.cuotas_para_imprimir(conn, periodo, cobrador)
    html_response(handler, render_print(periodo, cobrador, rows))

