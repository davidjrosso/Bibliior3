from app.controllers.base_controller import json_response, read_json
from app.models import config_model


def get(handler, conn, _query):
    json_response(handler, {"exito": True, "config": config_model.get_config(conn)})


def update(handler, conn, _query):
    config_model.update_config(conn, read_json(handler))
    json_response(handler, {"exito": True})

