from pathlib import Path
import sqlite3

from app.models.helpers import today_iso
from app.settings import DATA_DIR, DB_PATH


BACKUP_DIR = DATA_DIR / "backups"
BACKUP_RETENTION = 15


def backup_diario(retention: int = BACKUP_RETENTION) -> Path | None:
    if not DB_PATH.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = today_iso().replace("-", "")
    if any(BACKUP_DIR.glob(f"biblioteca-{fecha}-*.sqlite3")):
        return None

    destino = BACKUP_DIR / f"biblioteca-{fecha}-{_hora_actual()}.sqlite3"
    _copiar_sqlite(DB_PATH, destino)
    _limpiar_backups(retention)
    return destino


def _copiar_sqlite(origen: Path, destino: Path) -> None:
    with sqlite3.connect(origen) as source, sqlite3.connect(destino) as target:
        source.backup(target)


def _limpiar_backups(retention: int) -> None:
    backups = sorted(BACKUP_DIR.glob("biblioteca-*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
    for backup in backups[max(1, retention) :]:
        backup.unlink(missing_ok=True)


def _hora_actual() -> str:
    from datetime import datetime

    return datetime.now().strftime("%H%M%S")
