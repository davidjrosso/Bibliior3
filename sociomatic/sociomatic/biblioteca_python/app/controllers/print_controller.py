from http import HTTPStatus

from app.controllers.base_controller import html_response
from app.models import config_model, cuota_model
from app.models.helpers import next_period
from app.models import socio_model
from app.views.print_view import render_morosos, render_print


def print_cuotas(handler, conn, query):
    periodo = query.get("periodo", [next_period()])[0]
    cobrador = int(query.get("cobrador", ["1"])[0])
    if cobrador not in {row["id"] for row in config_model.listar_cobradores(conn, solo_activos=True)}:
        handler.send_error(HTTPStatus.BAD_REQUEST, "Cobrador invalido.")
        return
    rows = cuota_model.cuotas_para_imprimir(conn, periodo, cobrador)
    html_response(handler, render_print(periodo, config_model.cobrador_nombre(conn, cobrador), rows))


def print_morosos(handler, conn, _query):
    config = config_model.get_config(conn)
    limite = int(config.get("moroso_cuotas_limite", "4"))
    html_response(handler, render_morosos(socio_model.listar_morosos(conn), limite))
