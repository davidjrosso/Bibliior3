from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from urllib.parse import parse_qs, unquote, urlparse

from app.models.backup_model import backup_diario
from app.models.database import init_db
from app.router import dispatch_api, dispatch_print, dispatch_print_morosos
from app.settings import DB_PATH, STATIC_DIR


class BibliotecaHandler(SimpleHTTPRequestHandler):
    server_version = "BibliotecaPython/1.0"

    def end_headers(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("", "/") or parsed.path.endswith(".html"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(STATIC_DIR / "index.html")
        return str(STATIC_DIR / unquote(parsed.path.lstrip("/")))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            dispatch_api(self, "GET", parsed.path, parse_qs(parsed.query))
            return
        if parsed.path == "/imprimir":
            dispatch_print(self, parse_qs(parsed.query))
            return
        if parsed.path == "/imprimir-morosos":
            dispatch_print_morosos(self, parse_qs(parsed.query))
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        dispatch_api(self, "POST", parsed.path, parse_qs(parsed.query))

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        dispatch_api(self, "PUT", parsed.path, parse_qs(parsed.query))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        dispatch_api(self, "DELETE", parsed.path, parse_qs(parsed.query))


def main() -> None:
    init_db()
    backup_path = backup_diario()
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    httpd = ThreadingHTTPServer((host, port), BibliotecaHandler)
    print(f"Sistema Biblioteca listo en http://{host}:{port}")
    print(f"Base SQLite: {DB_PATH}")
    if backup_path:
        print(f"Backup diario: {backup_path}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
