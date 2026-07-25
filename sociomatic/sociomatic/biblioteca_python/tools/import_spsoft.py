from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
import struct
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_ZIP = Path.home() / "Downloads" / "spsoft-20260725T174059Z-1-001.zip"
DEFAULT_SP01 = ROOT / "data" / "analisis_sp01_koha" / "sp01_parseado.csv"
DEFAULT_KOHA = ROOT / "data" / "analisis_sp01_koha" / "koha_usuarios.csv"
DEFAULT_MDB = ROOT / "data" / "analisis_spsoft_zip" / "fvmaecli_registro_altas_bajas.csv"
DB_PATH = ROOT / "data" / "biblioteca.sqlite3"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def norm_date(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def usable_history_date(value: str | None) -> bool:
    parsed = norm_date(value)
    if not parsed:
        return False
    year = int(parsed[:4])
    return 1900 <= year <= date.today().year


def split_name(full_name: str) -> tuple[str, str]:
    clean = " ".join((full_name or "").replace(",", " ").split()).strip().upper()
    if not clean:
        return "SOCIO", "SIN NOMBRE"
    parts = clean.split()
    if len(parts) == 1:
        return parts[0], "."
    return parts[0], " ".join(parts[1:])


def clean_dni(value: str | int | float | None, nro_socio: int) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not text or int(text or "0") in {0, 99999999} or len(text) < 6:
        return f"SD-{nro_socio}"
    return text


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def as_int(value) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


class DbfTable:
    def __init__(self, data: bytes):
        self.data = data
        self.records = struct.unpack("<I", data[4:8])[0]
        self.header_len = struct.unpack("<H", data[8:10])[0]
        self.record_len = struct.unpack("<H", data[10:12])[0]
        self.fields = []
        pos = 32
        offset = 1
        while pos + 32 <= min(self.header_len, len(data)) and data[pos] != 0x0D:
            desc = data[pos : pos + 32]
            name = desc[:11].split(b"\x00")[0].decode("cp850", "replace").strip()
            field_type = chr(desc[11])
            length = desc[16]
            decimals = desc[17]
            self.fields.append((name, field_type, length, decimals, offset))
            offset += length
            pos += 32

    def rows(self):
        pos = self.header_len
        for _ in range(self.records):
            rec = self.data[pos : pos + self.record_len]
            pos += self.record_len
            if len(rec) < self.record_len or rec[:1] == b"*":
                continue
            row = {}
            for name, field_type, length, decimals, offset in self.fields:
                raw = rec[offset : offset + length]
                value = raw.decode("cp850", "replace").strip()
                if field_type == "N" and value:
                    try:
                        value = float(value) if decimals else int(value)
                    except ValueError:
                        pass
                elif field_type == "D":
                    value = norm_date(value.replace(" ", ""))
                row[name] = value
            yield row


def read_dbf_from_zip(zip_path: Path, member: str) -> list[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as fh:
            return list(DbfTable(fh.read()).rows())


def koha_by_nro(rows: list[dict]) -> dict[int, dict]:
    result = {}
    for row in rows:
        nro = as_int(row.get("cardnumber"))
        name = (row.get("nombre_koha") or "").upper()
        if nro in {1, 8080, 99999} or "SOCIO EN SALA" in name or "BIBLIOTECARIO" in name:
            continue
        if nro is not None:
            result[nro] = row
    return result


def sp01_by_nro(rows: list[dict]) -> dict[int, dict]:
    result = {}
    for row in rows:
        nro = as_int(row.get("codigo"))
        if nro is not None:
            result[nro] = row
    return result


def mdb_by_nro(rows: list[dict]) -> dict[int, dict]:
    result = {}
    for row in rows:
        nro = as_int(row.get("Nro Socio"))
        if nro is not None:
            result[nro] = row
    return result


def build_socios(mdb_rows: list[dict], sp01_rows: list[dict], koha_rows: list[dict], cuota_rows: list[dict]) -> dict[int, dict]:
    mdb = mdb_by_nro(mdb_rows)
    sp01 = sp01_by_nro(sp01_rows)
    koha = koha_by_nro(koha_rows)
    cuota_refs = {as_int(row.get("NCLI")) for row in cuota_rows}
    cuota_refs.discard(None)
    nros = set(mdb) | set(sp01) | set(koha) | cuota_refs
    timestamp = now_iso()
    socios = {}
    for nro in sorted(nros):
        row_mdb = mdb.get(nro, {})
        row_sp01 = sp01.get(nro, {})
        row_koha = koha.get(nro, {})
        koha_name = row_koha.get("nombre_koha", "")
        if "," in koha_name:
            apellido, nombre = [part.strip().upper() for part in koha_name.split(",", 1)]
        else:
            full_name = row_sp01.get("nombre_lis") or row_mdb.get("Apellido y Nombre") or koha_name
            apellido, nombre = split_name(full_name)
        dni = clean_dni(row_sp01.get("dni_cuit_lis") or row_mdb.get("Campo8"), nro)
        actividad = (row_sp01.get("actividad_lis") or "").strip()
        estado = "jubilado" if "JUBIL" in actividad.upper() else "activo"
        fecha_baja = norm_date(row_mdb.get("Fecha Egreso"))
        fecha_alta = norm_date(row_mdb.get("Fecha Ingreso")) or "2000-01-01"
        direccion = row_sp01.get("domicilio_lis") or row_mdb.get("Campo10") or ""
        localidad = row_sp01.get("localidad_lis") or row_mdb.get("Campo4") or "RIO TERCERO"
        telefono = row_sp01.get("telefono1_lis") or row_mdb.get("Campo7") or ""
        socios[nro] = {
            "nro_socio": nro,
            "dni": dni,
            "apellido": apellido or "SOCIO",
            "nombre": nombre or ".",
            "telefono": str(telefono).strip(),
            "email": row_koha.get("email_koha", "") or "",
            "direccion": direccion.strip(),
            "barrio": "",
            "localidad": localidad.strip() or "RIO TERCERO",
            "fecha_nacimiento": None,
            "ocupacion": actividad.strip(),
            "estado": estado,
            "cobrador": 1,
            "fecha_alta": fecha_alta,
            "fecha_baja": fecha_baja,
            "creado_en": timestamp,
            "actualizado_en": timestamp,
        }
    return socios


def grouped_cuotas(rows: list[dict]) -> dict[tuple[int, str], dict]:
    groups = defaultdict(lambda: {"importe": 0.0, "cancel": 0.0, "records": 0, "fechas": [], "anuladas": 0})
    for row in rows:
        nro = as_int(row.get("NCLI"))
        fecha = row.get("FECHA") or row.get("FE_EMI")
        if nro is None or not usable_history_date(fecha):
            continue
        if row.get("ANULA") == "A":
            continue
        periodo = fecha[:7]
        key = (nro, periodo)
        importe = float(row.get("IMPORTE") or 0)
        cancel = float(row.get("CANCEL") or 0)
        groups[key]["importe"] += importe
        groups[key]["cancel"] += cancel
        groups[key]["records"] += 1
        groups[key]["fechas"].append(fecha)
    return groups


def backup_db(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"biblioteca_pre_spsoft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    shutil.copy2(db_path, target)
    return target


def clear_data(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in ("caja_movimientos", "caja_dias", "cuotas", "socios", "auditoria"):
        conn.execute(f"DELETE FROM {table}")
    for seq in ("caja_movimientos", "cuotas", "socios", "auditoria"):
        conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (seq,))
    conn.execute("PRAGMA foreign_keys = ON")


def import_data(args) -> dict:
    from app.models.database import init_db

    init_db()
    backup = backup_db(DB_PATH)
    sp01_rows = read_csv(args.sp01_csv)
    koha_rows = read_csv(args.koha_csv)
    mdb_rows = read_csv(args.mdb_csv)
    cuota_rows = read_dbf_from_zip(args.zip, "spsoft/Fvta/FVCUOTA.DBF")
    caja_rows = read_dbf_from_zip(args.zip, "spsoft/Fvta/FVCAJA.DBF")
    socios = build_socios(mdb_rows, sp01_rows, koha_rows, cuota_rows)
    cuotas = grouped_cuotas(cuota_rows)
    timestamp = now_iso()
    stats = Counter()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        clear_data(conn)
        nro_to_id = {}
        used_dni = set()
        for nro, socio in socios.items():
            dni = socio["dni"]
            if socio["fecha_baja"] is None and dni in used_dni:
                socio["dni"] = f"SD-{nro}"
            if socio["fecha_baja"] is None:
                used_dni.add(socio["dni"])
            cur = conn.execute(
                """
                INSERT INTO socios (
                    nro_socio, dni, apellido, nombre, telefono, email, direccion, barrio, localidad,
                    fecha_nacimiento, ocupacion, estado, cobrador, fecha_alta, fecha_baja, creado_en, actualizado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    socio["nro_socio"], socio["dni"], socio["apellido"], socio["nombre"],
                    socio["telefono"], socio["email"], socio["direccion"], socio["barrio"],
                    socio["localidad"], socio["fecha_nacimiento"], socio["ocupacion"],
                    socio["estado"], socio["cobrador"], socio["fecha_alta"], socio["fecha_baja"],
                    socio["creado_en"], socio["actualizado_en"],
                ),
            )
            nro_to_id[nro] = cur.lastrowid
            stats["socios_baja" if socio["fecha_baja"] else "socios_activos"] += 1
        for (nro, periodo), data in sorted(cuotas.items()):
            socio_id = nro_to_id.get(nro)
            if not socio_id:
                continue
            restante = round(float(data["importe"]) - float(data["cancel"]), 2)
            estado = "pagada" if data["importe"] > 0 and restante <= 0.01 else "pendiente"
            monto = round(float(data["importe"]) if estado == "pagada" else max(restante, 0.0), 2)
            if monto <= 0:
                continue
            observacion = f"Importado SPSoft. Total original {data['importe']:.2f}, cancelado {data['cancel']:.2f}."
            if data["records"] > 1:
                observacion = f"Importado SPSoft: {data['records']} registros agrupados. Total original {data['importe']:.2f}, cancelado {data['cancel']:.2f}."
            fecha_pago = max(data["fechas"]) if estado == "pagada" else None
            conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, fecha_pago, observacion, creado_en, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (socio_id, periodo, monto, estado, fecha_pago, observacion, timestamp, timestamp),
            )
            stats[f"cuotas_{estado}"] += 1
        dias = set()
        for row in caja_rows:
            if row.get("ANULA") == "A" or row.get("TIPO") != "EF":
                continue
            fecha = row.get("FE_EMI")
            monto = float(row.get("IMP") or 0)
            if not usable_history_date(fecha) or monto == 0:
                continue
            dias.add(fecha)
            tipo = "ingreso" if monto > 0 else "egreso"
            conn.execute(
                """
                INSERT INTO caja_movimientos (
                    fecha, tipo, concepto, descripcion, monto, medio_pago, referencia, cuota_id, creado_en, actualizado_en
                ) VALUES (?, ?, 'Caja historica SPSoft', ?, ?, 'efectivo', ?, NULL, ?, ?)
                """,
                (
                    fecha,
                    tipo,
                    f"Comprobante {row.get('CODSUC', '')}-{row.get('NFAC', '')}".strip(),
                    abs(monto),
                    f"spsoft:caja:{row.get('CODSUC', '')}-{row.get('NFAC', '')}",
                    timestamp,
                    timestamp,
                ),
            )
            stats["caja_movimientos"] += 1
        for fecha in sorted(dias):
            conn.execute(
                """
                INSERT OR IGNORE INTO caja_dias (fecha, saldo_inicial, observacion, cerrado, creado_en, actualizado_en)
                VALUES (?, 0, 'Importado desde SPSoft', 1, ?, ?)
                """,
                (fecha, timestamp, timestamp),
            )
        stats["caja_dias"] = len(dias)
        conn.execute(
            "INSERT INTO auditoria (accion, detalle, creado_en) VALUES ('importacion_spsoft', ?, ?)",
            (f"Importacion inicial desde {args.zip.name}", timestamp),
        )
    return {"backup": str(backup) if backup else "", **stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa datos historicos de SPSoft a Biblioteca.")
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--sp01-csv", type=Path, default=DEFAULT_SP01)
    parser.add_argument("--koha-csv", type=Path, default=DEFAULT_KOHA)
    parser.add_argument("--mdb-csv", type=Path, default=DEFAULT_MDB)
    args = parser.parse_args()
    stats = import_data(args)
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
