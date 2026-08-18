from http import HTTPStatus

from app.controllers.base_controller import html_response
from app.services import print_service


def print_cuotas(handler, conn, query):
    try:
        html_response(handler, print_service.cuotas_html(conn, query))
    except ValueError as exc:
        handler.send_error(HTTPStatus.BAD_REQUEST, str(exc))
        return


def print_morosos(handler, conn, _query):
    html_response(handler, print_service.morosos_html(conn))
