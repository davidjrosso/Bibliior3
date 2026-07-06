import json
from http import HTTPStatus


def read_json(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if not length:
        return {}
    body = handler.rfile.read(length).decode("utf-8")
    return json.loads(body) if body else {}


def json_response(handler, payload: dict, status: int = HTTPStatus.OK, headers: dict | None = None) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(data)


def html_response(handler, html: str, status: int = HTTPStatus.OK) -> None:
    data = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
