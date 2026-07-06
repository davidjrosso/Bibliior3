import json
import re
import sqlite3
from http import HTTPStatus

from app.controllers import auth_controller, caja_controller, config_controller, cuota_controller, dashboard_controller, print_controller, socio_controller
from app.controllers.base_controller import html_response, json_response
from app.models.database import get_db
from app.models import security_model


def dispatch_api(handler, method: str, path: str, query: dict) -> None:
    try:
        with get_db() as conn:
            if path == "/api/auth/session" and method == "GET":
                auth_controller.session(handler, conn, query)
                return
            if path == "/api/auth/login" and method == "POST":
                auth_controller.login(handler, conn, query)
                return
            if path == "/api/auth/logout" and method == "POST":
                auth_controller.logout(handler, conn, query)
                return
            if not security_model.is_authenticated(handler, conn):
                json_response(handler, {"exito": False, "error": "Debe iniciar sesion."}, HTTPStatus.UNAUTHORIZED)
                return
            if path == "/api/config/acceso" and method == "POST":
                auth_controller.update_login(handler, conn, query)
                return
            if path == "/api/config" and method == "GET":
                config_controller.get(handler, conn, query)
                return
            if path == "/api/config" and method == "POST":
                config_controller.update(handler, conn, query)
                return
            if path == "/api/config/seguridad" and method == "POST":
                config_controller.update_security(handler, conn, query)
                return
            if path == "/api/config/tipos-socio" and method == "POST":
                config_controller.create_tipo_socio(handler, conn, query)
                return
            tipo_match = re.fullmatch(r"/api/config/tipos-socio/([A-Za-z0-9_-]+)", path)
            if tipo_match:
                tipo_id = tipo_match.group(1)
                if method == "PUT":
                    config_controller.update_tipo_socio(handler, conn, query, tipo_id)
                elif method == "DELETE":
                    config_controller.delete_tipo_socio(handler, conn, query, tipo_id)
                else:
                    json_response(handler, {"error": "Metodo no permitido"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return
            if path == "/api/config/cobradores" and method == "POST":
                config_controller.create_cobrador(handler, conn, query)
                return
            cobrador_match = re.fullmatch(r"/api/config/cobradores/(\d+)", path)
            if cobrador_match:
                cobrador_id = int(cobrador_match.group(1))
                if method == "PUT":
                    config_controller.update_cobrador(handler, conn, query, cobrador_id)
                elif method == "DELETE":
                    config_controller.delete_cobrador(handler, conn, query, cobrador_id)
                else:
                    json_response(handler, {"error": "Metodo no permitido"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return

            if path == "/api/dashboard" and method == "GET":
                dashboard_controller.get(handler, conn, query)
                return

            if path == "/api/caja" and method == "GET":
                caja_controller.get(handler, conn, query)
                return
            if path == "/api/caja/dia" and method == "POST":
                caja_controller.update_day(handler, conn, query)
                return
            if path == "/api/caja/movimientos" and method == "POST":
                caja_controller.create_movement(handler, conn, query)
                return
            caja_match = re.fullmatch(r"/api/caja/movimientos/(\d+)", path)
            if caja_match:
                movimiento_id = int(caja_match.group(1))
                if method == "PUT":
                    caja_controller.update_movement(handler, conn, query, movimiento_id)
                elif method == "DELETE":
                    caja_controller.delete_movement(handler, conn, query, movimiento_id)
                else:
                    json_response(handler, {"error": "Metodo no permitido"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return

            if path == "/api/socios" and method == "GET":
                socio_controller.index(handler, conn, query)
                return
            if path == "/api/socios/morosos" and method == "GET":
                socio_controller.morosos(handler, conn, query)
                return
            if path == "/api/socios" and method == "POST":
                socio_controller.create(handler, conn, query)
                return
            socio_match = re.fullmatch(r"/api/socios/(\d+)", path)
            if socio_match:
                socio_id = int(socio_match.group(1))
                if method == "GET":
                    socio_controller.show(handler, conn, query, socio_id)
                elif method == "PUT":
                    socio_controller.update(handler, conn, query, socio_id)
                elif method == "DELETE":
                    socio_controller.delete(handler, conn, query, socio_id)
                else:
                    json_response(handler, {"error": "Metodo no permitido"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return

            if path == "/api/cuotas/generar" and method == "POST":
                cuota_controller.generate(handler, conn, query)
                return
            if path == "/api/cuotas/adelanto" and method == "POST":
                cuota_controller.advance_payment(handler, conn, query)
                return
            if path == "/api/cuotas" and method == "GET":
                cuota_controller.index(handler, conn, query)
                return
            if path == "/api/cuotas" and method == "POST":
                cuota_controller.create(handler, conn, query)
                return
            cuota_match = re.fullmatch(r"/api/cuotas/(\d+)", path)
            if cuota_match:
                cuota_id = int(cuota_match.group(1))
                if method == "PUT":
                    cuota_controller.update(handler, conn, query, cuota_id)
                elif method == "DELETE":
                    cuota_controller.delete(handler, conn, query, cuota_id)
                else:
                    json_response(handler, {"error": "Metodo no permitido"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return
            cuota_pay_match = re.fullmatch(r"/api/cuotas/(\d+)/pagar", path)
            if cuota_pay_match and method == "POST":
                cuota_controller.pay(handler, conn, query, int(cuota_pay_match.group(1)))
                return
            cuota_pending_match = re.fullmatch(r"/api/cuotas/(\d+)/pendiente", path)
            if cuota_pending_match and method == "POST":
                cuota_controller.pending(handler, conn, query, int(cuota_pending_match.group(1)))
                return

            json_response(handler, {"error": "Endpoint no encontrado"}, HTTPStatus.NOT_FOUND)
    except LookupError as exc:
        json_response(handler, {"exito": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
    except ValueError as exc:
        json_response(handler, {"exito": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
    except PermissionError as exc:
        json_response(handler, {"exito": False, "error": str(exc)}, HTTPStatus.FORBIDDEN)
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "socios.nro_socio" in message:
            error = "Ese nro. de socio ya esta en uso."
        elif "socios.dni" in message:
            error = "Ese DNI ya esta registrado en un socio activo."
        else:
            error = f"Dato duplicado o invalido: {exc}"
        json_response(handler, {"exito": False, "error": error}, HTTPStatus.BAD_REQUEST)
    except json.JSONDecodeError:
        json_response(handler, {"exito": False, "error": "JSON invalido"}, HTTPStatus.BAD_REQUEST)
    except Exception as exc:
        json_response(handler, {"exito": False, "error": f"Error interno: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def dispatch_print(handler, query: dict) -> None:
    with get_db() as conn:
        if not security_model.is_authenticated(handler, conn):
            html_response(handler, "<h1>Debe iniciar sesion.</h1>", HTTPStatus.UNAUTHORIZED)
            return
        print_controller.print_cuotas(handler, conn, query)


def dispatch_print_morosos(handler, query: dict) -> None:
    with get_db() as conn:
        if not security_model.is_authenticated(handler, conn):
            html_response(handler, "<h1>Debe iniciar sesion.</h1>", HTTPStatus.UNAUTHORIZED)
            return
        print_controller.print_morosos(handler, conn, query)
