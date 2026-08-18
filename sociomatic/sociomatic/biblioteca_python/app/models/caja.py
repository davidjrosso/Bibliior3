from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping

from app.models.row import row_value


TipoMovimientoCaja = Literal["ingreso", "egreso"]
MedioPago = Literal["efectivo", "transferencia", "tarjeta", "cheque", "otro"]


@dataclass(slots=True)
class CajaDia:
    fecha: str
    saldo_inicial: float
    observacion: str
    cerrado: bool
    creado_en: str
    actualizado_en: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> CajaDia:
        return cls(
            fecha=str(row["fecha"]),
            saldo_inicial=float(row_value(row, "saldo_inicial", 0) or 0),
            observacion=str(row_value(row, "observacion", "") or ""),
            cerrado=bool(int(row_value(row, "cerrado", 0) or 0)),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CajaMovimiento:
    id: int | None
    fecha: str
    tipo: TipoMovimientoCaja
    concepto: str
    descripcion: str
    monto: float
    medio_pago: MedioPago
    referencia: str
    cuota_id: int | None
    creado_en: str
    actualizado_en: str

    @property
    def impacta_caja_diaria(self) -> bool:
        return self.medio_pago == "efectivo"

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> CajaMovimiento:
        return cls(
            id=row_value(row, "id"),
            fecha=str(row["fecha"]),
            tipo=str(row["tipo"]),  # type: ignore[arg-type]
            concepto=str(row["concepto"]),
            descripcion=str(row_value(row, "descripcion", "") or ""),
            monto=float(row["monto"]),
            medio_pago=str(row_value(row, "medio_pago", "efectivo") or "efectivo"),  # type: ignore[arg-type]
            referencia=str(row_value(row, "referencia", "") or ""),
            cuota_id=row_value(row, "cuota_id"),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
