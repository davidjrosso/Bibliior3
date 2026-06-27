import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.environ.get("BIBLIOTECA_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "biblioteca.sqlite3"

COBRADORES = {
    1: "Cobrador",
    2: "No me acuerdo",
    3: "Biblioteca",
    4: "Pago adelantado",
    5: "Debe mas de cuatro cuotas",
}
