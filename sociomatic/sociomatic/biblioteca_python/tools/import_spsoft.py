from __future__ import annotations

import argparse
import csv
import re
import shutil
import sqlite3
import struct
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.models.helpers import add_months

DEFAULT_ZIP = Path.home() / "Downloads" / "spsoft-20260725T174059Z-1-001.zip"
DEFAULT_SOURCE_DIR = ROOT.parents[2] / "Soft Biblio - NO TOCAR-20260817T193633Z-1-001" / "Soft Biblio - NO TOCAR"
DEFAULT_SP01 = ROOT / "data" / "analisis_sp01_koha" / "sp01_parseado.csv"
DEFAULT_KOHA = ROOT / "data" / "analisis_sp01_koha" / "koha_usuarios.csv"
DEFAULT_MDB = ROOT / "data" / "analisis_spsoft_zip" / "fvmaecli_registro_altas_bajas.csv"
DB_PATH = ROOT / "data" / "biblioteca.sqlite3"
ZONA_COBRADOR = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    6: 5,
}
MONTH_ALIASES = [
    ("SEPTIEMBRE", 9),
    ("SETIEMBRE", 9),
    ("FEBRERO", 2),
    ("AGOSTO", 8),
    ("OCTUBRE", 10),
    ("NOVIEMBRE", 11),
    ("DICIEMBRE", 12),
    ("MARZO", 3),
    ("ABRIL", 4),
    ("ENERO", 1),
    ("JUNIO", 6),
    ("JULIO", 7),
    ("MAYO", 5),
    ("SEPT", 9),
    ("SEP", 9),
    ("SET", 9),
    ("FEB", 2),
    ("AGO", 8),
    ("AG", 8),
    ("OCT", 10),
    ("NOV", 11),
    ("DIC", 12),
    ("MAR", 3),
    ("ABR", 4),
    ("AB", 4),
    ("ENE", 1),
    ("JUN", 6),
    ("JUL", 7),
]


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


def parse_year(value: str | int | None) -> int | None:
    if value is None:
        return None
    try:
        number = int(str(value))
    except ValueError:
        return None
    if 2000 <= number <= 2099:
        return number
    if 0 <= number <= 99:
        return 2000 + number
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


def read_dbf(path: Path) -> list[dict]:
    return list(DbfTable(path.read_bytes()).rows())


def load_dbf(args, name: str) -> list[dict]:
    if args.source_dir:
        return read_dbf(args.source_dir / name)
    return read_dbf_from_zip(args.zip, f"spsoft/Fvta/{name}")


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


def cliente_by_nro(rows: list[dict]) -> dict[int, dict]:
    result = {}
    for row in rows:
        nro = as_int(row.get("NCLI"))
        if nro is not None:
            result[nro] = row
    return result


def es_registro_especial(row: dict) -> bool:
    nro = as_int(row.get("NCLI"))
    razon = (row.get("RAZON") or "").upper()
    return nro in {0, 999999} or "BIBLIOTECA POP" in razon


def es_socio_importable(row: dict) -> bool:
    zona = as_int(row.get("ZONA"))
    return zona in ZONA_COBRADOR and not es_registro_especial(row)


def normalizar_nota_zona4(value: str | None) -> str:
    text = str(value or "").replace("\ufffd", "N").strip().upper()
    text = text.replace("Ñ", "N")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^A-Z0-9/]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_es_anio(token: str) -> bool:
    if token in {"ANO", "AN", "AN0"}:
        return True
    if token.startswith("AN") and any(ch.isdigit() for ch in token):
        return True
    return token.startswith("A") and token.endswith("O") and any(ch.isdigit() for ch in token)


def anio_probable(token: str) -> int | None:
    for match in reversed(re.findall(r"20\d{2}|\d{2}", token)):
        year = parse_year(match)
        if year and 2020 <= year <= 2035:
            return year
    return None


def extraer_meses(text: str) -> list[tuple[int, int | None, int]]:
    tokens = normalizar_nota_zona4(text).replace("/", " ").split()
    found = []
    for idx, token in enumerate(tokens):
        for alias, month in MONTH_ALIASES:
            if not token.startswith(alias):
                continue
            rest = token[len(alias) :]
            year = anio_probable(rest)
            if year is None and idx + 1 < len(tokens):
                year = anio_probable(tokens[idx + 1])
            found.append((month, year, idx))
            break
    return found


def periodos_entre(desde: str, hasta: str) -> list[str]:
    if desde > hasta:
        return []
    periodos = []
    periodo = desde
    while periodo <= hasta:
        periodos.append(periodo)
        periodo = add_months(periodo, 1)
    return periodos


def rango_pagado_zona4(nota: str | None) -> tuple[str | None, str | None, str]:
    raw = str(nota or "").strip()
    normalizada = normalizar_nota_zona4(raw)
    if not normalizada or normalizada == "(VACIO)":
        return None, None, "sin dato"
    if "DEUDA" in normalizada:
        return None, None, "requiere revision: deuda"

    tokens = normalizada.split()
    year_words = [token for token in tokens if token_es_anio(token)]
    if year_words:
        year = None
        for token in reversed(tokens):
            year = anio_probable(token)
            if year:
                break
        if year:
            return f"{year}-01", f"{year}-12", "anio completo"

    meses = extraer_meses(raw)
    if not meses:
        return None, None, "no interpretado"

    tiene_rango = "/" in normalizada or " A " in f" {normalizada} "
    if tiene_rango and len(meses) >= 2:
        start_month, start_year, _ = meses[0]
        end_month, end_year, _ = meses[-1]
        if start_year is None:
            start_year = end_year
        if end_year is None:
            end_year = start_year
        if start_year and end_year:
            return f"{start_year}-{start_month:02d}", f"{end_year}-{end_month:02d}", "rango explicito"

    month, year, _ = meses[-1]
    if year:
        start_year = 2026 if year > 2026 else year
        return f"{start_year}-01", f"{year}-{month:02d}", "hasta mes indicado"
    return None, None, "sin anio"


def aplicar_pagos_zona4(conn: sqlite3.Connection, cliente_rows: list[dict], timestamp: str) -> Counter:
    from app.models import config_model

    stats = Counter()
    fecha_pago = timestamp[:10]
    for row_cliente in cliente_rows:
        if as_int(row_cliente.get("ZONA")) != 4:
            continue
        nro = as_int(row_cliente.get("NCLI"))
        desde, hasta, motivo = rango_pagado_zona4(row_cliente.get("DGR"))
        if not desde or not hasta:
            stats["zona4_revision_manual"] += 1
            continue
        socio = conn.execute(
            "SELECT id, estado FROM socios WHERE nro_socio = ? AND fecha_baja IS NULL AND cobrador = 4",
            (nro,),
        ).fetchone()
        if not socio:
            stats["zona4_socio_no_encontrado"] += 1
            continue
        monto = config_model.cuota_monto(conn, socio["estado"])
        observacion = (
            f"Importado SPSoft Zona 4/Ingr. Brutos: {str(row_cliente.get('DGR') or '').strip()} "
            f"({motivo}, {desde} a {hasta})."
        )
        for periodo in periodos_entre(desde, hasta):
            existing = conn.execute(
                "SELECT id, estado FROM cuotas WHERE socio_id = ? AND periodo = ?",
                (socio["id"], periodo),
            ).fetchone()
            if existing and existing["estado"] == "pagada":
                stats["zona4_cuotas_ya_pagadas"] += 1
                continue
            if existing:
                conn.execute(
                    """
                    UPDATE cuotas
                    SET estado = 'pagada', fecha_pago = ?, observacion = ?, actualizado_en = ?
                    WHERE id = ?
                    """,
                    (fecha_pago, observacion, timestamp, existing["id"]),
                )
                stats["zona4_cuotas_marcadas_pagadas"] += 1
                continue
            conn.execute(
                """
                INSERT INTO cuotas (socio_id, periodo, monto, estado, fecha_pago, observacion, creado_en, actualizado_en)
                VALUES (?, ?, ?, 'pagada', ?, ?, ?, ?)
                """,
                (socio["id"], periodo, monto, fecha_pago, observacion, timestamp, timestamp),
            )
            stats["zona4_cuotas_creadas_pagadas"] += 1
        stats["zona4_socios_aplicados"] += 1
    return stats


def build_socios(
    cliente_rows: list[dict],
    mdb_rows: list[dict],
    sp01_rows: list[dict],
    koha_rows: list[dict],
    cuota_rows: list[dict],
) -> dict[int, dict]:
    clientes = {
        nro: row
        for nro, row in cliente_by_nro(cliente_rows).items()
        if es_socio_importable(row)
    }
    mdb = mdb_by_nro(mdb_rows)
    sp01 = sp01_by_nro(sp01_rows)
    koha = koha_by_nro(koha_rows)
    nros = set(clientes)
    timestamp = now_iso()
    socios = {}
    for nro in sorted(nros):
        row_cliente = clientes.get(nro, {})
        row_mdb = mdb.get(nro, {})
        row_sp01 = sp01.get(nro, {})
        row_koha = koha.get(nro, {})
        koha_name = row_koha.get("nombre_koha", "")
        if row_cliente.get("RAZON"):
            apellido, nombre = split_name(row_cliente.get("RAZON", ""))
        elif row_sp01.get("nombre_lis"):
            apellido, nombre = split_name(row_sp01.get("nombre_lis", ""))
        elif row_mdb.get("Apellido y Nombre"):
            apellido, nombre = split_name(row_mdb.get("Apellido y Nombre", ""))
        elif "," in koha_name:
            apellido, nombre = [part.strip().upper() for part in koha_name.split(",", 1)]
        else:
            apellido, nombre = split_name(koha_name)
        dni = clean_dni(row_cliente.get("CUIT") or row_sp01.get("dni_cuit_lis") or row_mdb.get("Campo8"), nro)
        actividad = (row_sp01.get("actividad_lis") or "").strip()
        estado = "jubilado" if "JUBIL" in actividad.upper() else "activo"
        fecha_baja = None
        fecha_alta = norm_date(row_mdb.get("Fecha Ingreso")) or "2000-01-01"
        direccion = row_cliente.get("DIRE1") or row_sp01.get("domicilio_lis") or row_mdb.get("Campo10") or ""
        localidad = row_cliente.get("LOC") or row_sp01.get("localidad_lis") or row_mdb.get("Campo4") or "RIO TERCERO"
        telefono = row_cliente.get("TELEF2") or row_cliente.get("TE") or row_sp01.get("telefono1_lis") or row_mdb.get("Campo7") or ""
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
            "cobrador": ZONA_COBRADOR[as_int(row_cliente.get("ZONA"))],
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
    cliente_rows = load_dbf(args, "FVMAECLI.DBF")
    cuota_rows = load_dbf(args, "FVCUOTA.DBF")
    caja_rows = load_dbf(args, "FVCAJA.DBF")
    socios = build_socios(cliente_rows, mdb_rows, sp01_rows, koha_rows, cuota_rows)
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
        stats.update(aplicar_pagos_zona4(conn, cliente_rows, timestamp))
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
            (f"Importacion inicial desde {(args.source_dir or args.zip).name}", timestamp),
        )
    return {"backup": str(backup) if backup else "", **stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa datos historicos de SPSoft a Biblioteca.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR if DEFAULT_SOURCE_DIR.exists() else None)
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
